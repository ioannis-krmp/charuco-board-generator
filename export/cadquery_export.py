"""Pure CadQuery colored-STEP-assembly export. Shared by the GUI's
background worker (mesh_export.StepExportWorker) and the standalone
build_step.py CLI tool. Progress is reported via a plain callback so this
module has no Qt dependency.
"""
from shapely.geometry import MultiPolygon, Polygon

from .geometry import board_bounds, image_to_polygons


def export_step(img, w, h, ppm, pattern_mm, out_path, base_mm=0.0, border_mm=0.0, progress_cb=None):
    import cadquery as cq

    def report(msg):
        if progress_cb:
            progress_cb(msg)

    report("Building 2D polygons...")
    black_poly, white_poly = image_to_polygons(img, w, h, ppm, border_mm)

    report("Extruding black solid (this takes a while)...")
    black_solid = _extrude_cq(black_poly, pattern_mm, cq, "black", report, z=base_mm)

    report("Extruding white solid...")
    white_solid = _extrude_cq(white_poly, pattern_mm, cq, "white", report, z=base_mm)
    if base_mm > 0:
        report("Fusing white base...")
        minx, miny, maxx, maxy = board_bounds(black_poly, white_poly)
        base = (
            cq.Workplane("XY")
            .box(maxx - minx, maxy - miny, base_mm, centered=False)
            .translate((minx, miny, 0))
        )
        white_solid = base.union(white_solid)

    report("Building assembly and saving STEP...")
    asm = cq.Assembly()
    asm.add(black_solid, name="Black", color=cq.Color(0.1, 0.1, 0.1, 1))
    asm.add(white_solid, name="White", color=cq.Color(0.95, 0.95, 0.95, 1))
    asm.save(out_path)
    return out_path


def _extrude_cq(poly, height, cq, label, report, z=0.0):
    if isinstance(poly, Polygon):
        return _extrude_single_cq(poly, height, cq, z)
    elif isinstance(poly, MultiPolygon):
        geoms = list(poly.geoms)
        total = len(geoms)
        solids = []
        for i, p in enumerate(geoms):
            if i % 20 == 0:
                report(f"Extruding {label}: {i}/{total} polygons...")
            solids.append(_extrude_single_cq(p, height, cq, z).val())
        compound = cq.Compound.makeCompound(solids)
        return cq.Workplane().newObject([compound])
    raise TypeError(f"Unexpected geometry type: {type(poly)}")


def _extrude_single_cq(poly, height, cq, z=0.0):
    plane = cq.Plane(origin=(0, 0, z))
    exterior = list(poly.exterior.coords)
    wp = cq.Workplane(plane).polyline(exterior).close().extrude(height)
    for hole in poly.interiors:
        cut = cq.Workplane(plane).polyline(list(hole.coords)).close().extrude(height)
        wp = wp.cut(cut)
    return wp
