from PyQt6.QtCore import QThread, pyqtSignal
from shapely.geometry import box as shapely_box, MultiPolygon, Polygon
from shapely.ops import unary_union


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
                        rects.append(shapely_box(
                            xs * mm_per_px,
                            (self.h - 1 - y) * mm_per_px,
                            x * mm_per_px,
                            (self.h - y) * mm_per_px,
                        ))
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
