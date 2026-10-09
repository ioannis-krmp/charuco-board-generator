"""CLI: generate a colored CadQuery STEP assembly directly from a rendered
board PNG + metadata file (width, height, px-per-mm — one per line). Shares
the STEP export pipeline with the GUI via export/cadquery_export.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2

from export.cadquery_export import export_step


def build_step(png_path: str, meta_path: str, out_step: str, pattern_mm: float = 2.5, base_mm: float = 0.0, border_mm: float = 0.0) -> None:
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

    export_step(img, w, h, ppm, pattern_mm, out_step, base_mm=base_mm, border_mm=border_mm, progress_cb=print)
    print(f"done — {out_step} ({os.path.getsize(out_step) / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: build_step.py <png> <meta> <output.step> [pattern_mm] [base_mm]")
        sys.exit(1)
    extra = [float(a) for a in sys.argv[4:6]]
    build_step(sys.argv[1], sys.argv[2], sys.argv[3], *extra)
