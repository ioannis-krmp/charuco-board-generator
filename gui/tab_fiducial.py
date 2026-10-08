from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QComboBox

from boards.board_types import generate_chessboard_image, generate_circle_grid_image
from .gui_common import BoardTab

MODE_CHESSBOARD = "Chessboard"
MODE_CIRCLES_SYMMETRIC = "Circle Grid — symmetric"
MODE_CIRCLES_ASYMMETRIC = "Circle Grid — asymmetric"


class FiducialTab(BoardTab):
    """Classic (no embedded-ID) calibration patterns: plain checkerboard or
    a symmetric/asymmetric circle grid.
    """

    def _build_param_widgets(self, form):
        self._mode_cb = QComboBox()
        self._mode_cb.addItems([MODE_CHESSBOARD, MODE_CIRCLES_SYMMETRIC, MODE_CIRCLES_ASYMMETRIC])
        form.addRow("Pattern:", self._mode_cb)

        self._cols = QSpinBox()
        self._cols.setRange(2, 40)
        self._cols.setValue(9)
        form.addRow("Columns:", self._cols)

        self._rows = QSpinBox()
        self._rows.setRange(2, 40)
        self._rows.setValue(6)
        form.addRow("Rows:", self._rows)

        self._square_mm = QDoubleSpinBox()
        self._square_mm.setRange(1, 100)
        self._square_mm.setValue(20.0)
        self._square_mm.setSuffix(" mm")
        form.addRow("Square size:", self._square_mm)

        self._circle_mm = QDoubleSpinBox()
        self._circle_mm.setRange(1, 80)
        self._circle_mm.setValue(10.0)
        self._circle_mm.setSuffix(" mm")
        form.addRow("Circle diameter:", self._circle_mm)

        self._spacing_mm = QDoubleSpinBox()
        self._spacing_mm.setRange(1, 100)
        self._spacing_mm.setValue(20.0)
        self._spacing_mm.setSuffix(" mm")
        form.addRow("Spacing:", self._spacing_mm)

        self._thick = QDoubleSpinBox()
        self._thick.setRange(0.5, 10)
        self._thick.setValue(2.5)
        self._thick.setSuffix(" mm")
        form.addRow("Thickness:", self._thick)

        self._ppm = QSpinBox()
        self._ppm.setRange(1, 20)
        self._ppm.setValue(4)
        self._ppm.setSuffix(" px/mm")
        form.addRow("Resolution:", self._ppm)

        for w in (self._cols, self._rows, self._square_mm, self._circle_mm, self._spacing_mm, self._ppm):
            w.valueChanged.connect(self._on_param_changed)
        self._thick.valueChanged.connect(self._on_param_changed)
        self._mode_cb.currentIndexChanged.connect(self._on_mode_changed)
        self._on_mode_changed()

    def _on_mode_changed(self):
        is_chessboard = self._mode_cb.currentText() == MODE_CHESSBOARD
        form = self._square_mm.parentWidget().layout()
        for field, visible in (
            (self._square_mm, is_chessboard),
            (self._circle_mm, not is_chessboard),
            (self._spacing_mm, not is_chessboard),
        ):
            field.setVisible(visible)
            label = form.labelForField(field)
            if label is not None:
                label.setVisible(visible)
        self._on_param_changed()

    def _params(self):
        mode = self._mode_cb.currentText()
        return {
            "mode": mode,
            "cols": self._cols.value(),
            "rows": self._rows.value(),
            "square_mm": self._square_mm.value(),
            "circle_mm": self._circle_mm.value(),
            "spacing_mm": self._spacing_mm.value(),
            "thick_mm": self._thick.value(),
            "ppm": self._ppm.value(),
        }

    def _generate_image(self, p):
        if p["mode"] == MODE_CHESSBOARD:
            return generate_chessboard_image(p["cols"], p["rows"], p["square_mm"], p["ppm"])
        asymmetric = p["mode"] == MODE_CIRCLES_ASYMMETRIC
        return generate_circle_grid_image(
            p["cols"], p["rows"], p["circle_mm"], p["spacing_mm"], p["ppm"], asymmetric
        )

    def _info_text(self, p):
        if p["mode"] == MODE_CHESSBOARD:
            board_w = p["cols"] * p["square_mm"]
            board_h = p["rows"] * p["square_mm"]
            text = f"Board size: {board_w:.0f} x {board_h:.0f} mm\nSquares: {p['cols']} x {p['rows']}"
            ok = True
        else:
            if p["circle_mm"] >= p["spacing_mm"]:
                text = "!! Circle diameter must be smaller than spacing !!"
                return text, False
            board_w = (p["cols"] - 1) * p["spacing_mm"] + p["circle_mm"]
            board_h = (p["rows"] - 1) * p["spacing_mm"] + p["circle_mm"]
            text = (
                f"Approx board size: {board_w:.0f} x {board_h:.0f} mm\n"
                f"Circles: {p['cols']} x {p['rows']}"
            )
            ok = True
        return text, ok

    def _file_prefix(self, p):
        tag = {
            MODE_CHESSBOARD: "chessboard",
            MODE_CIRCLES_SYMMETRIC: "circlegrid_sym",
            MODE_CIRCLES_ASYMMETRIC: "circlegrid_asym",
        }[p["mode"]]
        return f"{tag}_{p['cols']}_{p['rows']}"
