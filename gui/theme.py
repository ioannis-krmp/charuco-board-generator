"""App-wide theme: modern dark palette (charcoal + teal accent), applied
once at the QApplication level in main.py.
"""

BACKGROUND = "#2b2e33"
PANEL = "#33373d"
INPUT_BG = "#3a3e45"
TEXT = "#e8e8ea"
MUTED_TEXT = "#9a9da3"
ACCENT = "#3fc1c9"
ACCENT_DIM = "#2d4a4c"
BORDER = "#44484f"
CANVAS = "#1c1e21"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background: {BACKGROUND};
    color: {TEXT};
    font-size: 13px;
}}

QGroupBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 14px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {ACCENT};
}}

QLabel {{
    color: {TEXT};
    background: transparent;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {PANEL};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background: {BACKGROUND};
    color: {MUTED_TEXT};
    padding: 8px 20px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {PANEL};
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{
    color: {TEXT};
}}

QPushButton {{
    background: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 7px 14px;
}}
QPushButton:hover {{
    background: {ACCENT_DIM};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: {ACCENT};
    color: {CANVAS};
}}
QPushButton:disabled {{
    background: {BACKGROUND};
    color: #5a5d63;
    border-color: {BORDER};
}}

QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: {ACCENT};
}}
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    selection-color: {CANVAS};
    outline: none;
}}

QStatusBar {{
    background: {PANEL};
    color: {MUTED_TEXT};
    border-top: 1px solid {BORDER};
}}

QProgressBar {{
    background: {INPUT_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    color: {TEXT};
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
"""

PREVIEW_STYLE = (
    f"background: {CANVAS}; color: {MUTED_TEXT}; "
    f"border: 1px solid {BORDER}; border-radius: 4px;"
)
