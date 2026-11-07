"""Top-level window: sidebar + stacked page area + live status bar."""

import time

import psutil
from PyQt5.QtCore import QByteArray, QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.settings import Settings
from ui.dashboard import Dashboard
from ui.sidebar import Sidebar
from ui.settings_page import SettingsPage
from ui.system_info import SystemInfo
from ui.themes import build_stylesheet, THEMES
from modules.cpu.cpu_monitor import CPUMonitorModule

NAV_ENTRIES = [
    ("dashboard", "Dashboard", "\u2600"),
    ("system", "System Info", "\u2199"),
    ("cpu", "CPU", "\u25FC"),
    ("memory", "Memory", "\u25B2"),
    ("storage", "Storage", "\u26D1"),
    ("network", "Network", "\u2192"),
    ("processes", "Processes", "\u2699"),
    ("hardware", "Hardware", "\u2692"),
    ("settings", "Settings", "\u2699"),
]

MODULE_PAGES = {"dashboard", "system", "settings", "cpu"}


class _PlaceholderPage(QWidget):
    """Shown for modules that belong to a later phase."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        box = QFrame()
        box.setObjectName("card")
        box.setFixedSize(460, 300)
        inner = QVBoxLayout(box)
        inner.setAlignment(Qt.AlignCenter)
        icon = QLabel("\u26A0")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 48px;")
        lbl = QLabel(f"{title} \u2014 coming soon")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 18px; font-weight: 700; margin-top: 14px;")
        sub = QLabel("This module is built in a later phase.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #64748B; font-size: 14px;")
        inner.addWidget(icon)
        inner.addWidget(lbl)
        inner.addWidget(sub)
        layout.addWidget(box)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._settings.setting_changed.connect(self._on_setting_changed)
        self.setWindowTitle("System Monitor")
        self.resize(1250, 800)

        self._sidebar = Sidebar(NAV_ENTRIES, self)

        self._stack = QStackedWidget(self)
        self._stack.setObjectName("pages")
        self._stack.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        self._pages: dict = {}
        self._add_page("dashboard", Dashboard(self))
        self._add_page("system", SystemInfo(self))
        self._add_page("settings", SettingsPage(settings, self))

        # ---------- Live feature modules ----------
        self._cpu_module = CPUMonitorModule(settings)
        self._add_page("cpu", self._cpu_module.create_page())

        for page_id, label, _icon in NAV_ENTRIES:
            if page_id in MODULE_PAGES:
                continue
            self._add_page(page_id, _PlaceholderPage(label, self))

        self._sidebar.page_selected.connect(self._show_page)

        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._stack)
        splitter.setSizes([260, 990])

        root.addWidget(splitter)

        self._status = QStatusBar(self)
        self._status.setObjectName("statusBar")
        self._cpu_lbl = QLabel("CPU: -- %")
        self._mem_lbl = QLabel("RAM: -- %")
        self._time_lbl = QLabel("")
        self._status.addWidget(self._cpu_lbl)
        self._status.addWidget(self._mem_lbl)
        self._status.addPermanentWidget(self._time_lbl)
        self.setStatusBar(self._status)

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

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)
        self._update_status()

        # Start the CPU module collector after the window is shown
        self._cpu_module.start()

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

    def _update_status(self) -> None:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            self._cpu_lbl.setText(f"CPU: {cpu:.1f} %")
            self._mem_lbl.setText(f"RAM: {mem.percent:.1f} %")
        except Exception:
            self._cpu_lbl.setText("CPU: -- %")
            self._mem_lbl.setText("RAM: -- %")
        self._time_lbl.setText(time.strftime("%H:%M:%S"))

    def _on_setting_changed(self, key: str, value) -> None:
        if key == "theme":
            palette = THEMES.get(value, THEMES["blue_white"])
            QApplication.instance().setStyleSheet(build_stylesheet(palette))

    def closeEvent(self, event) -> None:
        self._settings.set(
            "window_geometry", bytes(self.saveGeometry().toHex()).decode("latin-1")
        )
        dashboard = self._pages.get("dashboard")
        if dashboard is not None:
            dashboard.stop()
        self._cpu_module.stop()
        super().closeEvent(event)
