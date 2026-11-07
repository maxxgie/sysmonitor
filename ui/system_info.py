"""System information page: OS, hostname, uptime, hardware details."""

import platform
import sys
import time

import psutil

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def _uptime_string() -> str:
    try:
        boot = psutil.boot_time()
        seconds = int(time.time() - boot)
    except Exception:
        return "Unknown"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


class _InfoRow(QFrame):
    def __init__(self, label: str, value: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName("muted")
        lbl.setWordWrap(True)

        val = QLabel(value)
        val.setWordWrap(True)
        val.setStyleSheet("font-size: 15px; font-weight: 600;")

        layout.addWidget(lbl)
        layout.addWidget(val)


class SystemInfo(QWidget):
    """Static system information: OS, hardware, uptime, environment."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)
        grid.setContentsMargins(24, 24, 24, 24)

        rows = [
            ("Operating System", f"{platform.system()} {platform.release()}"),
            ("OS Version", platform.version()),
            ("Hostname", platform.node()),
            ("Architecture", platform.machine()),
            ("Processor", platform.processor() or "Unknown"),
            ("Python Version", sys.version.split(" ")[0]),
            ("Uptime", _uptime_string()),
            ("Boot Time", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(psutil.boot_time()))),
            ("Logical CPUs", str(psutil.cpu_count(logical=True))),
            ("Physical CPUs", str(psutil.cpu_count(logical=False) or "Unknown")),
        ]

        for i, (label, value) in enumerate(rows):
            grid.addWidget(_InfoRow(label, value), i // 2, i % 2)

        grid.setColumnStretch(2, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        header = QLabel("System Information")
        header.setObjectName("heading")
        sub = QLabel("Static hardware and operating system details.")
        sub.setObjectName("subheading")
        root.addWidget(header)
        root.addWidget(sub)
        root.addSpacing(16)
        root.addWidget(scroll)
        scroll.setWidget(container)
