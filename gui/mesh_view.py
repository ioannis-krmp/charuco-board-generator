"""Interactive 3D preview of the black/white meshes (pyqtgraph OpenGL).
Left-drag orbits, right/middle-drag pans, wheel zooms.
"""
import numpy as np
import pyqtgraph.opengl as gl
from pyqtgraph import Vector
from pyqtgraph.opengl.shaders import FragmentShader, ShaderProgram, VertexShader
from PyQt6.QtGui import QOffscreenSurface, QOpenGLContext
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton

BLACK_COLOR = (0.12, 0.12, 0.13, 1.0)
WHITE_COLOR = (0.93, 0.93, 0.93, 1.0)
BACKGROUND = (28, 30, 33, 255)  # theme.CANVAS
EXAGGERATION = 5.0

# Headlight: the light sits at the camera, so faces looking at the viewer are
# bright whatever the orbit angle. (pyqtgraph's built-in "shaded" lights from
# behind the view direction, which leaves the board's top face nearly black.)
_HEADLIGHT = ShaderProgram("headlight", [
    VertexShader("""
        uniform mat4 u_mvp;
        uniform mat3 u_normal;
        attribute vec4 a_position;
        attribute vec3 a_normal;
        attribute vec4 a_color;
        varying vec4 v_color;
        varying vec3 v_normal;
        void main() {
            v_normal = normalize(u_normal * a_normal);
            v_color = a_color;
            gl_Position = u_mvp * a_position;
        }
    """),
    FragmentShader("""
        #ifdef GL_ES
        precision mediump float;
        #endif
        varying vec4 v_color;
        varying vec3 v_normal;
        void main() {
            float k = 0.4 + 0.6 * abs(normalize(v_normal).z);
            gl_FragColor = vec4(v_color.rgb * k, v_color.a);
        }
    """),
])


_gl_ok = None


def opengl_available():
    """True if an OpenGL context can actually be created and made current.
    Importing pyqtgraph.opengl succeeds even on machines without working GL,
    so probe once at runtime (needs a QApplication)."""
    global _gl_ok
    if _gl_ok is None:
        ctx = QOpenGLContext()
        surface = QOffscreenSurface()
        surface.create()
        _gl_ok = bool(ctx.create() and ctx.makeCurrent(surface))
        if _gl_ok:
            ctx.doneCurrent()
    return _gl_ok


class MeshView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._extent = 100.0
        self._items = []
        self._framed = False

        self._gl = gl.GLViewWidget()
        self._gl.setBackgroundColor(BACKGROUND)

        self._exaggerate = QCheckBox(f"Exaggerate height x{EXAGGERATION:g}")
        self._exaggerate.setToolTip("Stretch Z so thin base/pattern layers are visible")
        self._exaggerate.toggled.connect(self._apply_z_scale)

        reset = QPushButton("Reset view")
        reset.clicked.connect(self.reset_view)

        controls = QHBoxLayout()
        controls.addWidget(self._exaggerate)
        controls.addStretch()
        controls.addWidget(reset)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self._gl, stretch=1)

    def set_meshes(self, black_mesh, white_mesh):
        for item in self._items:
            self._gl.removeItem(item)
        self._items = []

        # Center the board on the origin (x/y only; z stays 0 = bed).
        lo = np.minimum(black_mesh.bounds[0], white_mesh.bounds[0])
        hi = np.maximum(black_mesh.bounds[1], white_mesh.bounds[1])
        offset = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.0])
        self._extent = float(max(hi[0] - lo[0], hi[1] - lo[1]))

        for mesh, color in ((white_mesh, WHITE_COLOR), (black_mesh, BLACK_COLOR)):
            data = gl.MeshData(
                vertexes=np.asarray(mesh.vertices - offset, dtype=np.float32),
                faces=np.asarray(mesh.faces, dtype=np.uint32),
            )
            item = gl.GLMeshItem(
                meshdata=data, smooth=False, shader=_HEADLIGHT, color=color,
                glOptions="opaque",
            )
            self._gl.addItem(item)
            self._items.append(item)

        self._apply_z_scale()
        if not self._framed:
            self.reset_view()
            self._framed = True

    def reset_view(self):
        self._gl.setCameraPosition(
            distance=self._extent * 1.4, elevation=45, azimuth=-90
        )
        self._gl.opts["center"] = Vector(0, 0, 0)
        self._gl.update()

    def _apply_z_scale(self):
        k = EXAGGERATION if self._exaggerate.isChecked() else 1.0
        for item in self._items:
            item.resetTransform()
            item.scale(1, 1, k)
        self._gl.update()
