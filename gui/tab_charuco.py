from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QComboBox

from boards.board_types import ARUCO_DICTS, generate_charuco_image
from .gui_common import BoardTab


class CharucoTab(BoardTab):
    def _build_param_widgets(self, form):
        self._sq_x = QSpinBox()
        self._sq_x.setRange(3, 30)
        self._sq_x.setValue(16)
        form.addRow("Squares X:", self._sq_x)

        self._sq_y = QSpinBox()
        self._sq_y.setRange(3, 30)
        self._sq_y.setValue(14)
        form.addRow("Squares Y:", self._sq_y)

        self._sq_mm = QDoubleSpinBox()
        self._sq_mm.setRange(5, 100)
        self._sq_mm.setValue(20.0)
        self._sq_mm.setSuffix(" mm")
        form.addRow("Square size:", self._sq_mm)

        self._mk_mm = QDoubleSpinBox()
        self._mk_mm.setRange(3, 80)
        self._mk_mm.setValue(15.0)
        self._mk_mm.setSuffix(" mm")
        form.addRow("Marker size:", self._mk_mm)

        self._dict_cb = QComboBox()
        for name, _, _ in ARUCO_DICTS:
            self._dict_cb.addItem(name)
        self._dict_cb.setCurrentIndex(5)  # DICT_5X5_250
        form.addRow("Dictionary:", self._dict_cb)

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

        for w in (self._sq_x, self._sq_y, self._sq_mm, self._mk_mm, self._ppm):
            w.valueChanged.connect(self._on_param_changed)
        self._dict_cb.currentIndexChanged.connect(self._on_param_changed)
        self._thick.valueChanged.connect(self._on_param_changed)

    def _params(self):
        idx = self._dict_cb.currentIndex()
        name, dict_id, capacity = ARUCO_DICTS[idx]
        return {
            "squares_x": self._sq_x.value(),
            "squares_y": self._sq_y.value(),
            "square_mm": self._sq_mm.value(),
            "marker_mm": self._mk_mm.value(),
            "dict_id": dict_id,
            "dict_name": name,
            "dict_capacity": capacity,
            "thick_mm": self._thick.value(),
            "ppm": self._ppm.value(),
        }

    def _generate_image(self, p):
        return generate_charuco_image(
            p["squares_x"], p["squares_y"],
            p["square_mm"], p["marker_mm"],
            p["dict_id"], p["ppm"],
        )

    def _info_text(self, p):
        sx, sy = p["squares_x"], p["squares_y"]
        board_w = sx * p["square_mm"]
        board_h = sy * p["square_mm"]
        corners = (sx - 1) * (sy - 1)
        markers = (sx * sy) // 2
        cap = p["dict_capacity"]

        warn = ""
        if markers > cap:
            warn = f"\n!! Need {markers} markers but {p['dict_name']} only has {cap} !!"
        if p["marker_mm"] >= p["square_mm"]:
            warn += "\n!! Marker must be smaller than square !!"

        text = (
            f"Board size: {board_w:.0f} x {board_h:.0f} mm\n"
            f"Corners: {corners}\n"
            f"Markers: {markers} / {cap}"
            f"{warn}"
        )
        ok = markers <= cap and p["marker_mm"] < p["square_mm"]
        return text, ok

    def _file_prefix(self, p):
        return f"charuco_{p['squares_x']}_{p['squares_y']}_{int(p['square_mm'])}mm"
