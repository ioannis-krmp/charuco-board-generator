import trimesh
from shapely.geometry import box as shapely_box, MultiPolygon, Polygon
from shapely.ops import unary_union


def build_meshes(img, w, h, ppm, thick_mm):
    mm_per_px = 1.0 / ppm
    board_w = w * mm_per_px
    board_h = h * mm_per_px

    rects = []
    for y in range(h):
        row = img[y]
        x = 0
        while x < w:
            if row[x] < 128:
                xs = x
                while x < w and row[x] < 128:
                    x += 1
                rects.append(shapely_box(
                    xs * mm_per_px,
                    (h - 1 - y) * mm_per_px,
                    x * mm_per_px,
                    (h - y) * mm_per_px,
                ))
            else:
                x += 1

    black_poly = unary_union(rects)
    full_rect = shapely_box(0, 0, board_w, board_h)
    white_poly = full_rect.difference(black_poly)

    black_mesh = extrude_poly(black_poly, thick_mm)
    white_mesh = extrude_poly(white_poly, thick_mm)
    return black_mesh, white_mesh


def extrude_poly(poly, height):
    if isinstance(poly, Polygon):
        return trimesh.creation.extrude_polygon(poly, height)
    elif isinstance(poly, MultiPolygon):
        meshes = [trimesh.creation.extrude_polygon(p, height) for p in poly.geoms]
        return trimesh.util.concatenate(meshes)
    raise TypeError(f"Unexpected geometry type: {type(poly)}")
