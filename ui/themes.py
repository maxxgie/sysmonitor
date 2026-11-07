"""Colour palettes and the Qt stylesheet (QSS).

Default theme is a professional blue & white scheme. A dark variant is
available. The active theme is stored in Settings and can be switched live.
"""

from typing import Dict

BLUE_WHITE: Dict[str, str] = {
    "name": "blue_white",
    # Surfaces
    "background": "#FFFFFF",
    "surface": "#F8FAFC",
    "surface_alt": "#F1F5F9",
    "panel": "#FFFFFF",
    # Borders
    "border": "#E2E8F0",
    "border_focus": "#3B82F6",
    "border_hover": "#CBD5E1",
    # Text
    "text": "#0F172A",
    "text_secondary": "#64748B",
    "text_muted": "#94A3B8",
    "text_inverse": "#FFFFFF",
    # Accent (blue)
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "accent_active": "#1D4ED8",
    "accent_bg": "#EFF6FF",
    "accent_border": "#93C5FD",
    # Semantic
    "success": "#10B981",
    "success_bg": "#ECFDF5",
    "warning": "#F59E0B",
    "warning_bg": "#FFFBEB",
    "danger": "#EF4444",
    "danger_bg": "#FEF2F2",
    # Shadow / elevation
    "shadow_sm": "rgba(15, 23, 42, 0.06)",
    "shadow_md": "rgba(15, 23, 42, 0.08)",
    "shadow_lg": "rgba(15, 23, 42, 0.10)",
    # Status bar
    "statusbar": "#FFFFFF",
    "statusbar_border": "#E2E8F0",
}

DARK: Dict[str, str] = {
    "name": "dark",
    # Surfaces
    "background": "#0B1021",
    "surface": "#111827",
    "surface_alt": "#1E293B",
    "panel": "#111827",
    # Borders
    "border": "#334155",
    "border_focus": "#3B82F6",
    "border_hover": "#475569",
    # Text
    "text": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "text_inverse": "#FFFFFF",
    # Accent (blue)
    "accent": "#3B82F6",
    "accent_hover": "#60A5FA",
    "accent_active": "#2563EB",
    "accent_bg": "#1E3A8A",
    "accent_border": "#60A5FA",
    # Semantic
    "success": "#34D399",
    "success_bg": "#064E3B",
    "warning": "#FBBF24",
    "warning_bg": "#78350F",
    "danger": "#F87171",
    "danger_bg": "#991B1B",
    # Shadow / elevation
    "shadow_sm": "rgba(0, 0, 0, 0.30)",
    "shadow_md": "rgba(0, 0, 0, 0.40)",
    "shadow_lg": "rgba(0, 0, 0, 0.50)",
    # Status bar
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
    """Build a polished Qt stylesheet from a palette dict."""
    p = palette
    return f"""
    /* ============ Base ============ */
    QMainWindow, QWidget {{
        background-color: {p['background']};
        color: {p['text']};
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                     "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
        selection-background-color: {p['accent']};
        selection-color: {p['text_inverse']};
    }}

    QToolTip {{
        background-color: {p['surface_alt']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }}

    QStatusBar {{
        background-color: {p['statusbar']};
        color: {p['text_secondary']};
        border-top: 1px solid {p['statusbar_border']};
        padding: 6px 14px;
        font-size: 12px;
    }}

    QStatusBar QLabel {{
        color: {p['text_secondary']};
        background: transparent;
        padding: 2px 10px;
    }}

    /* ============ Sidebar ============ */
    QWidget#sidebar {{
        background-color: {p['surface']};
        border-right: 1px solid {p['border']};
    }}

    QFrame#sidebarHeader {{
        background-color: transparent;
        border: none;
    }}

    QLabel#sidebarIcon {{
        color: {p['accent']};
        background: transparent;
    }}

    QLabel#sidebarTitle {{
        color: {p['text']};
        background: transparent;
    }}

    QLabel#sidebarSubtitle {{
        color: {p['text_muted']};
        background: transparent;
    }}

    QFrame#sidebarDivider {{
        background-color: {p['border']};
        border: none;
    }}

    QScrollArea#sidebarScroll {{
        background-color: transparent;
        border: none;
    }}

    QWidget#navContainer {{
        background-color: transparent;
    }}

    QPushButton#navButton {{
        background-color: transparent;
        border: none;
        border-radius: 10px;
        margin: 6px 14px;
        text-align: left;
        padding: 10px 18px;
        color: {p['text_secondary']};
    }}

    QPushButton#navButton:checked {{
        background-color: {p['accent_bg']};
        color: {p['accent_active']};
        border-left: 4px solid {p['accent_active']};
        padding-left: 14px;
    }}

    QPushButton#navButton:!checked:hover {{
        background-color: {p['surface_alt']};
        color: {p['text']};
    }}

    QPushButton#navButton:pressed {{
        background-color: {p['accent_bg']};
    }}

    /* ============ Pages / Stack ============ */
    QStackedWidget {{
        background-color: transparent;
        border: none;
    }}

    /* ============ Cards ============ */
    QFrame#card {{
        background-color: {p['panel']};
        border: 1px solid {p['border']};
        border-radius: 14px;
    }}

    QFrame#card:hover {{
        border-color: {p['border_hover']};
    }}

    /* ============ Headings ============ */
    QLabel#heading {{
        color: {p['text']};
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.2px;
        padding: 0;
    }}

    QLabel#subheading {{
        color: {p['text_secondary']};
        font-size: 14px;
        font-weight: 500;
        padding: 0;
    }}

    QLabel#muted {{
        color: {p['text_muted']};
        font-size: 12px;
    }}

    /* ============ Value labels (big metrics) ============ */
    QLabel#value {{
        color: {p['text']};
    }}

    /* ============ Buttons ============ */
    QPushButton#primary {{
        background-color: {p['accent']};
        color: {p['text_inverse']};
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 700;
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
        color: rgba(255, 255, 255, 0.45);
    }}

    QPushButton#ghost {{
        background-color: transparent;
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 700;
        font-size: 13px;
    }}

    QPushButton#ghost:hover {{
        background-color: {p['surface_alt']};
        border-color: {p['border_focus']};
    }}

    QPushButton#danger {{
        background-color: {p['danger']};
        color: {p['text_inverse']};
        border: none;
        border-radius: 10px;
        padding: 8px 16px;
        font-weight: 700;
        font-size: 12px;
    }}

    QPushButton#danger:hover {{
        background-color: #DC2626;
    }}

    /* ============ Inputs ============ */
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {p['panel']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 13px;
        min-height: 20px;
    }}

    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border-color: {p['border_focus']};
        outline: none;
    }}

    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}

    QComboBox::down-arrow {{
        color: {p['text_muted']};
    }}

    QComboBox QAbstractItemView {{
        background-color: {p['panel']};
        border: 1px solid {p['border']};
        selection-background-color: {p['accent_bg']};
        selection-color: {p['accent_active']};
        padding: 6px;
    }}

    QComboBox QAbstractItemView::item {{
        padding: 8px 12px;
        border-radius: 6px;
        margin: 2px;
    }}

    QComboBox QAbstractItemView::item:selected {{
        background-color: {p['accent_bg']};
        color: {p['accent_active']};
        margin: 2px;
    }}

    QSpinBox::up-button, QSpinBox::down-button {{
        border: none;
        background: transparent;
        width: 24px;
    }}

    /* ============ Scrollbars ============ */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: {p['text_muted']};
        border-radius: 5px;
        min-height: 28px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {p['text_secondary']};
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background: {p['text_muted']};
        border-radius: 5px;
        min-width: 28px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {p['text_secondary']};
    }}
    """
