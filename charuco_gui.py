import sys
import os
import cv2
import numpy as np
import trimesh
from shapely.geometry import box as shapely_box, MultiPolygon, Polygon
from shapely.ops import unary_union

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QLabel, QPushButton, QFileDialog, QProgressBar, QStatusBar,
    QSizePolicy, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap


DICTS = [
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


def generate_board_image(squares_x, squares_y, square_mm, marker_mm, dict_id, ppm):
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


def build_meshes(img, w, h, ppm, thick_mm):
    mm_per_px = 1.0 / ppm
    board_w = w * mm_per_px
    board_h = h * mm_per_px

    rects = []
    for y in range(h):
        row = img[y]
        x = 0
        while x < w:
            if row[x] < 128:
                xs = x
                while x < w and row[x] < 128:
                    x += 1
                dx = (x - xs) * mm_per_px
                dy = mm_per_px
                x_mm = xs * mm_per_px
                y_mm = (h - 1 - y) * mm_per_px
                rects.append(shapely_box(x_mm, y_mm, x_mm + dx, y_mm + dy))
            else:
                x += 1

    black_poly = unary_union(rects)
    full_rect = shapely_box(0, 0, board_w, board_h)
    white_poly = full_rect.difference(black_poly)

    black_mesh = _extrude_poly(black_poly, thick_mm)
    white_mesh = _extrude_poly(white_poly, thick_mm)
    return black_mesh, white_mesh


def _extrude_poly(poly, height):
    if isinstance(poly, Polygon):
        return trimesh.creation.extrude_polygon(poly, height)
    elif isinstance(poly, MultiPolygon):
        meshes = [trimesh.creation.extrude_polygon(p, height) for p in poly.geoms]
        return trimesh.util.concatenate(meshes)
    raise TypeError(f"Unexpected geometry type: {type(poly)}")


class StepExportWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, img, w, h, ppm, thick_mm, out_path):
        super().__init__()
        self.img = img
        self.w, self.h, self.ppm = w, h, ppm
        self.thick_mm = thick_mm
        self.out_path = out_path

    def run(self):
        try:
            import cadquery as cq

            mm_per_px = 1.0 / self.ppm
            board_w = self.w * mm_per_px
            board_h = self.h * mm_per_px

            self.progress.emit("Building 2D polygons...")
            rects = []
            for y in range(self.h):
                row = self.img[y]
                x = 0
                while x < self.w:
                    if row[x] < 128:
                        xs = x
                        while x < self.w and row[x] < 128:
                            x += 1
                        dx = (x - xs) * mm_per_px
                        dy = mm_per_px
                        x_mm = xs * mm_per_px
                        y_mm = (self.h - 1 - y) * mm_per_px
                        rects.append(shapely_box(x_mm, y_mm, x_mm + dx, y_mm + dy))
                    else:
                        x += 1

            self.progress.emit("Merging polygons...")
            black_poly = unary_union(rects)
            full_rect = shapely_box(0, 0, board_w, board_h)
            white_poly = full_rect.difference(black_poly)

            self.progress.emit("Extruding black solid (this takes a while)...")
            black_solid = self._extrude_cq(black_poly, self.thick_mm, cq, "black")

            self.progress.emit("Extruding white solid...")
            white_solid = self._extrude_cq(white_poly, self.thick_mm, cq, "white")

            self.progress.emit("Building assembly and saving STEP...")
            asm = cq.Assembly()
            asm.add(black_solid, name="Black", color=cq.Color(0.1, 0.1, 0.1, 1))
            asm.add(white_solid, name="White", color=cq.Color(0.95, 0.95, 0.95, 1))
            asm.save(self.out_path)

            self.finished.emit(self.out_path)
        except Exception as e:
            self.error.emit(str(e))

    def _extrude_cq(self, poly, height, cq, label):
        if isinstance(poly, Polygon):
            return self._extrude_single_cq(poly, height, cq)
        elif isinstance(poly, MultiPolygon):
            geoms = list(poly.geoms)
            total = len(geoms)
            solids = []
            for i, p in enumerate(geoms):
                if i % 20 == 0:
                    self.progress.emit(f"Extruding {label}: {i}/{total} polygons...")
                solids.append(self._extrude_single_cq(p, height, cq).val())
            compound = cq.Compound.makeCompound(solids)
            return cq.Workplane().newObject([compound])
        raise TypeError(f"Unexpected geometry type: {type(poly)}")

    def _extrude_single_cq(self, poly, height, cq):
        exterior = list(poly.exterior.coords)
        wp = cq.Workplane("XY").polyline(exterior).close().extrude(height)
        for hole in poly.interiors:
            cut = cq.Workplane("XY").polyline(list(hole.coords)).close().extrude(height)
            wp = wp.cut(cut)
        return wp


class CharucoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Charuco Board Generator")
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

        self._preview = QLabel("Click 'Generate' or change parameters")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._preview.setStyleSheet("background: #222; color: #aaa; border: 1px solid #555;")
        layout.addWidget(self._preview, stretch=1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        self._status = QStatusBar()
        self._status.addPermanentWidget(self._progress)
        self.setStatusBar(self._status)

        self._update_info()
        self._generate_preview()

    def _create_params_group(self):
        grp = QGroupBox("Parameters")
        form = QFormLayout(grp)

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
        for name, _, _ in DICTS:
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

    def _params(self):
        idx = self._dict_cb.currentIndex()
        _, dict_id, capacity = DICTS[idx]
        return {
            "squares_x": self._sq_x.value(),
            "squares_y": self._sq_y.value(),
            "square_mm": self._sq_mm.value(),
            "marker_mm": self._mk_mm.value(),
            "dict_id": dict_id,
            "dict_name": DICTS[idx][0],
            "dict_capacity": capacity,
            "thick_mm": self._thick.value(),
            "ppm": self._ppm.value(),
        }

    def _file_prefix(self):
        p = self._params()
        return f"charuco_{p['squares_x']}_{p['squares_y']}_{int(p['square_mm'])}mm"

    def _on_param_changed(self):
        self._update_info()
        self._black_mesh = None
        self._white_mesh = None
        self._debounce.start()

    def _update_info(self):
        p = self._params()
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

        self._info_label.setText(
            f"Board size: {board_w:.0f} x {board_h:.0f} mm\n"
            f"Corners: {corners}\n"
            f"Markers: {markers} / {cap}"
            f"{warn}"
        )

        ok = markers <= cap and p["marker_mm"] < p["square_mm"]
        for btn in (self._btn_stl, self._btn_3mf, self._btn_step):
            btn.setEnabled(ok)

    def _generate_preview(self):
        p = self._params()
        if p["marker_mm"] >= p["square_mm"]:
            return
        markers = (p["squares_x"] * p["squares_y"]) // 2
        if markers > p["dict_capacity"]:
            return

        try:
            img, w, h = generate_board_image(
                p["squares_x"], p["squares_y"],
                p["square_mm"], p["marker_mm"],
                p["dict_id"], p["ppm"],
            )
            self._board_img = img
            self._board_w = w
            self._board_h = h

            qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(
                self._preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview.setPixmap(scaled)
            self._status.showMessage("Preview updated", 2000)
        except Exception as e:
            self._status.showMessage(f"Preview error: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._board_img is not None:
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

        prefix = self._file_prefix()
        black_path = os.path.join(directory, f"{prefix}_black.stl")
        white_path = os.path.join(directory, f"{prefix}_white.stl")

        self._black_mesh.export(black_path)
        self._white_mesh.export(white_path)
        self._status.showMessage(f"Exported: {black_path}, {white_path}", 5000)

    def _export_3mf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export 3MF", f"{self._file_prefix()}_board.3mf", "3MF files (*.3mf)"
        )
        if not path:
            return
        if not self._ensure_meshes():
            return

        prefix = self._file_prefix()
        scene = trimesh.Scene()
        scene.add_geometry(self._black_mesh, node_name="black", geom_name=f"{prefix}_black")
        scene.add_geometry(self._white_mesh, node_name="white", geom_name=f"{prefix}_white")
        scene.export(path)
        self._status.showMessage(f"Exported: {path}", 5000)

    def _export_step(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export STEP", f"{self._file_prefix()}_board.step", "STEP files (*.step)"
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CharucoApp()
    window.show()
    sys.exit(app.exec())
