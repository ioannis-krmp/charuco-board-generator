"""Tests for the pure raster -> polygon -> mesh pipeline in geometry.py."""
import numpy as np
import pytest
from shapely.geometry import MultiPolygon, Polygon

from export.geometry import image_to_polygons, build_meshes, extrude_polygon
from boards.board_types import generate_chessboard_image


def test_image_to_polygons_all_white_raises():
    img = np.full((10, 10), 255, dtype=np.uint8)
    with pytest.raises(ValueError):
        image_to_polygons(img, 10, 10, ppm=2)


def test_image_to_polygons_partitions_full_area():
    img, w, h, ppm = generate_chessboard_image(squares_x=3, squares_y=3, square_mm=10.0, ppm=2)
    black_poly, white_poly = image_to_polygons(img, w, h, ppm)
    board_w, board_h = w / ppm, h / ppm
    total_area = board_w * board_h
    assert abs(black_poly.area + white_poly.area - total_area) < 1e-6


def test_build_meshes_valid_volumes():
    img, w, h, ppm = generate_chessboard_image(squares_x=4, squares_y=4, square_mm=10.0, ppm=2)
    black_mesh, white_mesh = build_meshes(img, w, h, ppm, pattern_mm=2.5)
    assert black_mesh.volume > 0
    assert white_mesh.volume > 0

    board_w, board_h = w / ppm, h / ppm
    total_volume = board_w * board_h * 2.5
    assert abs(black_mesh.volume + white_mesh.volume - total_volume) < 1.0


def test_extrude_polygon_handles_polygon_and_multipolygon():
    single = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    mesh = extrude_polygon(single, 2.0)
    assert mesh.volume == pytest.approx(2.0, rel=1e-6)

    multi = MultiPolygon([
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),
    ])
    mesh2 = extrude_polygon(multi, 2.0)
    assert mesh2.volume == pytest.approx(4.0, rel=1e-6)


def test_extrude_polygon_rejects_other_types():
    with pytest.raises(TypeError):
        extrude_polygon("not a polygon", 1.0)


def test_build_meshes_with_base_adds_white_base():
    img, w, h, ppm = generate_chessboard_image(squares_x=4, squares_y=4, square_mm=10.0, ppm=2)
    black_mesh, white_mesh = build_meshes(img, w, h, ppm, pattern_mm=0.6, base_mm=1.8)

    # Black only occupies the top 0.6 mm; white spans the full height.
    assert black_mesh.bounds[0][2] == pytest.approx(1.8)
    assert black_mesh.bounds[1][2] == pytest.approx(2.4)
    assert white_mesh.bounds[0][2] == pytest.approx(0.0)
    assert white_mesh.bounds[1][2] == pytest.approx(2.4)

    board_w, board_h = w / ppm, h / ppm
    assert abs(black_mesh.volume + white_mesh.volume - board_w * board_h * 2.4) < 1.0
    assert black_mesh.volume == pytest.approx(board_w * board_h * 0.6 / 2, rel=0.05)


def test_build_meshes_without_base_is_full_height():
    img, w, h, ppm = generate_chessboard_image(squares_x=4, squares_y=4, square_mm=10.0, ppm=2)
    black_mesh, white_mesh = build_meshes(img, w, h, ppm, pattern_mm=2.5, base_mm=0.0)
    for mesh in (black_mesh, white_mesh):
        assert mesh.bounds[0][2] == pytest.approx(0.0)
        assert mesh.bounds[1][2] == pytest.approx(2.5)


@pytest.mark.parametrize("pattern_mm,base_mm", [(0, 1.0), (-1, 0), (0.6, -0.2)])
def test_build_meshes_rejects_bad_heights(pattern_mm, base_mm):
    img, w, h, ppm = generate_chessboard_image(squares_x=4, squares_y=4, square_mm=10.0, ppm=2)
    with pytest.raises(ValueError):
        build_meshes(img, w, h, ppm, pattern_mm=pattern_mm, base_mm=base_mm)


def test_board_bounds_matches_full_board():
    from export.geometry import board_bounds
    img, w, h, ppm = generate_chessboard_image(squares_x=3, squares_y=3, square_mm=10.0, ppm=2)
    black_poly, white_poly = image_to_polygons(img, w, h, ppm)
    assert board_bounds(black_poly, white_poly) == pytest.approx(black_poly.union(white_poly).bounds)
