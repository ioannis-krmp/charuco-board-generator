from enum import Enum

import cv2
import numpy as np


class BoardType(Enum):
    CHARUCO = "CharUco"
    ARUCO_GRID = "ArUco Grid"
    CHECKERBOARD = "Checkerboard"
    SINGLE_MARKER = "Single Marker"


def generate_charuco(squares_x, squares_y, square_mm, marker_mm, dict_id, ppm):
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
    return img, w, h


def generate_aruco_grid(columns, rows, marker_mm, spacing_mm, dict_id, ppm):
    d = cv2.aruco.getPredefinedDictionary(dict_id)
    try:
        board = cv2.aruco.GridBoard(
            (columns, rows), marker_mm, spacing_mm, d
        )
    except Exception:
        board = cv2.aruco.GridBoard_create(
            columns, rows, marker_mm, spacing_mm, d
        )
    board_w_mm = columns * marker_mm + (columns - 1) * spacing_mm
    board_h_mm = rows * marker_mm + (rows - 1) * spacing_mm
    w = int(round(board_w_mm * ppm))
    h = int(round(board_h_mm * ppm))
    try:
        img = board.generateImage((w, h), marginSize=0, borderBits=1)
    except Exception:
        img = board.draw((w, h), marginSize=0, borderBits=1)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img, w, h


def generate_checkerboard(squares_x, squares_y, square_mm, ppm):
    sq_px = int(round(square_mm * ppm))
    w = squares_x * sq_px
    h = squares_y * sq_px
    img = np.ones((h, w), dtype=np.uint8) * 255
    for row in range(squares_y):
        for col in range(squares_x):
            if (row + col) % 2 == 0:
                y0 = row * sq_px
                x0 = col * sq_px
                img[y0:y0 + sq_px, x0:x0 + sq_px] = 0
    return img, w, h


def generate_single_marker(marker_id, size_mm, dict_id, ppm, border_bits=1):
    d = cv2.aruco.getPredefinedDictionary(dict_id)
    side_px = int(round(size_mm * ppm))
    try:
        img = cv2.aruco.generateImageMarker(d, marker_id, side_px, borderBits=border_bits)
    except Exception:
        img = cv2.aruco.drawMarker(d, marker_id, side_px, borderBits=border_bits)
    return img, side_px, side_px
