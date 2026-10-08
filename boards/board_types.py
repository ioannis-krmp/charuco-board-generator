"""Pure, Qt-free raster generators for the fiducial/calibration board types.

Every generator returns (img, w, h, ppm): a grayscale uint8 numpy array
(0 = black, 255 = white) plus its pixel dimensions and the px-per-mm used to
build it. That's the only contract `mesh_export.build_meshes` and
`StepExportWorker` care about, so none of this module is Qt- or
board-type-aware beyond producing that raster.
"""
import cv2
import numpy as np


ARUCO_DICTS = [
    ("DICT_4X4_50",   cv2.aruco.DICT_4X4_50,   50),
    ("DICT_4X4_100",  cv2.aruco.DICT_4X4_100,  100),
    ("DICT_4X4_250",  cv2.aruco.DICT_4X4_250,  250),
    ("DICT_5X5_50",   cv2.aruco.DICT_5X5_50,   50),
    ("DICT_5X5_100",  cv2.aruco.DICT_5X5_100,  100),
    ("DICT_5X5_250",  cv2.aruco.DICT_5X5_250,  250),
    ("DICT_6X6_50",   cv2.aruco.DICT_6X6_50,   50),
    ("DICT_6X6_100",  cv2.aruco.DICT_6X6_100,  100),
    ("DICT_6X6_250",  cv2.aruco.DICT_6X6_250,  250),
    ("DICT_7X7_50",   cv2.aruco.DICT_7X7_50,   50),
    ("DICT_7X7_100",  cv2.aruco.DICT_7X7_100,  100),
    ("DICT_7X7_250",  cv2.aruco.DICT_7X7_250,  250),
]

APRILTAG_DICTS = [
    ("DICT_APRILTAG_16h5",  cv2.aruco.DICT_APRILTAG_16h5,  30),
    ("DICT_APRILTAG_25h9",  cv2.aruco.DICT_APRILTAG_25h9,  35),
    ("DICT_APRILTAG_36h10", cv2.aruco.DICT_APRILTAG_36h10, 2320),
    ("DICT_APRILTAG_36h11", cv2.aruco.DICT_APRILTAG_36h11, 587),
]


def generate_charuco_image(squares_x, squares_y, square_mm, marker_mm, dict_id, ppm):
    d = cv2.aruco.getPredefinedDictionary(dict_id)
    try:
        board = cv2.aruco.CharucoBoard(
            (squares_x, squares_y), square_mm, marker_mm, d
        )
    except Exception:
        board = cv2.aruco.CharucoBoard_create(
            squares_x, squares_y, square_mm, marker_mm, d
        )
    w = int(round(squares_x * square_mm * ppm))
    h = int(round(squares_y * square_mm * ppm))
    try:
        img = board.generateImage((w, h), marginSize=0, borderBits=1)
    except Exception:
        img = board.draw((w, h), marginSize=0, borderBits=1)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img, w, h, ppm


def generate_grid_board_image(markers_x, markers_y, marker_mm, separation_mm, dict_id, ppm):
    """ArUco/AprilTag grid board: a plain grid of markers, no checkerboard."""
    d = cv2.aruco.getPredefinedDictionary(dict_id)
    board = cv2.aruco.GridBoard(
        (markers_x, markers_y), marker_mm, separation_mm, d
    )
    board_w = markers_x * marker_mm + (markers_x - 1) * separation_mm
    board_h = markers_y * marker_mm + (markers_y - 1) * separation_mm
    w = int(round(board_w * ppm))
    h = int(round(board_h * ppm))
    img = board.generateImage((w, h), marginSize=0, borderBits=1)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img, w, h, ppm


def generate_chessboard_image(squares_x, squares_y, square_mm, ppm):
    """Classic checkerboard calibration pattern, no embedded IDs."""
    square_px = max(1, int(round(square_mm * ppm)))
    w = squares_x * square_px
    h = squares_y * square_px
    xs = np.arange(w) // square_px
    ys = np.arange(h) // square_px
    parity = (xs[None, :] + ys[:, None]) % 2
    img = np.where(parity == 0, 255, 0).astype(np.uint8)
    return img, w, h, ppm


def generate_circle_grid_image(cols, rows, circle_mm, spacing_mm, ppm, asymmetric):
    """Symmetric or asymmetric filled-circle calibration grid."""
    radius_px = max(1, int(round((circle_mm / 2.0) * ppm)))
    spacing_px = int(round(spacing_mm * ppm))
    margin_px = radius_px + 2

    if asymmetric:
        row_pitch_px = max(1, spacing_px // 2)
        w = (cols - 1) * spacing_px + spacing_px // 2 + 2 * margin_px
        h = (rows - 1) * row_pitch_px + 2 * margin_px
    else:
        row_pitch_px = spacing_px
        w = (cols - 1) * spacing_px + 2 * margin_px
        h = (rows - 1) * row_pitch_px + 2 * margin_px

    img = np.full((h, w), 255, dtype=np.uint8)

    for r in range(rows):
        y = margin_px + r * row_pitch_px
        x_offset = (spacing_px // 2) if (asymmetric and r % 2 == 1) else 0
        for c in range(cols):
            x = margin_px + x_offset + c * spacing_px
            cv2.circle(img, (x, y), radius_px, 0, thickness=-1, lineType=cv2.LINE_8)

    return img, w, h, ppm
