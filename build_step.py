import os
import cv2
import numpy as np
import cadquery as cq
from shapely.geometry import box as shapely_box, MultiPolygon, Polygon
from shapely.ops import unary_union


def build_step(
    png_path: str,
    meta_path: str,
    out_step: str,
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

    print("E: unary_union...")
    black_poly = unary_union(rects)

    print("F: white = board - black...")
    full_rect = shapely_box(0, 0, board_w, board_h)
    white_poly = full_rect.difference(black_poly)

    print("G: extrude to CadQuery solids...")
    black_solid = _extrude_cq(black_poly, thick_mm)
    white_solid = _extrude_cq(white_poly, thick_mm)

    print("H: build colored assembly...")
    asm = cq.Assembly()
    asm.add(black_solid, name="Black", color=cq.Color(0.1, 0.1, 0.1, 1))
    asm.add(white_solid, name="White", color=cq.Color(0.95, 0.95, 0.95, 1))

    print("I: export STEP...")
    asm.save(out_step)
    print(f"J: done — {out_step} ({os.path.getsize(out_step) / 1024 / 1024:.1f} MB)")


def _extrude_cq(poly, height: float) -> cq.Workplane:
    """Extrude a shapely Polygon or MultiPolygon to a CadQuery solid."""
    if isinstance(poly, Polygon):
        return _extrude_single_cq(poly, height)
    elif isinstance(poly, MultiPolygon):
        parts = [_extrude_single_cq(p, height) for p in poly.geoms]
        result = parts[0]
        for p in parts[1:]:
            result = result.union(p)
        return result
    else:
        raise TypeError(f"Unexpected geometry type: {type(poly)}")


def _extrude_single_cq(poly: Polygon, height: float) -> cq.Workplane:
    """Extrude a single shapely Polygon (with holes) to a CadQuery solid."""
    exterior = list(poly.exterior.coords)
    wp = cq.Workplane("XY").polyline(exterior).close().extrude(height)
    for hole in poly.interiors:
        hole_coords = list(hole.coords)
        cut = cq.Workplane("XY").polyline(hole_coords).close().extrude(height)
        wp = wp.cut(cut)
    return wp


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: build_step.py <png> <meta> <output.step>")
        sys.exit(1)
    build_step(sys.argv[1], sys.argv[2], sys.argv[3])
