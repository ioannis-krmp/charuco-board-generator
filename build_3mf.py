import os
import sys
import trimesh

if len(sys.argv) < 3:
    print("Usage: build_3mf.py <black.stl> <white.stl> [output.3mf]")
    sys.exit(1)

black_path = sys.argv[1]
white_path = sys.argv[2]

base_name = os.path.basename(black_path).replace("_black.stl", "")
out_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
    os.path.dirname(os.path.abspath(black_path)), f"{base_name}_board.3mf"
)

print("A: loading STLs...")
black_mesh = trimesh.load(black_path)
white_mesh = trimesh.load(white_path)

print("B: building scene...")
scene = trimesh.Scene()
scene.add_geometry(black_mesh, node_name="black", geom_name=f"{base_name}_black")
scene.add_geometry(white_mesh, node_name="white", geom_name=f"{base_name}_white")

print("C: exporting 3MF...")
scene.export(out_path)

size_mb = os.path.getsize(out_path) / 1024 / 1024
print(f"D: done — {out_path} ({size_mb:.1f} MB)")
