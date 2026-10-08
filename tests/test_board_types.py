"""Tests for the pure, Qt-free raster generators in board_types.py.
No display or Qt required — these run in plain CI.
"""
import cv2
import numpy as np
import pytest

from boards.board_types import (
    ARUCO_DICTS,
    APRILTAG_DICTS,
    generate_charuco_image,
    generate_grid_board_image,
    generate_chessboard_image,
    generate_circle_grid_image,
)


def test_dict_capacities_match_opencv():
    """Catches drift if a future OpenCV changes a predefined dict's size."""
    for name, dict_id, capacity in ARUCO_DICTS + APRILTAG_DICTS:
        d = cv2.aruco.getPredefinedDictionary(dict_id)
        assert d.bytesList.shape[0] == capacity, name


def test_generate_charuco_image_shape_and_values():
    img, w, h, ppm = generate_charuco_image(
        squares_x=6, squares_y=5, square_mm=20.0, marker_mm=15.0,
        dict_id=cv2.aruco.DICT_4X4_50, ppm=4,
    )
    assert img.shape == (h, w)
    assert img.dtype == np.uint8
    assert w == round(6 * 20.0 * 4)
    assert h == round(5 * 20.0 * 4)
    assert img.min() == 0
    assert img.max() == 255


def test_generate_grid_board_image_shape():
    img, w, h, ppm = generate_grid_board_image(
        markers_x=3, markers_y=4, marker_mm=30.0, separation_mm=6.0,
        dict_id=cv2.aruco.DICT_5X5_250, ppm=4,
    )
    assert img.shape == (h, w)
    expected_w = round((3 * 30.0 + 2 * 6.0) * 4)
    expected_h = round((4 * 30.0 + 3 * 6.0) * 4)
    assert w == expected_w
    assert h == expected_h
    assert img.min() == 0  # markers present


def test_generate_grid_board_image_apriltag_dict():
    img, w, h, ppm = generate_grid_board_image(
        markers_x=2, markers_y=2, marker_mm=30.0, separation_mm=5.0,
        dict_id=cv2.aruco.DICT_APRILTAG_36h11, ppm=4,
    )
    assert img.shape == (h, w)
    assert img.min() == 0


def test_generate_chessboard_image_is_binary_and_alternating():
    img, w, h, ppm = generate_chessboard_image(squares_x=4, squares_y=3, square_mm=10.0, ppm=2)
    square_px = round(10.0 * 2)
    assert w == 4 * square_px
    assert h == 3 * square_px
    assert set(np.unique(img)) <= {0, 255}

    # top-left square is white (parity 0,0 -> 255 per generator), neighbor is black
    assert img[0, 0] == 255
    assert img[0, square_px] == 0
    assert img[square_px, 0] == 0


def test_generate_chessboard_image_min_size():
    img, w, h, ppm = generate_chessboard_image(squares_x=2, squares_y=2, square_mm=5.0, ppm=1)
    assert img.shape == (h, w)
    assert w > 0 and h > 0


@pytest.mark.parametrize("asymmetric", [False, True])
def test_generate_circle_grid_image(asymmetric):
    img, w, h, ppm = generate_circle_grid_image(
        cols=4, rows=3, circle_mm=8.0, spacing_mm=15.0, ppm=3, asymmetric=asymmetric
    )
    assert img.shape == (h, w)
    assert img.dtype == np.uint8
    assert img.min() == 0  # circles drawn
    assert img.max() == 255  # white background present


def test_circle_grid_symmetric_vs_asymmetric_differ():
    kwargs = dict(cols=4, rows=4, circle_mm=8.0, spacing_mm=20.0, ppm=3)
    sym_img, sym_w, sym_h, _ = generate_circle_grid_image(asymmetric=False, **kwargs)
    asym_img, asym_w, asym_h, _ = generate_circle_grid_image(asymmetric=True, **kwargs)
    assert (sym_w, sym_h) != (asym_w, asym_h)
