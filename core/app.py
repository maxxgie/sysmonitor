"""Application bootstrap: wires logger, database, settings, theme and window."""

import sys

from PyQt5.QtWidgets import QApplication

from core.database import Database
from core.logger import setup_logging
from core.settings import Settings
from ui.main_window import MainWindow
from ui.themes import build_stylesheet, THEMES


def create_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName("System Monitor")
    app.setOrganizationName("SystemMonitor")
    return app


def build_window() -> MainWindow:
    """Composition root: create shared services and hand them to the UI."""
    setup_logging()
    database = Database()
    settings = Settings(database)

    theme_name = settings.get("theme", "blue_white")
    palette = THEMES.get(theme_name, THEMES["blue_white"])
    QApplication.instance().setStyleSheet(build_stylesheet(palette))

    window = MainWindow(settings)
    return window


def main() -> int:
    app = create_app()
    window = build_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
