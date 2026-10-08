"""Pure CadQuery colored-STEP-assembly export. Shared by the GUI's
background worker (mesh_export.StepExportWorker) and the standalone
build_step.py CLI tool. Progress is reported via a plain callback so this
module has no Qt dependency.
"""
from shapely.geometry import MultiPolygon, Polygon

from .geometry import image_to_polygons


def export_step(img, w, h, ppm, thick_mm, out_path, border_mm=0.0, progress_cb=None):
    import cadquery as cq

    def report(msg):
        if progress_cb:
            progress_cb(msg)

    report("Building 2D polygons...")
    black_poly, white_poly = image_to_polygons(img, w, h, ppm, border_mm)

    report("Extruding black solid (this takes a while)...")
    black_solid = _extrude_cq(black_poly, thick_mm, cq, "black", report)

    report("Extruding white solid...")
    white_solid = _extrude_cq(white_poly, thick_mm, cq, "white", report)

    report("Building assembly and saving STEP...")
    asm = cq.Assembly()
    asm.add(black_solid, name="Black", color=cq.Color(0.1, 0.1, 0.1, 1))
    asm.add(white_solid, name="White", color=cq.Color(0.95, 0.95, 0.95, 1))
    asm.save(out_path)
    return out_path


def _extrude_cq(poly, height, cq, label, report):
    if isinstance(poly, Polygon):
        return _extrude_single_cq(poly, height, cq)
    elif isinstance(poly, MultiPolygon):
        geoms = list(poly.geoms)
        total = len(geoms)
        solids = []
        for i, p in enumerate(geoms):
            if i % 20 == 0:
                report(f"Extruding {label}: {i}/{total} polygons...")
            solids.append(_extrude_single_cq(p, height, cq).val())
        compound = cq.Compound.makeCompound(solids)
        return cq.Workplane().newObject([compound])
    raise TypeError(f"Unexpected geometry type: {type(poly)}")


def _extrude_single_cq(poly, height, cq):
    exterior = list(poly.exterior.coords)
    wp = cq.Workplane("XY").polyline(exterior).close().extrude(height)
    for hole in poly.interiors:
        cut = cq.Workplane("XY").polyline(list(hole.coords)).close().extrude(height)
        wp = wp.cut(cut)
    return wp
