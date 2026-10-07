import os
import cv2
import numpy as np
import trimesh
from shapely.geometry import box as shapely_box, MultiPolygon, Polygon
from shapely.ops import unary_union


def build_stl(
    png_path: str,
    meta_path: str,
    out_black_stl: str,
    out_white_stl: str,
    thick_mm: float = 2.5,
    border_mm: float = 0.0,
) -> None:
    print("A: start")

    with open(meta_path) as f:
        w = int(f.readline())
        h = int(f.readline())
        ppm = float(f.readline())
    print("B: meta", w, h, ppm)

    img = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)
    assert img is not None, f"Failed to load {png_path}"
    assert img.shape == (h, w), f"PNG size {img.shape} != meta ({h},{w})"
    print("C: image loaded", img.shape)

    mm_per_px = 1.0 / ppm
    board_w = w * mm_per_px + 2 * border_mm
    board_h = h * mm_per_px + 2 * border_mm

    # Build shapely rectangles from run-length encoded dark pixels
    rects = []
    for y in range(h):
        if y % 200 == 0:
            print(f"   row {y}/{h}")
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

    print(f"D: {len(rects)} rectangles")
    assert rects, "No black regions found"

    print("E: unary_union (merge 2D polygons)...")
    black_poly = unary_union(rects)
    print(f"   black area: {black_poly.area:.2f} mm²")

    print("F: white = full board - black (2D difference)...")
    full_rect = shapely_box(0, 0, board_w, board_h)
    white_poly = full_rect.difference(black_poly)
    print(f"   white area: {white_poly.area:.2f} mm²")

    # Accuracy check
    total_area = board_w * board_h
    area_error = abs(black_poly.area + white_poly.area - total_area)
    assert area_error < 1e-6, f"Area mismatch: {area_error}"
    print(f"   area check OK (error: {area_error:.2e})")

    print("G: extrude to 3D meshes...")
    black_mesh = _extrude_poly(black_poly, thick_mm)
    white_mesh = _extrude_poly(white_poly, thick_mm)
    print(f"   black: {len(black_mesh.faces)} faces, volume {black_mesh.volume:.2f} mm³")
    print(f"   white: {len(white_mesh.faces)} faces, volume {white_mesh.volume:.2f} mm³")

    print("H: export STLs...")
    black_mesh.export(out_black_stl)
    print(f"   black: {os.path.exists(out_black_stl)}")
    white_mesh.export(out_white_stl)
    print(f"   white: {os.path.exists(out_white_stl)}")

    print("I: done")
    print(out_black_stl)
    print(out_white_stl)


def _extrude_poly(poly, height: float) -> trimesh.Trimesh:
    """Extrude a shapely Polygon or MultiPolygon to a trimesh mesh."""
    if isinstance(poly, Polygon):
        return trimesh.creation.extrude_polygon(poly, height)
    elif isinstance(poly, MultiPolygon):
        meshes = [trimesh.creation.extrude_polygon(p, height) for p in poly.geoms]
        return trimesh.util.concatenate(meshes)
    else:
        raise TypeError(f"Unexpected geometry type: {type(poly)}")
