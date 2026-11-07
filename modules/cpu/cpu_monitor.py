"""CPU module: collector, data model, live graph page.

Professional and robust:
- Collector reads psutil and returns a plain dataclass (testable without GUI).
- Page widget renders a rolling 60-sample usage graph plus detail cards.
- Fail soft: missing sensors or permission errors show "Not supported", never crash.
- 1-second refresh via QTimer on the main thread (psutil calls are fast).
- Module implements the MonitorModule contract used by the shell.
"""

import platform
from dataclasses import dataclass, field
from typing import List, Optional

import psutil

from PyQt5.QtCore import QPointF, QSize, QTimer, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPolygonF, QRadialGradient
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.settings import Settings
from ui.themes import BLUE_WHITE


@dataclass
class CPUData:
    """Plain data object returned by the CPU collector."""

    name: str = "Unknown"
    logical_cores: int = 0
    physical_cores: int = 0
    usage_percent: float = 0.0
    frequency_mhz: Optional[float] = None
    per_core: List[float] = field(default_factory=list)
    temperature_c: Optional[float] = None
    supported: bool = True


class LineGraph(QWidget):
    """Rolling line graph widget. Draws a smooth usage curve over time.

    Keeps a fixed-length buffer of samples and paints a blue line on the
    current theme surface. No external charting dependency required.
    """

    def __init__(self, parent=None, max_points: int = 60) -> None:
        super().__init__(parent)
        self._max_points = max_points
        self._samples: List[float] = []
        self.setMinimumSize(QSize(320, 200))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def add_sample(self, value: float) -> None:
        value = max(0.0, min(100.0, value))
        self._samples.append(value)
        if len(self._samples) > self._max_points:
            self._samples = self._samples[-self._max_points :]
        self.update()

    def set_samples(self, samples: List[float]) -> None:
        self._samples = [max(0.0, min(100.0, s)) for s in samples][
            -self._max_points :
        ]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        w = rect.width()
        h = rect.height()
        if w < 10 or h < 10 or not self._samples:
            return

        palette = BLUE_WHITE
        accent = QColor(palette["accent"])       # #3B82F6
        accent_glow = QColor(palette["accent"])  # glow fill
        accent_glow.setAlpha(30)
        grid = QColor(palette["border"])         # #E2E8F0
        text = QColor(palette["text_muted"])     # #94A3B8

        # Grid lines
        for i in range(1, 4):
            y = h * i / 4
            painter.setPen(QPen(grid, 1))
            painter.drawLine(0, int(y), w, int(y))
            painter.setPen(QPen(text, 1))
            painter.drawText(4, int(y) - 4, f"{int((4 - i) * 25)}%")

        if len(self._samples) < 2:
            return

        # Build polygon: trace the line across the width
        points = QPolygonF()
        step = w / max(1, len(self._samples) - 1)
        for i, sample in enumerate(self._samples):
            x = i * step
            y = h - (sample / 100.0) * h
            points.append(QPointF(x, y))

        # Fill area under the line
        fill_poly = QPolygonF(points)
        fill_poly.append(QPointF(w, h))
        fill_poly.append(QPointF(0, h))

        gradient = QRadialGradient(w / 2, h / 2, max(w, h))
        gradient.setColorAt(0, accent_glow)
        gradient.setColorAt(1, QColor(accent.red(), accent.green(), accent.blue(), 8))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(fill_poly)

        # Line
        pen = QPen(accent, 2.2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPolyline(points)

        # Current value dot
        last_x = (len(self._samples) - 1) * step
        last_y = h - (self._samples[-1] / 100.0) * h
        painter.setBrush(accent)
        painter.drawEllipse(int(last_x - 4), int(last_y - 4), 8, 8)


class CPUMonitorModule:
    """CPU feature module: collector + page widget.

    Implements the MonitorModule contract:
        id, title, icon, create_page(), start(), stop()
    """

    id = "cpu"
    title = "CPU"
    icon = "\u25FC"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timer: Optional[QTimer] = None
        self._page: Optional["CPUPage"] = None
        self._history: List[float] = []

    def create_page(self) -> QWidget:
        self._page = CPUPage(self._settings, self)
        return self._page

    def start(self) -> None:
        if self._timer is None:
            self._timer = QTimer()
            self._timer.timeout.connect(self._tick)
            interval = int(self._settings.get("refresh_interval_ms", 1000))
            self._timer.start(interval)
        self._tick()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def _tick(self) -> None:
        data = self.collect()
        if self._page is not None:
            self._page.update_data(data)

    def collect(self) -> CPUData:
        """Read CPU data with psutil. Fail soft — never raise."""
        try:
            name = self._cpu_name()
        except Exception:
            name = "Unknown"

        try:
            logical = psutil.cpu_count(logical=True) or 0
        except Exception:
            logical = 0

        try:
            physical = psutil.cpu_count(logical=False) or 0
        except Exception:
            physical = 0

        try:
            usage = psutil.cpu_percent(interval=None)
        except Exception:
            usage = 0.0

        try:
            freq = psutil.cpu_freq()
            freq_mhz = freq.current if freq else None
        except Exception:
            freq_mhz = None

        try:
            per_core = psutil.cpu_percent(interval=None, percpu=True) or []
        except Exception:
            per_core = []

        try:
            temps = psutil.sensors_temperatures()
            temp_c = None
            for _key, entries in temps.items():
                for entry in entries:
                    if entry.current is not None:
                        temp_c = entry.current
                        break
                if temp_c is not None:
                    break
        except Exception:
            temp_c = None

        supported = logical > 0

        data = CPUData(
            name=name,
            logical_cores=logical,
            physical_cores=physical,
            usage_percent=usage,
            frequency_mhz=freq_mhz,
            per_core=per_core,
            temperature_c=temp_c,
            supported=supported,
        )

        self._history.append(data.usage_percent)
        max_points = int(self._settings.get("graph_history_points", 60))
        if len(self._history) > max_points:
            self._history = self._history[-max_points:]

        return data

    @staticmethod
    def _cpu_name() -> str:
        try:
            name = platform.processor()
            if name and name.strip():
                return name
        except Exception:
            pass
        try:
            return platform.machine()
        except Exception:
            return "Unknown"


class _StatCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("muted")
        title_lbl.setAlignment(Qt.AlignRight | Qt.AlignTop)

        value_lbl = QLabel(value)
        value_lbl.setObjectName("value")
        value_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        value_lbl.setStyleSheet("font-size: 28px; font-weight: 800;")

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


class CPUPage(QWidget):
    """CPU page widget: detail cards + live usage graph."""

    def __init__(self, settings: Settings, module: CPUMonitorModule, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._module = module

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # Header
        header = QHBoxLayout()
        heading = QLabel("CPU")
        heading.setObjectName("heading")
        sub = QLabel("Processor usage, frequency, cores, and live history.")
        sub.setObjectName("subheading")
        header.addWidget(heading)
        header.addStretch()
        header.addWidget(sub)
        root.addLayout(header)

        # Stat cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_usage = _StatCard("Usage", "-- %", "Current processor load")
        self.card_cores = _StatCard("Cores", "--", "Logical / physical")
        self.card_freq = _StatCard("Frequency", "-- MHz", "Current clock speed")
        self.card_temp = _StatCard("Temperature", "-- °C", "Package temperature")

        for card in (self.card_usage, self.card_cores, self.card_freq, self.card_temp):
            cards_layout.addWidget(card)

        root.addLayout(cards_layout)

        # Graph
        graph_label = QLabel("Usage history (60s)")
        graph_label.setObjectName("subheading")
        root.addWidget(graph_label)

        self._graph = LineGraph()
        self._graph.setMinimumHeight(220)
        root.addWidget(self._graph, 1)

        # Per-core mini bars
        core_label = QLabel("Per-core load")
        core_label.setObjectName("subheading")
        root.addWidget(core_label)
        self._cores_container = QVBoxLayout()
        self._cores_container.setSpacing(6)
        root.addLayout(self._cores_container)

        root.addStretch()

        scroll.setWidget(container)

        page_root = QVBoxLayout(self)
        page_root.setContentsMargins(0, 0, 0, 0)
        page_root.setSpacing(0)
        page_root.addWidget(scroll)

    def update_data(self, data: CPUData) -> None:
        if not data.supported:
            self.card_usage.set_value("Not supported")
            self.card_cores.set_value("—")
            self.card_freq.set_value("—")
            self.card_temp.set_value("—")
            self._graph.set_samples([0.0] * 60)
            self._render_cores([])
            return

        self.card_usage.set_value(f"{data.usage_percent:.1f} %")
        self.card_cores.set_value(
            f"{data.logical_cores} / {data.physical_cores or '?'}"
        )
        freq_text = f"{data.frequency_mhz:.0f}" if data.frequency_mhz else "—"
        self.card_freq.set_value(f"{freq_text} MHz")
        temp_text = f"{data.temperature_c:.0f}" if data.temperature_c is not None else "—"
        self.card_temp.set_value(f"{temp_text} °C")

        self._graph.set_samples(self._module._history)
        self._render_cores(data.per_core)

    def _render_cores(self, per_core: List[float]) -> None:
        # Clear existing
        while self._cores_container.count():
            item = self._cores_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not per_core:
            empty = QLabel("Per-core data not available")
            empty.setObjectName("muted")
            self._cores_container.addWidget(empty)
            return

        for i, pct in enumerate(per_core):
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(f"Core {i}")
            lbl.setFixedWidth(56)
            lbl.setStyleSheet("font-size: 12px; color: #64748B;")

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(pct))
            bar.setFixedHeight(8)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                "QProgressBar { border: none; background: #E2E8F0; border-radius: 4px; }"
                "QProgressBar::chunk { background: #3B82F6; border-radius: 4px; }"
            )

            pct_lbl = QLabel(f"{pct:.0f}%")
            pct_lbl.setFixedWidth(36)
            pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            pct_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")

            row.addWidget(lbl)
            row.addWidget(bar, 1)
            row.addWidget(pct_lbl)

            row_widget = QWidget()
            row_widget.setLayout(row)
            self._cores_container.addWidget(row_widget)
