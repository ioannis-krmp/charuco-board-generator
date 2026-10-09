from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QComboBox

from boards.board_types import generate_grid_board_image
from .gui_common import BoardTab


class ArucoGridTab(BoardTab):
    """Marker-only grid board (no checkerboard). Instantiated once per
    dictionary family — e.g. ARUCO_DICTS for the "ArUco" tab,
    APRILTAG_DICTS for the "AprilTag" tab — since both just point the same
    cv2.aruco.GridBoard generator at a different dictionary list.
    """

    def __init__(self, status_bar, progress_bar, dicts, file_prefix, default_dict_index=0, parent=None):
        self._dicts = dicts
        self._file_prefix_tag = file_prefix
        self._default_dict_index = default_dict_index
        super().__init__(status_bar, progress_bar, parent)

    def _build_param_widgets(self, form):
        self._mk_x = QSpinBox()
        self._mk_x.setRange(1, 30)
        self._mk_x.setValue(5)
        form.addRow("Markers X:", self._mk_x)

        self._mk_y = QSpinBox()
        self._mk_y.setRange(1, 30)
        self._mk_y.setValue(7)
        form.addRow("Markers Y:", self._mk_y)

        self._mk_mm = QDoubleSpinBox()
        self._mk_mm.setRange(3, 100)
        self._mk_mm.setValue(30.0)
        self._mk_mm.setSuffix(" mm")
        form.addRow("Marker size:", self._mk_mm)

        self._sep_mm = QDoubleSpinBox()
        self._sep_mm.setRange(0, 50)
        self._sep_mm.setValue(6.0)
        self._sep_mm.setSuffix(" mm")
        form.addRow("Separation:", self._sep_mm)

        self._dict_cb = QComboBox()
        for name, _, _ in self._dicts:
            self._dict_cb.addItem(name)
        self._dict_cb.setCurrentIndex(self._default_dict_index)
        form.addRow("Dictionary:", self._dict_cb)

        self._ppm = QSpinBox()
        self._ppm.setRange(1, 20)
        self._ppm.setValue(4)
        self._ppm.setSuffix(" px/mm")
        form.addRow("Resolution:", self._ppm)

        for w in (self._mk_x, self._mk_y, self._mk_mm, self._sep_mm, self._ppm):
            w.valueChanged.connect(self._on_param_changed)
        self._dict_cb.currentIndexChanged.connect(self._on_param_changed)

    def _params(self):
        idx = self._dict_cb.currentIndex()
        name, dict_id, capacity = self._dicts[idx]
        return {
            "markers_x": self._mk_x.value(),
            "markers_y": self._mk_y.value(),
            "marker_mm": self._mk_mm.value(),
            "separation_mm": self._sep_mm.value(),
            "dict_id": dict_id,
            "dict_name": name,
            "dict_capacity": capacity,
            "ppm": self._ppm.value(),
        }

    def _generate_image(self, p):
        return generate_grid_board_image(
            p["markers_x"], p["markers_y"],
            p["marker_mm"], p["separation_mm"],
            p["dict_id"], p["ppm"],
        )

    def _info_text(self, p):
        mx, my = p["markers_x"], p["markers_y"]
        board_w = mx * p["marker_mm"] + (mx - 1) * p["separation_mm"]
        board_h = my * p["marker_mm"] + (my - 1) * p["separation_mm"]
        markers = mx * my
        cap = p["dict_capacity"]

        warn = ""
        if markers > cap:
            warn = f"\n!! Need {markers} markers but {p['dict_name']} only has {cap} !!"

        text = (
            f"Board size: {board_w:.0f} x {board_h:.0f} mm\n"
            f"Markers: {markers} / {cap}"
            f"{warn}"
        )
        ok = markers <= cap
        return text, ok

    def _file_prefix(self, p):
        return f"{self._file_prefix_tag}_{p['markers_x']}_{p['markers_y']}_{int(p['marker_mm'])}mm"
