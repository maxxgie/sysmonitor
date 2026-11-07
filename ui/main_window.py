"""Top-level window: sidebar + stacked page area."""

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.settings import Settings
from ui.dashboard import Dashboard
from ui.sidebar import Sidebar
from ui.settings_page import SettingsPage
from ui.themes import build_stylesheet, THEMES

NAV_ENTRIES = [
    ("dashboard", "Dashboard", "\u2600"),
    ("cpu", "CPU", "\u25FC"),
    ("memory", "Memory", "\u25B2"),
    ("storage", "Storage", "\u26D1"),
    ("network", "Network", "\u2192"),
    ("processes", "Processes", "\u2699"),
    ("hardware", "Hardware", "\u2692"),
    ("settings", "Settings", "\u2699"),
]

MODULE_PAGES = {"dashboard", "settings"}


class _PlaceholderPage(QWidget):
    """Shown for modules that belong to a later phase."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        box = QFrame()
        box.setObjectName("card")
        box.setFixedSize(420, 260)
        inner = QVBoxLayout(box)
        inner.setAlignment(Qt.AlignCenter)
        icon = QLabel("\u26A0")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 40px;")
        lbl = QLabel(f"{title} \u2014 coming soon")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 16px; font-weight: 600; margin-top: 12px;")
        sub = QLabel("This module is built in a later phase.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #64748B; font-size: 13px;")
        inner.addWidget(icon)
        inner.addWidget(lbl)
        inner.addWidget(sub)
        layout.addWidget(box)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("System Monitor")
        self.resize(1100, 700)

        self._sidebar = Sidebar(NAV_ENTRIES, self)
        self._sidebar.setFixedWidth(240)

        self._stack = QStackedWidget(self)
        self._stack.setObjectName("pages")

        self._pages: dict = {}
        self._add_page("dashboard", Dashboard(self))
        self._add_page("settings", SettingsPage(settings, self))
        for page_id, label, _icon in NAV_ENTRIES:
            if page_id in MODULE_PAGES:
                continue
            self._add_page(page_id, _PlaceholderPage(label, self))

        self._sidebar.page_selected.connect(self._show_page)

        central = QWidget(self)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._sidebar)
        root.addWidget(self._stack)
        self.setCentralWidget(central)

        start_page = self._settings.get("start_page", "dashboard")
        if start_page not in self._pages:
            start_page = "dashboard"
        self._sidebar.set_active_page(start_page)
        self._show_page(start_page)

        geometry = self._settings.get("window_geometry", "")
        if geometry:
            ba = QByteArray.fromHex(geometry.encode("latin-1"))
            if not ba.isEmpty():
                self.restoreGeometry(ba)

    def _add_page(self, page_id: str, widget: QWidget) -> None:
        self._pages[page_id] = widget
        self._stack.addWidget(widget)

    def _show_page(self, page_id: str) -> None:
        widget = self._pages.get(page_id)
        if widget is None:
            return
        self._stack.setCurrentWidget(widget)
        self._sidebar.set_active_page(page_id)
        self._settings.set("start_page", page_id)

    def closeEvent(self, event) -> None:
        self._settings.set(
            "window_geometry", bytes(self.saveGeometry().toHex()).decode("latin-1")
        )
        super().closeEvent(event)
