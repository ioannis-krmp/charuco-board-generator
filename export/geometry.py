"""Pure, Qt-free raster -> 2D polygon -> 3D mesh helpers. Shared by the GUI
preview/export pipeline (mesh_export.py) and the standalone CLI tools
(png_to_stl.py, build_step.py via cadquery_export.py).
"""
import trimesh
from shapely.geometry import box as shapely_box, MultiPolygon, Polygon
from shapely.ops import unary_union


def image_to_polygons(img, w, h, ppm, border_mm=0.0):
    """Run-length encode the dark (<128) pixels of a grayscale raster into
    shapely polygons in mm space, returning (black_poly, white_poly).
    """
    mm_per_px = 1.0 / ppm
    board_w = w * mm_per_px + 2 * border_mm
    board_h = h * mm_per_px + 2 * border_mm

    rects = []
    for y in range(h):
        row = img[y]
        x = 0
        while x < w:
            if row[x] < 128:
                xs = x
                while x < w and row[x] < 128:
                    x += 1
                dx = (x - xs) * mm_per_px
                dy = mm_per_px
                x_mm = border_mm + xs * mm_per_px
                y_mm = border_mm + (h - 1 - y) * mm_per_px
                rects.append(shapely_box(x_mm, y_mm, x_mm + dx, y_mm + dy))
            else:
                x += 1

    if not rects:
        raise ValueError("No black regions found in rendered image")

    black_poly = unary_union(rects)
    full_rect = shapely_box(0, 0, board_w, board_h)
    white_poly = full_rect.difference(black_poly)
    return black_poly, white_poly


def board_bounds(black_poly, white_poly):
    """Bounding box of the whole board. The two polygons partition it, so
    combining their bounds is exact (and far cheaper than a polygon union)."""
    b, w = black_poly.bounds, white_poly.bounds
    return min(b[0], w[0]), min(b[1], w[1]), max(b[2], w[2]), max(b[3], w[3])


def build_meshes(img, w, h, ppm, pattern_mm, base_mm=0.0, border_mm=0.0):
    """Black/white meshes for dual-color printing.

    pattern_mm is the height of the two-color layer. base_mm > 0 adds a solid
    full-board white base below it, so the black islands sit on (and bond to)
    white instead of touching it only at side walls. The pattern then spans
    z = base_mm .. base_mm + pattern_mm. base_mm = 0 means both colors run
    the full height (no base).
    """
    if pattern_mm <= 0:
        raise ValueError("pattern_mm must be > 0")
    if base_mm < 0:
        raise ValueError("base_mm must be >= 0")
    black_poly, white_poly = image_to_polygons(img, w, h, ppm, border_mm)

    black_mesh = extrude_polygon(black_poly, pattern_mm)
    white_mesh = extrude_polygon(white_poly, pattern_mm)
    if base_mm == 0:
        return black_mesh, white_mesh

    black_mesh.apply_translation((0, 0, base_mm))
    white_mesh.apply_translation((0, 0, base_mm))
    minx, miny, maxx, maxy = board_bounds(black_poly, white_poly)
    base_mesh = extrude_polygon(shapely_box(minx, miny, maxx, maxy), base_mm)
    # Plain concatenation, not a boolean union: the raster-traced pattern
    # isn't guaranteed watertight (diagonal pixel corners), and slicers merge
    # overlapping shells within one part per layer anyway.
    white_mesh = trimesh.util.concatenate([base_mesh, white_mesh])
    return black_mesh, white_mesh


def extrude_polygon(poly, height):
    if isinstance(poly, Polygon):
        return trimesh.creation.extrude_polygon(poly, height)
    elif isinstance(poly, MultiPolygon):
        meshes = [trimesh.creation.extrude_polygon(p, height) for p in poly.geoms]
        return trimesh.util.concatenate(meshes)
    raise TypeError(f"Unexpected geometry type: {type(poly)}")
