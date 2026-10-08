"""Shared QWidget base class for a single board-type tab: parameter form,
live preview, board-info panel, and STL/3MF/STEP export — all generic over
how the raster image is produced. Subclasses only need to supply the
parameter widgets and a raster generator function.
"""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QPushButton, QFileDialog, QSizePolicy, QMessageBox, QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

from export.geometry import build_meshes
from export.mesh_export import StepExportWorker


class BoardTab(QWidget):
    """Subclasses must implement:
    - _build_param_widgets(form): add rows to the Parameters QFormLayout,
      and connect each widget's change signal to self._on_param_changed
    - _params() -> dict
    - _generate_image(params) -> (img, w, h, ppm)
    - _info_text(params) -> (text: str, ok: bool)
    - _file_prefix(params) -> str
    """

    def __init__(self, status_bar, progress_bar, parent=None):
        super().__init__(parent)
        self._status = status_bar
        self._progress = progress_bar

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

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        params_grp = QGroupBox("Parameters")
        form = QFormLayout(params_grp)
        info_grp = self._create_info_group()
        export_grp = self._create_export_group()
        self._build_param_widgets(form)
        left.addWidget(params_grp)
        left.addWidget(info_grp)
        left.addWidget(export_grp)
        left.addStretch()
        layout.addLayout(left, stretch=0)

        self._preview = QLabel("Click 'Generate' or change parameters")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._preview.setStyleSheet("background: #222; color: #aaa; border: 1px solid #555;")
        layout.addWidget(self._preview, stretch=1)

        self._update_info()
        self._generate_preview()

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

    def _on_param_changed(self):
        self._update_info()
        self._black_mesh = None
        self._white_mesh = None
        self._debounce.start()

    def _update_info(self):
        p = self._params()
        text, ok = self._info_text(p)
        self._info_label.setText(text)
        for btn in (self._btn_stl, self._btn_3mf, self._btn_step):
            btn.setEnabled(ok)

    def _generate_preview(self):
        p = self._params()
        _, ok = self._info_text(p)
        if not ok:
            return

        try:
            img, w, h, ppm = self._generate_image(p)
            self._board_img = img
            self._board_w = w
            self._board_h = h

            self._render_pixmap()
            self._status.showMessage("Preview updated", 2000)
        except Exception as e:
            self._status.showMessage(f"Preview error: {e}")

    def _render_pixmap(self):
        qimg = QImage(
            self._board_img.data,
            self._board_w, self._board_h,
            self._board_w,
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
        if self._board_img is not None:
            self._render_pixmap()

    def _ensure_meshes(self):
        if self._black_mesh is not None:
            return True
        if self._board_img is None:
            self._generate_preview()
        if self._board_img is None:
            return False

        p = self._params()
        self._status.showMessage("Building meshes...")
        QApplication.processEvents()
        self._black_mesh, self._white_mesh = build_meshes(
            self._board_img, self._board_w, self._board_h,
            p["ppm"], p["thick_mm"],
        )
        self._status.showMessage("Meshes ready", 2000)
        return True

    def _export_stl(self):
        directory = QFileDialog.getExistingDirectory(self, "Export STL — choose folder")
        if not directory:
            return
        if not self._ensure_meshes():
            return

        prefix = self._file_prefix(self._params())
        black_path = os.path.join(directory, f"{prefix}_black.stl")
        white_path = os.path.join(directory, f"{prefix}_white.stl")

        self._black_mesh.export(black_path)
        self._white_mesh.export(white_path)
        self._status.showMessage(f"Exported: {black_path}, {white_path}", 5000)

    def _export_3mf(self):
        import trimesh

        prefix = self._file_prefix(self._params())
        path, _ = QFileDialog.getSaveFileName(
            self, "Export 3MF", f"{prefix}_board.3mf", "3MF files (*.3mf)"
        )
        if not path:
            return
        if not self._ensure_meshes():
            return

        scene = trimesh.Scene()
        scene.add_geometry(self._black_mesh, node_name="black", geom_name=f"{prefix}_black")
        scene.add_geometry(self._white_mesh, node_name="white", geom_name=f"{prefix}_white")
        scene.export(path)
        self._status.showMessage(f"Exported: {path}", 5000)

    def _export_step(self):
        prefix = self._file_prefix(self._params())
        path, _ = QFileDialog.getSaveFileName(
            self, "Export STEP", f"{prefix}_board.step", "STEP files (*.step)"
        )
        if not path:
            return
        if self._board_img is None:
            self._generate_preview()
        if self._board_img is None:
            return

        p = self._params()
        self._btn_step.setEnabled(False)
        self._progress.setVisible(True)

        self._step_worker = StepExportWorker(
            self._board_img, self._board_w, self._board_h,
            p["ppm"], p["thick_mm"], path,
        )
        self._step_worker.progress.connect(
            lambda msg: self._status.showMessage(msg)
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
