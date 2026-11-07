"""Colour palettes and the Qt stylesheet (QSS).

Default theme is a professional blue & white scheme. A dark variant is
available for later use. The active theme is stored in Settings.
"""

from typing import Dict

BLUE_WHITE: Dict[str, str] = {
    "name": "blue_white",
    "background": "#FFFFFF",
    "surface": "#F8FAFC",
    "surface_alt": "#F1F5F9",
    "panel": "#FFFFFF",
    "border": "#E2E8F0",
    "border_focus": "#3B82F6",
    "text": "#0F172A",
    "text_secondary": "#64748B",
    "text_muted": "#94A3B8",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "accent_active": "#1D4ED8",
    "accent_bg": "#EFF6FF",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "shadow": "rgba(15, 23, 42, 0.08)",
    "statusbar": "#FFFFFF",
    "statusbar_border": "#E2E8F0",
}

DARK: Dict[str, str] = {
    "name": "dark",
    "background": "#0B1021",
    "surface": "#111827",
    "surface_alt": "#1E293B",
    "panel": "#111827",
    "border": "#334155",
    "border_focus": "#3B82F6",
    "text": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "accent": "#3B82F6",
    "accent_hover": "#60A5FA",
    "accent_active": "#2563EB",
    "accent_bg": "#1E3A8A",
    "success": "#34D399",
    "warning": "#FBBF24",
    "danger": "#F87171",
    "shadow": "rgba(0, 0, 0, 0.45)",
    "statusbar": "#0B1021",
    "statusbar_border": "#334155",
}

THEMES = {"blue_white": BLUE_WHITE, "dark": DARK}


def _rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def build_stylesheet(palette: Dict[str, str]) -> str:
    """Build a Qt stylesheet from a palette dict."""
    p = palette
    return f"""
    QMainWindow, QWidget {{
        background-color: {p['background']};
        color: {p['text']};
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                     "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }}

    QToolTip {{
        background-color: {p['surface_alt']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 6px 10px;
    }}

    QStatusBar {{
        background-color: {p['statusbar']};
        color: {p['text_secondary']};
        border-top: 1px solid {p['statusbar_border']};
        padding: 4px 12px;
        font-size: 12px;
    }}

    QStatusBar QLabel {{
        color: {p['text_secondary']};
        background: transparent;
        padding: 2px 8px;
    }}

    /* ---------- Sidebar ---------- */
    QListWidget#sidebar {{
        background-color: {p['surface']};
        border: none;
        border-right: 1px solid {p['border']};
        outline: none;
        padding: 8px 0;
    }}

    QListWidget#sidebar::item {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        margin: 4px 12px;
        padding: 10px 14px;
        color: {p['text_secondary']};
        font-size: 13px;
        font-weight: 500;
    }}

    QListWidget#sidebar::item:selected {{
        background-color: {p['accent_bg']};
        color: {p['accent_active']};
        border-left: 4px solid {p['accent_active']};
        padding-left: 10px;
    }}

    QListWidget#sidebar::item:hover:!selected {{
        background-color: {p['surface_alt']};
        color: {p['text']};
    }}

    /* ---------- Pages / stack ---------- */
    QStackedWidget {{
        background-color: transparent;
        border: none;
    }}

    QFrame#card {{
        background-color: {p['panel']};
        border: 1px solid {p['border']};
        border-radius: 12px;
    }}

    QLabel#heading {{
        color: {p['text']};
        font-size: 20px;
        font-weight: 700;
        padding: 0;
    }}

    QLabel#subheading {{
        color: {p['text_secondary']};
        font-size: 13px;
        padding: 0;
    }}

    QLabel#muted {{
        color: {p['text_muted']};
        font-size: 12px;
    }}

    /* ---------- Buttons ---------- */
    QPushButton#primary {{
        background-color: {p['accent']};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }}

    QPushButton#primary:hover {{
        background-color: {p['accent_hover']};
    }}

    QPushButton#primary:pressed {{
        background-color: {p['accent_active']};
    }}

    QPushButton#primary:disabled {{
        background-color: {p['text_muted']};
        color: rgba(255, 255, 255, 0.5);
    }}

    QPushButton#ghost {{
        background-color: transparent;
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }}

    QPushButton#ghost:hover {{
        background-color: {p['surface_alt']};
        border-color: {p['border_focus']};
    }}

    QPushButton#danger {{
        background-color: {p['danger']};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 6px 14px;
        font-weight: 600;
        font-size: 12px;
    }}

    QPushButton#danger:hover {{
        background-color: #DC2626;
    }}

    /* ---------- Inputs ---------- */
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {p['panel']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        min-height: 20px;
    }}

    QLineEdit:focus, QComboBox:focus {{
        border-color: {p['border_focus']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p['panel']};
        border: 1px solid {p['border']};
        selection-background-color: {p['accent_bg']};
        selection-color: {p['accent_active']};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: {p['text_muted']};
        border-radius: 5px;
        min-height: 24px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {p['text_secondary']};
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0;
    }}
    """
