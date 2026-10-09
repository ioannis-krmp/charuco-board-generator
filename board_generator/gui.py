import os

import trimesh
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QLabel, QPushButton, QFileDialog, QProgressBar, QStatusBar,
    QSizePolicy, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

from board_generator.boards import (
    BoardType, generate_charuco, generate_aruco_grid, generate_checkerboard,
    generate_single_marker,
)
from board_generator.dictionaries import ALL_DICTS
from board_generator.mesh import build_meshes

from board_generator.step_export import StepExportWorker


class BoardGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Board Generator")
        self.setMinimumSize(900, 600)

        self._board_img = None
        self._board_w = 0
        self._board_h = 0
        self._black_mesh = None
        self._white_mesh = None
        self._step_worker = None
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._generate_preview)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        left = QVBoxLayout()
        left.addWidget(self._create_params_group())
        left.addWidget(self._create_info_group())
        left.addWidget(self._create_export_group())
        left.addStretch()
        layout.addLayout(left, stretch=0)

        self._preview = QLabel("Generating preview...")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )
        self._preview.setStyleSheet(
            "background: #222; color: #aaa; border: 1px solid #555;"
        )
        layout.addWidget(self._preview, stretch=1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        self._status = QStatusBar()
        self._status.addPermanentWidget(self._progress)
        self.setStatusBar(self._status)

        self._update_param_visibility()
        self._update_info()
        self._generate_preview()

    # ── parameter panel ─────────────────────────────────────────────

    def _create_params_group(self):
        grp = QGroupBox("Parameters")
        self._form = QFormLayout(grp)

        self._board_type_cb = QComboBox()
        for bt in BoardType:
            self._board_type_cb.addItem(bt.value)
        self._form.addRow("Board type:", self._board_type_cb)

        self._sq_x = QSpinBox()
        self._sq_x.setRange(2, 30)
        self._sq_x.setValue(16)
        self._label_sq_x = QLabel("Squares X:")
        self._form.addRow(self._label_sq_x, self._sq_x)

        self._sq_y = QSpinBox()
        self._sq_y.setRange(2, 30)
        self._sq_y.setValue(14)
        self._label_sq_y = QLabel("Squares Y:")
        self._form.addRow(self._label_sq_y, self._sq_y)

        self._sq_mm = QDoubleSpinBox()
        self._sq_mm.setRange(5, 100)
        self._sq_mm.setValue(20.0)
        self._sq_mm.setSuffix(" mm")
        self._label_sq_mm = QLabel("Square size:")
        self._form.addRow(self._label_sq_mm, self._sq_mm)

        self._mk_mm = QDoubleSpinBox()
        self._mk_mm.setRange(3, 80)
        self._mk_mm.setValue(15.0)
        self._mk_mm.setSuffix(" mm")
        self._label_mk_mm = QLabel("Marker size:")
        self._form.addRow(self._label_mk_mm, self._mk_mm)

        self._spacing_mm = QDoubleSpinBox()
        self._spacing_mm.setRange(1, 50)
        self._spacing_mm.setValue(5.0)
        self._spacing_mm.setSuffix(" mm")
        self._label_spacing = QLabel("Spacing:")
        self._form.addRow(self._label_spacing, self._spacing_mm)

        self._dict_cb = QComboBox()
        from board_generator.dictionaries import ARUCO_DICTS, APRILTAG_DICTS
        for name, _, _ in ARUCO_DICTS:
            self._dict_cb.addItem(name)
        self._dict_cb.insertSeparator(len(ARUCO_DICTS))
        for name, _, _ in APRILTAG_DICTS:
            self._dict_cb.addItem(name)
        self._dict_cb.setCurrentIndex(6)  # DICT_5X5_250
        self._label_dict = QLabel("Dictionary:")
        self._form.addRow(self._label_dict, self._dict_cb)

        self._marker_id = QSpinBox()
        self._marker_id.setRange(0, 249)
        self._marker_id.setValue(0)
        self._label_marker_id = QLabel("Marker ID:")
        self._form.addRow(self._label_marker_id, self._marker_id)

        self._thick = QDoubleSpinBox()
        self._thick.setRange(0.5, 10)
        self._thick.setValue(2.5)
        self._thick.setSuffix(" mm")
        self._form.addRow("Thickness:", self._thick)

        self._ppm = QSpinBox()
        self._ppm.setRange(1, 20)
        self._ppm.setValue(4)
        self._ppm.setSuffix(" px/mm")
        self._form.addRow("Resolution:", self._ppm)

        self._board_type_cb.currentIndexChanged.connect(self._on_board_type_changed)
        for w in (self._sq_x, self._sq_y, self._sq_mm, self._mk_mm,
                  self._spacing_mm, self._marker_id, self._ppm):
            w.valueChanged.connect(self._on_param_changed)
        self._dict_cb.currentIndexChanged.connect(self._on_param_changed)
        self._thick.valueChanged.connect(self._on_param_changed)

        return grp

    def _create_info_group(self):
        grp = QGroupBox("Board Info")
        layout = QVBoxLayout(grp)
        self._info_label = QLabel()
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)
        return grp

    def _create_export_group(self):
        grp = QGroupBox("Export")
        layout = QVBoxLayout(grp)

        self._btn_stl = QPushButton("Export STL files")
        self._btn_stl.clicked.connect(self._export_stl)
        layout.addWidget(self._btn_stl)

        self._btn_3mf = QPushButton("Export 3MF file")
        self._btn_3mf.clicked.connect(self._export_3mf)
        layout.addWidget(self._btn_3mf)

        self._btn_step = QPushButton("Export STEP file (slow)")
        self._btn_step.clicked.connect(self._export_step)
        layout.addWidget(self._btn_step)

        return grp

    # ── board-type switching ────────────────────────────────────────

    def _current_board_type(self):
        return list(BoardType)[self._board_type_cb.currentIndex()]

    def _current_dict(self):
        idx = self._dict_cb.currentIndex()
        from board_generator.dictionaries import ARUCO_DICTS
        if idx > len(ARUCO_DICTS):
            idx -= 1  # skip separator
        return ALL_DICTS[idx]

    def _on_board_type_changed(self):
        self._update_param_visibility()
        self._on_param_changed()

    def _update_param_visibility(self):
        bt = self._current_board_type()
        is_aruco = bt == BoardType.ARUCO_GRID
        is_checker = bt == BoardType.CHECKERBOARD
        is_single = bt == BoardType.SINGLE_MARKER

        self._label_sq_x.setText("Columns:" if is_aruco else "Squares X:")
        self._label_sq_y.setText("Rows:" if is_aruco else "Squares Y:")
        self._label_mk_mm.setText("Size:" if is_single else "Marker size:")

        for w in (self._label_sq_x, self._sq_x, self._label_sq_y, self._sq_y):
            w.setVisible(not is_single)

        for w in (self._label_sq_mm, self._sq_mm):
            w.setVisible(not is_aruco and not is_single)

        for w in (self._label_mk_mm, self._mk_mm):
            w.setVisible(not is_checker)

        for w in (self._label_spacing, self._spacing_mm):
            w.setVisible(is_aruco)

        for w in (self._label_dict, self._dict_cb):
            w.setVisible(not is_checker)

        for w in (self._label_marker_id, self._marker_id):
            w.setVisible(is_single)

    # ── parameter changes ───────────────────────────────────────────

    def _on_param_changed(self):
        self._update_info()
        self._black_mesh = None
        self._white_mesh = None
        self._debounce.start()

    def _is_valid(self):
        bt = self._current_board_type()
        _, _, capacity = self._current_dict()

        if bt == BoardType.CHARUCO:
            sx, sy = self._sq_x.value(), self._sq_y.value()
            return (self._mk_mm.value() < self._sq_mm.value()
                    and (sx * sy) // 2 <= capacity)
        if bt == BoardType.ARUCO_GRID:
            return (self._sq_x.value() * self._sq_y.value()) <= capacity
        if bt == BoardType.SINGLE_MARKER:
            return self._marker_id.value() < capacity
        return True

    def _update_info(self):
        bt = self._current_board_type()
        sx, sy = self._sq_x.value(), self._sq_y.value()
        dict_name, _, capacity = self._current_dict()
        warn = ""

        if bt == BoardType.CHARUCO:
            sq = self._sq_mm.value()
            mk = self._mk_mm.value()
            markers = (sx * sy) // 2
            corners = (sx - 1) * (sy - 1)
            if markers > capacity:
                warn = (f"\n!! Need {markers} markers but "
                        f"{dict_name} only has {capacity} !!")
            if mk >= sq:
                warn += "\n!! Marker must be smaller than square !!"
            self._info_label.setText(
                f"Board size: {sx * sq:.0f} x {sy * sq:.0f} mm\n"
                f"Corners: {corners}\n"
                f"Markers: {markers} / {capacity}{warn}"
            )

        elif bt == BoardType.ARUCO_GRID:
            mk = self._mk_mm.value()
            sp = self._spacing_mm.value()
            bw = sx * mk + (sx - 1) * sp
            bh = sy * mk + (sy - 1) * sp
            markers = sx * sy
            if markers > capacity:
                warn = (f"\n!! Need {markers} markers but "
                        f"{dict_name} only has {capacity} !!")
            self._info_label.setText(
                f"Board size: {bw:.1f} x {bh:.1f} mm\n"
                f"Markers: {markers} / {capacity}{warn}"
            )

        elif bt == BoardType.SINGLE_MARKER:
            mk = self._mk_mm.value()
            mid = self._marker_id.value()
            self._marker_id.setMaximum(max(capacity - 1, 0))
            if mid >= capacity:
                warn = (f"\n!! Marker ID {mid} exceeds "
                        f"{dict_name} capacity ({capacity}) !!")
            self._info_label.setText(
                f"Size: {mk:.1f} x {mk:.1f} mm\n"
                f"Marker ID: {mid} / {capacity}{warn}"
            )

        else:
            sq = self._sq_mm.value()
            corners = (sx - 1) * (sy - 1)
            self._info_label.setText(
                f"Board size: {sx * sq:.0f} x {sy * sq:.0f} mm\n"
                f"Corners: {corners}"
            )

        ok = self._is_valid()
        for btn in (self._btn_stl, self._btn_3mf, self._btn_step):
            btn.setEnabled(ok)

    # ── preview ─────────────────────────────────────────────────────

    def _generate_preview(self):
        if not self._is_valid():
            return
        bt = self._current_board_type()
        ppm = self._ppm.value()
        sx, sy = self._sq_x.value(), self._sq_y.value()

        try:
            if bt == BoardType.CHARUCO:
                _, dict_id, _ = self._current_dict()
                img, w, h = generate_charuco(
                    sx, sy, self._sq_mm.value(), self._mk_mm.value(),
                    dict_id, ppm,
                )
            elif bt == BoardType.ARUCO_GRID:
                _, dict_id, _ = self._current_dict()
                img, w, h = generate_aruco_grid(
                    sx, sy, self._mk_mm.value(), self._spacing_mm.value(),
                    dict_id, ppm,
                )
            elif bt == BoardType.SINGLE_MARKER:
                _, dict_id, _ = self._current_dict()
                img, w, h = generate_single_marker(
                    self._marker_id.value(), self._mk_mm.value(),
                    dict_id, ppm,
                )
            else:
                img, w, h = generate_checkerboard(
                    sx, sy, self._sq_mm.value(), ppm,
                )

            self._board_img = img
            self._board_w = w
            self._board_h = h
            self._show_preview()
            self._status.showMessage("Preview updated", 2000)
        except Exception as e:
            self._status.showMessage(f"Preview error: {e}")

    def _show_preview(self):
        if self._board_img is None:
            return
        qimg = QImage(
            self._board_img.data,
            self._board_w, self._board_h, self._board_w,
            QImage.Format.Format_Grayscale8,
        )
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            self._preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._show_preview()

    # ── mesh / export ───────────────────────────────────────────────

    def _ensure_meshes(self):
        if self._black_mesh is not None:
            return True
        if self._board_img is None:
            self._generate_preview()
        if self._board_img is None:
            return False

        self._status.showMessage("Building meshes...")
        QApplication.processEvents()
        self._black_mesh, self._white_mesh = build_meshes(
            self._board_img, self._board_w, self._board_h,
            self._ppm.value(), self._thick.value(),
        )
        self._status.showMessage("Meshes ready", 2000)
        return True

    def _file_prefix(self):
        bt = self._current_board_type()
        sx, sy = self._sq_x.value(), self._sq_y.value()
        if bt == BoardType.CHARUCO:
            return f"charuco_{sx}_{sy}_{int(self._sq_mm.value())}mm"
        if bt == BoardType.ARUCO_GRID:
            return f"aruco_grid_{sx}_{sy}_{int(self._mk_mm.value())}mm"
        if bt == BoardType.SINGLE_MARKER:
            dict_name = self._current_dict()[0]
            return f"marker_{dict_name}_id{self._marker_id.value()}_{int(self._mk_mm.value())}mm"
        return f"checkerboard_{sx}_{sy}_{int(self._sq_mm.value())}mm"

    def _export_stl(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Export STL — choose folder",
        )
        if not directory or not self._ensure_meshes():
            return

        prefix = self._file_prefix()
        black_path = os.path.join(directory, f"{prefix}_black.stl")
        white_path = os.path.join(directory, f"{prefix}_white.stl")
        self._black_mesh.export(black_path)
        self._white_mesh.export(white_path)
        self._status.showMessage(f"Exported: {black_path}, {white_path}", 5000)

    def _export_3mf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export 3MF",
            f"{self._file_prefix()}_board.3mf", "3MF files (*.3mf)",
        )
        if not path or not self._ensure_meshes():
            return

        prefix = self._file_prefix()
        scene = trimesh.Scene()
        scene.add_geometry(
            self._black_mesh, node_name="black", geom_name=f"{prefix}_black",
        )
        scene.add_geometry(
            self._white_mesh, node_name="white", geom_name=f"{prefix}_white",
        )
        scene.export(path)
        self._status.showMessage(f"Exported: {path}", 5000)

    def _export_step(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export STEP",
            f"{self._file_prefix()}_board.step", "STEP files (*.step)",
        )
        if not path:
            return
        if self._board_img is None:
            self._generate_preview()
        if self._board_img is None:
            return

        self._btn_step.setEnabled(False)
        self._progress.setVisible(True)

        self._step_worker = StepExportWorker(
            self._board_img, self._board_w, self._board_h,
            self._ppm.value(), self._thick.value(), path,
        )
        self._step_worker.progress.connect(
            lambda msg: self._status.showMessage(msg),
        )
        self._step_worker.finished.connect(self._on_step_done)
        self._step_worker.error.connect(self._on_step_error)
        self._step_worker.start()

    def _on_step_done(self, path):
        self._progress.setVisible(False)
        self._btn_step.setEnabled(True)
        self._status.showMessage(f"STEP exported: {path}", 5000)

    def _on_step_error(self, msg):
        self._progress.setVisible(False)
        self._btn_step.setEnabled(True)
        self._status.showMessage(f"STEP error: {msg}")
        QMessageBox.critical(self, "STEP Export Error", msg)
