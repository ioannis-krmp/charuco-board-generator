"""Shared QWidget base class for a single board-type tab: parameter form,
live preview, board-info panel, and STL/3MF/STEP export — all generic over
how the raster image is produced. Subclasses only need to supply the
parameter widgets and a raster generator function.
"""
import math
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QPushButton, QFileDialog, QSizePolicy, QMessageBox,
    QDoubleSpinBox, QCheckBox, QStackedWidget, QButtonGroup,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

from export.geometry import build_meshes
from export.mesh_export import StepExportWorker
from .theme import PREVIEW_STYLE

try:
    from .mesh_view import MeshView, opengl_available
except Exception:  # pyqtgraph/PyOpenGL missing: 2D preview only
    MeshView = None


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
        self._build_print_widgets(form)
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
        self._preview.setStyleSheet(PREVIEW_STYLE)

        self._view_3d = False
        self._mesh_view = None
        right = QVBoxLayout()
        self._stack = QStackedWidget()
        self._stack.addWidget(self._preview)
        if MeshView is not None and opengl_available():
            right.addLayout(self._create_view_toggle())
        right.addWidget(self._stack, stretch=1)
        layout.addLayout(right, stretch=1)

        self._update_info()
        self._generate_preview()

    def _create_view_toggle(self):
        row = QHBoxLayout()
        self._btn_2d = QPushButton("2D")
        self._btn_3d = QPushButton("3D")
        group = QButtonGroup(self)
        for btn in (self._btn_2d, self._btn_3d):
            btn.setCheckable(True)
            group.addButton(btn)
            row.addWidget(btn)
        self._btn_2d.setChecked(True)
        row.addStretch()
        self._btn_3d.toggled.connect(self._set_3d)
        return row

    def _set_3d(self, on):
        if on and self._mesh_view is None:
            try:
                self._mesh_view = MeshView()
            except Exception as e:
                self._btn_3d.setEnabled(False)
                self._btn_2d.setChecked(True)
                QMessageBox.warning(self, "3D view unavailable", f"Could not start the 3D view:\n{e}")
                return
            self._stack.addWidget(self._mesh_view)
        self._view_3d = on
        self._stack.setCurrentWidget(self._mesh_view if on else self._preview)
        if on:
            self._update_3d()

    def _update_3d(self):
        """Refresh the 3D view; returns False (with a status message) on error."""
        if not self._ensure_meshes():
            return False
        try:
            self._mesh_view.set_meshes(self._black_mesh, self._white_mesh)
        except Exception as e:
            self._status.showMessage(f"3D view error: {e}")
            return False
        return True

    def _build_print_widgets(self, form):
        self._layer = QDoubleSpinBox()
        self._layer.setRange(0.04, 1.0)
        self._layer.setSingleStep(0.02)
        self._layer.setDecimals(2)
        self._layer.setValue(0.2)
        self._layer.setSuffix(" mm")
        self._layer.setToolTip(
            "Your slicer's layer height. Base and pattern heights snap to\n"
            "multiples of it so the color boundary lands on a layer line."
        )
        form.addRow("Layer height:", self._layer)

        self._base_on = QCheckBox("Solid white base")
        self._base_on.setChecked(True)
        self._base_on.setToolTip(
            "Print a full-board white base under the two-color pattern so the\n"
            "black bonds to white face-to-face. Unchecked: both colors run the\n"
            "full pattern height, touching only at their side walls."
        )
        form.addRow(self._base_on)

        self._base = self._height_spin(4.0)
        form.addRow("Base height:", self._base)

        self._pattern = self._height_spin(0.6)
        self._pattern.setToolTip(
            "Height of the two-color layer (e.g. 0.6 mm = 3 x 0.2 mm layers)."
        )
        form.addRow("Pattern height:", self._pattern)

        self._total_label = QLabel()
        form.addRow("Total height:", self._total_label)

        self._saved_pattern = self._pattern.value()
        self._base_on.toggled.connect(self._on_base_toggled)
        self._layer.valueChanged.connect(self._on_layer_changed)
        for spin in (self._base, self._pattern):
            spin.valueChanged.connect(self._on_param_changed)
            spin.editingFinished.connect(self._snap_heights)
        self._on_layer_changed()

    def _height_spin(self, value):
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setValue(value)
        spin.setSuffix(" mm")
        return spin

    def _on_base_toggled(self, on):
        """Keep the total height when toggling the base: turning it off folds
        the base into the pattern (full-height two-color board); turning it
        back on restores the previous pattern height on top of a base."""
        self._base.setEnabled(on)
        if on:
            total = self._pattern.value()
            pattern = min(self._saved_pattern, total - self._layer.value())
            pattern = max(pattern, self._layer.value())
            self._pattern.setValue(pattern)
            self._base.setValue(total - pattern)
        else:
            self._saved_pattern = self._pattern.value()
            self._pattern.setValue(self._pattern.value() + self._base.value())
        self._snap_heights()
        self._on_param_changed()

    MAX_HEIGHT_MM = 50.0

    def _on_layer_changed(self):
        layer = self._layer.value()
        top = self._snap(self.MAX_HEIGHT_MM, layer, down=True)
        for spin in (self._base, self._pattern):
            spin.setRange(layer, top)
            spin.setSingleStep(layer)
        self._snap_heights()

    @staticmethod
    def _snap(value, layer, down=False):
        n = math.floor(value / layer + (1e-9 if down else 0.5 + 1e-9))
        return round(max(n, 1) * layer, 2)

    def _snap_heights(self):
        """Round base/pattern to the nearest multiple of the layer height
        (at least one layer, never past the range maximum)."""
        layer = self._layer.value()
        for spin in (self._base, self._pattern):
            snapped = min(self._snap(spin.value(), layer), spin.maximum())
            if abs(snapped - spin.value()) > 1e-9:
                spin.setValue(snapped)

    def _export_prefix(self):
        """Board prefix plus the print heights, so exports with different
        heights don't overwrite each other, e.g. charuco_14_14_20mm_b4_p0.6."""
        pattern_mm, base_mm = self._print_params()
        tag = f"b{base_mm:g}_p{pattern_mm:g}" if base_mm else f"p{pattern_mm:g}"
        return f"{self._file_prefix(self._params())}_{tag}"

    def _print_params(self):
        """(pattern_mm, base_mm); base_mm is 0 when the base is disabled."""
        base = self._base.value() if self._base_on.isChecked() else 0.0
        return self._pattern.value(), base

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
        if hasattr(self, "_total_label"):  # subclasses may fire this mid-build
            pattern_mm, base_mm = self._print_params()
            self._total_label.setText(f"{pattern_mm + base_mm:.2f} mm")
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
            if self._view_3d and not self._update_3d():
                return  # keep the error message visible
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
        pattern_mm, base_mm = self._print_params()
        self._status.showMessage("Building meshes...")
        # repaint(), not processEvents(): handling input here could change the
        # parameters mid-build and cache meshes built from the old ones.
        self._status.repaint()
        try:
            self._black_mesh, self._white_mesh = build_meshes(
                self._board_img, self._board_w, self._board_h,
                p["ppm"], pattern_mm, base_mm=base_mm,
            )
        except Exception as e:
            self._status.showMessage(f"Mesh error: {e}")
            return False
        self._status.showMessage("Meshes ready", 2000)
        return True

    def _export_stl(self):
        directory = QFileDialog.getExistingDirectory(self, "Export STL — choose folder")
        if not directory:
            return
        if not self._ensure_meshes():
            return

        prefix = self._export_prefix()
        black_path = os.path.join(directory, f"{prefix}_black.stl")
        white_path = os.path.join(directory, f"{prefix}_white.stl")
        existing = [p for p in (black_path, white_path) if os.path.exists(p)]
        if existing:
            answer = QMessageBox.question(
                self, "Overwrite files?",
                "These files already exist:\n" + "\n".join(existing) + "\n\nOverwrite them?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self._black_mesh.export(black_path)
        self._white_mesh.export(white_path)
        self._status.showMessage(f"Exported: {black_path}, {white_path}", 5000)

    def _export_3mf(self):
        import trimesh

        prefix = self._export_prefix()
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
        prefix = self._export_prefix()
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
        pattern_mm, base_mm = self._print_params()
        self._btn_step.setEnabled(False)
        self._progress.setVisible(True)

        self._step_worker = StepExportWorker(
            self._board_img, self._board_w, self._board_h,
            p["ppm"], pattern_mm, path, base_mm=base_mm,
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
