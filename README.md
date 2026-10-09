# Fiducial Board Generator

Generate 3D-printable calibration/fiducial boards with a GUI — ChArUco, plain ArUco marker grids, AprilTag grids, and classic chessboard/circle-grid patterns, each in its own tab.

Outputs STL (black + white parts for dual-color printing), 3MF (single file with both parts), and optionally STEP (colored CAD assembly via CadQuery).

Runs on Linux, macOS, and Windows.

![Fiducial Board Generator GUI](screenshot.png)

## Setup

### 1) Install uv

[uv](https://docs.astral.sh/uv/) manages the Python environment and dependencies. If you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then restart your shell, or run:

```bash
source $HOME/.local/bin/env
```

Verify with `uv --version`.

### 2) Clone and install

```bash
git clone git@github.com:ioannis-krmp/charuco-board-generator.git
cd charuco-board-generator
uv sync
```

`uv sync` creates `.venv/` and installs all dependencies from `pyproject.toml`: OpenCV, trimesh, shapely, CadQuery, PyQt6, pyqtgraph + PyOpenGL (3D view), numpy. All of these publish wheels for Linux, macOS, and Windows, so the same commands work on any OS — on Windows, run them from PowerShell (the `uv` installer gives you a PowerShell-native install command on its docs page).

### 3) Verify

```bash
uv run python -c "import cv2, trimesh, shapely; print('OK')"
```

## Usage

```bash
uv run python main.py
```

The window has one tab per board type. Every tab shares the same preview /
Board Info / Export layout; only the parameters differ.

- **ChArUco** — checkerboard with embedded ArUco markers at the corners.
  Squares X/Y, square size, marker size (must be smaller than square size),
  ArUco dictionary, resolution.
- **ArUco** — a plain grid of ArUco markers (no checkerboard), useful as a
  lighter-weight pose target. Markers X/Y, marker size, separation, ArUco
  dictionary, resolution.
- **AprilTag** — identical to the ArUco tab but backed by OpenCV's built-in
  AprilTag dictionaries (`DICT_APRILTAG_16h5/25h9/36h10/36h11`) instead of
  ArUco ones — no extra dependency required.
- **Chessboard** — classic calibration patterns with no embedded IDs: plain
  chessboard (the default), or a symmetric/asymmetric circle grid. Pick the
  pattern from the dropdown; the relevant size fields show/hide accordingly.

Each tab has a **2D / 3D** toggle above the preview. The 3D view shows the
black and white parts as they will print: left-drag to orbit, right-drag to
pan, wheel to zoom. "Exaggerate height" stretches Z so the thin base and
pattern layers are easy to see, and "Reset view" re-frames the board.

On every tab, the preview updates automatically as you change parameters,
and the Board Info panel flags invalid combinations (e.g. not enough
markers in the chosen dictionary) before letting you export.

**Export options (same on every tab):**

- **Export STL** — two files (black + white) for dual-color 3D printing (~2 seconds)
- **Export 3MF** — single file containing both parts (~1 second)
- **Export STEP** — colored CAD assembly via CadQuery (slow, runs in background with progress)

Exported filenames are prefixed by board type and end with the print heights
(`b` = base, `p` = pattern, in mm), e.g. `charuco_16_14_20mm_b4_p0.6_black.stl`,
`arucogrid_5_7_30mm_b4_p0.6_black.stl`, or `chessboard_9_6_p2.4_black.stl` with
the base turned off. STL export asks before overwriting existing files.

### CLI tools

For scripted/batch workflows, given a rendered board PNG (grayscale, black
regions < 128) and a `meta.txt` with three lines — `width_px`, `height_px`,
`px_per_mm`:

```bash
# Generate an STL pair directly from the PNG + metadata
uv run python scripts/png_to_stl.py <board.png> <meta.txt> <black.stl> <white.stl> [pattern_mm] [base_mm]

# Generate 3MF from an existing STL pair
uv run python scripts/build_3mf.py <black.stl> <white.stl> [output.3mf]

# Generate colored STEP from board PNG + metadata (slow)
uv run python scripts/build_step.py <board.png> <meta.txt> <output.step> [pattern_mm] [base_mm]
```

### Tests

```bash
uv run python -m pytest
```

Covers the pure raster generators (`boards/board_types.py`) and the raster
-> polygon -> mesh pipeline (`export/geometry.py`) — no Qt/display required.

## Printing

Load both STL files (or the single 3MF) in your slicer:

- Keep the same origin — don't re-center either part
- Assign black filament to the black part, white filament to the white part
- Print sequence: **By layer**
- **Layer height / Solid white base / Base height / Pattern height** (defaults 0.2 / on / 4.0 / 0.6 mm):
  the two-color pattern is only `Pattern height` tall and sits on a full-board
  white base of `Base height`. The black areas then bond to the white base
  below them instead of only at the side walls, and color/nozzle switching
  only happens in the pattern layers. Set `Layer height` to your slicer's
  value and both heights snap to multiples of it (e.g. 0.6 mm = 3 x 0.2 mm). A thicker base mainly adds stiffness (useful
  for large boards), not color adhesion. Untick the base for the old layout,
  where both colors run the full `Pattern height` and touch only at side walls.
- Add brim for large boards to prevent warping
- Measure printed square size with calipers and update your calibration config if needed

## Project structure

```
main.py                      # Entry point: QMainWindow with one tab per board type
gui/
  gui_common.py              # BoardTab base class: shared preview/export logic
  mesh_view.py               # Interactive 3D mesh preview (pyqtgraph OpenGL)
  tab_charuco.py             # ChArUco tab
  tab_aruco_grid.py          # ArUco / AprilTag tab (same class, different dictionary list)
  tab_fiducial.py            # Chessboard / circle-grid tab
boards/
  board_types.py             # Pure raster generators (ChArUco, ArUco/AprilTag grid, chessboard, circle grid)
export/
  geometry.py                # Pure raster -> polygon -> mesh pipeline (trimesh), shared by GUI + CLI
  cadquery_export.py         # Pure colored-STEP export pipeline (CadQuery), shared by GUI + CLI
  mesh_export.py             # Qt wrapper (StepExportWorker) around cadquery_export.py for the GUI
scripts/
  png_to_stl.py              # CLI: generate an STL pair from a board PNG + metadata
  build_3mf.py               # CLI: generate 3MF from existing STLs
  build_step.py              # CLI: generate colored STEP via CadQuery
tests/                       # pytest suite for boards/board_types.py and export/geometry.py
pyproject.toml               # Python dependencies
```

## Calibration YAML

For OpenCV camera calibration, use a YAML matching your board parameters (note: meters, not mm):

```yaml
dict_type: DICT_5X5_250
squares_x: 16
squares_y: 14
square_size: 0.020
marker_size: 0.015
```

**Naming convention:** OpenCV's `CharucoBoard` and this tool use `squares_x` = columns (horizontal) and `squares_y` = rows (vertical). Swapping these silently transposes the board and corrupts pose estimation.

## Troubleshooting

**"Could not load the Qt platform plugin xcb"** on Linux:

```bash
sudo apt install libxcb-cursor0
```

**macOS:** if `uv sync` fails building a native dependency, make sure Xcode
Command Line Tools are installed (`xcode-select --install`), then retry.

**Windows:** run the commands from PowerShell. If the app window doesn't
appear, check Windows Defender / antivirus isn't blocking the PyQt6 binary,
and that you're on a 64-bit Python (the default `uv` install).

## License

MIT
