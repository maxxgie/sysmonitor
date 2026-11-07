"""Dashboard landing page with live system metrics."""

import time

import psutil

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def _format_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:,.2f} {unit}"
        num /= 1024.0
    return f"{num:,.2f} PB"


class _StatCard(QFrame):
    def __init__(self, title: str, subtitle: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("muted")
        title_lbl.setAlignment(Qt.AlignRight | Qt.AlignTop)

        value_lbl = QLabel("--")
        value_lbl.setObjectName("value")
        value_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        value_lbl.setStyleSheet("font-size: 30px; font-weight: 800;")

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("muted")
        sub_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)

        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(value_lbl)
        layout.addWidget(sub_lbl)

        self._value = value_lbl

    def set_value(self, text: str) -> None:
        self._value.setText(text)


class Dashboard(QWidget):
    """Overview page: live summary cards for CPU, Memory, Storage, Network."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._net_io_prev = psutil.net_io_counters()
        self._time_prev = time.time()

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(16)
        grid.setContentsMargins(24, 24, 24, 24)

        self.card_cpu = _StatCard("CPU", "Processor usage")
        self.card_mem = _StatCard("Memory", "RAM usage")
        self.card_disk = _StatCard("Storage", "Disk usage")
        self.card_net = _StatCard("Network", "Upload / download")

        for i, card in enumerate(
            (self.card_cpu, self.card_mem, self.card_disk, self.card_net)
        ):
            grid.addWidget(card, 0, i)

        grid.setColumnStretch(4, 1)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 8)
        heading = QLabel("Dashboard")
        heading.setObjectName("heading")
        sub = QLabel("Live system metrics — refreshes every second.")
        sub.setObjectName("subheading")
        header_layout.addWidget(heading)
        header_layout.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(header)
        root.addWidget(scroll)
        scroll.setWidget(container)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)
        self._refresh()

    def _refresh(self) -> None:
        try:
            cpu = psutil.cpu_percent(interval=None)
            self.card_cpu.set_value(f"{cpu:.1f} %")

            mem = psutil.virtual_memory()
            self.card_mem.set_value(
                f"{mem.percent:.1f} %  ({_format_bytes(mem.used)} / {_format_bytes(mem.total)})"
            )

            disk = psutil.disk_usage("/")
            self.card_disk.set_value(
                f"{disk.percent:.1f} %  ({_format_bytes(disk.used)} / {_format_bytes(disk.total)})"
            )

            net = psutil.net_io_counters()
            now = time.time()
            if self._time_prev is not None:
                dt = max(now - self._time_prev, 0.001)
                up = (net.bytes_sent - self._net_io_prev.bytes_sent) / dt
                down = (net.bytes_recv - self._net_io_prev.bytes_recv) / dt
                self.card_net.set_value(
                    f"\u2191 {_format_bytes(up)}/s  \u2193 {_format_bytes(down)}/s"
                )
            self._net_io_prev = net
            self._time_prev = now
        except Exception:
            self.card_cpu.set_value("Error")
            self.card_mem.set_value("Error")
            self.card_disk.set_value("Error")
            self.card_net.set_value("Error")

    def stop(self) -> None:
        self._timer.stop()
