"""Qt wrapper around the shared raster -> mesh / STEP pipeline (geometry.py,
cadquery_export.py), so STEP export (slow, CadQuery-based) runs on a
background thread without blocking the GUI.
"""
from PyQt6.QtCore import QThread, pyqtSignal

from .cadquery_export import export_step


class StepExportWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, img, w, h, ppm, pattern_mm, out_path, base_mm=0.0):
        super().__init__()
        self.img = img
        self.w, self.h, self.ppm = w, h, ppm
        self.pattern_mm = pattern_mm
        self.base_mm = base_mm
        self.out_path = out_path

    def run(self):
        try:
            export_step(
                self.img, self.w, self.h, self.ppm, self.pattern_mm, self.out_path,
                base_mm=self.base_mm, progress_cb=self.progress.emit,
            )
            self.finished.emit(self.out_path)
        except Exception as e:
            self.error.emit(str(e))
