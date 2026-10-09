"""CLI: generate a black/white STL pair directly from a rendered board PNG
+ metadata file (width, height, px-per-mm — one per line). Shares the
raster -> mesh pipeline with the GUI via export/geometry.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2

from export.geometry import build_meshes


def build_stl(
    png_path: str,
    meta_path: str,
    out_black_stl: str,
    out_white_stl: str,
    pattern_mm: float = 2.5,
    base_mm: float = 0.0,
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

    print("D: building meshes (polygons, union, extrude)...")
    black_mesh, white_mesh = build_meshes(img, w, h, ppm, pattern_mm, base_mm=base_mm, border_mm=border_mm)
    print(f"   black: {len(black_mesh.faces)} faces, volume {black_mesh.volume:.2f} mm³")
    print(f"   white: {len(white_mesh.faces)} faces, volume {white_mesh.volume:.2f} mm³")

    print("E: export STLs...")
    black_mesh.export(out_black_stl)
    print(f"   black: {os.path.exists(out_black_stl)}")
    white_mesh.export(out_white_stl)
    print(f"   white: {os.path.exists(out_white_stl)}")

    print("F: done")
    print(out_black_stl)
    print(out_white_stl)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: png_to_stl.py <png> <meta> <output_black.stl> <output_white.stl> [pattern_mm] [base_mm]")
        sys.exit(1)
    extra = [float(a) for a in sys.argv[5:7]]
    build_stl(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], *extra)
