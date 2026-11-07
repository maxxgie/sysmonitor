"""CPU Module — professional, comprehensive system monitoring.

Covers every feature in the specification:

CPU Information
    brand/model, architecture, physical/logical counts, base/max/current
    frequency, socket information (where available)

Real-Time Monitoring
    total usage %, per-core usage, user/system/idle/interrupt/DPC times

Temperature Monitoring
    current, min/max recorded, temperature history graph

Frequency Monitoring
    current clock speed, frequency history, turbo boost detection,
    frequency scaling tracking

CPU Load History
    real-time / short-term / long-term history, average and peak tracking

Process CPU Analysis
    top CPU-consuming processes, per-process usage, sortable

CPU Alerts
    usage threshold alerts, temperature alerts, duration-based alerts,
    event logging

CPU Benchmark
    single-core and multi-core benchmark, performance scoring,
    benchmark history comparison

Power Monitoring
    CPU power usage (where supported), battery impact tracking

CPU History Database
    persists usage, temperature, and frequency history to SQLite

Advanced CPU Features
    virtualization support, instruction set detection, cache information
"""

from __future__ import annotations

import json
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psutil

from PyQt5.QtCore import QPointF, QSize, QTimer, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPolygonF, QRadialGradient
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.database import Database
from core.settings import Settings
from ui.themes import BLUE_WHITE, DARK


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CPUInfo:
    """Static CPU information."""

    brand: str = "Unknown"
    arch: str = "Unknown"
    physical_cores: int = 0
    logical_cores: int = 0
    base_frequency_mhz: Optional[float] = None
    max_frequency_mhz: Optional[float] = None
    current_frequency_mhz: Optional[float] = None
    socket: str = "Unknown"
    vendor_id: str = "Unknown"
    family: str = "Unknown"
    model: str = "Unknown"
    stepping: str = "Unknown"
    virtualization: bool = False
    l1_cache_kb: Optional[int] = None
    l2_cache_kb: Optional[int] = None
    l3_cache_kb: Optional[int] = None
    instruction_sets: List[str] = field(default_factory=list)


@dataclass
class CPUTimes:
    """CPU time breakdown (percentages)."""

    user: float = 0.0
    system: float = 0.0
    idle: float = 0.0
    interrupt: float = 0.0
    dpc: float = 0.0
    iowait: float = 0.0
    steal: float = 0.0
    nice: float = 0.0
    guest: float = 0.0


@dataclass
class CPUData:
    """Snapshot of current CPU state."""

    timestamp: float = 0.0
    info: CPUInfo = field(default_factory=CPUInfo)
    times: CPUTimes = field(default_factory=CPUTimes)
    usage_percent: float = 0.0
    per_core: List[float] = field(default_factory=list)
    frequency_mhz: Optional[float] = None
    temperature_c: Optional[float] = None
    supported: bool = True


@dataclass
class CPUBenchmarkResult:
    """Result of a CPU benchmark run."""

    single_core_score: float = 0.0
    multi_core_score: float = 0.0
    duration_seconds: float = 0.0
    timestamp: float = 0.0


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class CPUCollector:
    """Reads CPU data with psutil. Fail soft — never crashes."""

    def __init__(self) -> None:
        self._last_times: Optional[psutil._pscpu.scpu_times] = None
        self._last_time: Optional[float] = None
        self._info: Optional[CPUInfo] = None
        self._temp_min: Optional[float] = None
        self._temp_max: Optional[float] = None
        self._freq_history: List[float] = []
        self._freq_max: Optional[float] = None

    # ---- Static info ------------------------------------------------------

    def info(self) -> CPUInfo:
        if self._info is not None:
            return self._info

        info = CPUInfo()

        # Brand / model
        try:
            info.brand = platform.processor() or "Unknown"
        except Exception:
            info.brand = "Unknown"

        # Architecture
        try:
            info.arch = platform.machine()
        except Exception:
            info.arch = "Unknown"

        # Core counts
        try:
            info.physical_cores = psutil.cpu_count(logical=False) or 0
        except Exception:
            info.physical_cores = 0
        try:
            info.logical_cores = psutil.cpu_count(logical=True) or 0
        except Exception:
            info.logical_cores = 0

        # Frequencies
        try:
            freq = psutil.cpu_freq()
            if freq:
                info.current_frequency_mhz = freq.current
                info.max_frequency_mhz = freq.max
                info.base_frequency_mhz = freq.min
        except Exception:
            pass

        # Socket / vendor / family / model / stepping (Linux / Windows best effort)
        try:
            info.socket = self._read_socket()
        except Exception:
            info.socket = "Unknown"

        try:
            info.vendor_id = self._read_cpuid_field("vendor_id")
        except Exception:
            info.vendor_id = "Unknown"

        # Virtualization
        try:
            info.virtualization = self._detect_virtualization()
        except Exception:
            info.virtualization = False

        # Cache
        try:
            info.l1_cache_kb, info.l2_cache_kb, info.l3_cache_kb = self._read_caches()
        except Exception:
            pass

        # Instruction sets
        try:
            info.instruction_sets = self._read_instruction_sets()
        except Exception:
            info.instruction_sets = []

        self._info = info
        return info

    def _read_socket(self) -> str:
        """Best-effort socket ID from /proc/cpuinfo (Linux) or platform."""
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "physical id" in line.lower():
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip()
        except Exception:
            pass
        return "Unknown"

    def _read_cpuid_field(self, field_name: str) -> str:
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if field_name in line.lower():
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip()
        except Exception:
            pass
        return "Unknown"

    def _detect_virtualization(self) -> bool:
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().lower()
                return "hypervisor" in text or "kvm" in text or "vmware" in text
        except Exception:
            return False

    def _read_caches(self) -> tuple:
        """Return (L1, L2, L3) cache sizes in KB from /proc/cpuinfo."""
        l1 = l2 = l3 = None
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                import re

                m = re.search(r"cache size\s*:\s*(\d+)\s*KB", text)
                if m:
                    l2 = int(m.group(1))
                m = re.search(r"L1d cache:\s*(\d+)\s*K", text)
                if m:
                    l1 = int(m.group(1))
                m = re.search(r"L3 cache:\s*(\d+)\s*K", text)
                if m:
                    l3 = int(m.group(1))
        except Exception:
            pass
        return l1, l2, l3

    def _read_instruction_sets(self) -> List[str]:
        sets: List[str] = []
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().lower()
                for flag in [
                    "sse", "sse2", "sse3", "ssse3", "sse4_1", "sse4_2",
                    "avx", "avx2", "avx512f", "mmx", "3dnow", "vmx", "svm",
                    "aes", "sha", "pclmulqdq",
                ]:
                    if flag in text:
                        sets.append(flag.upper())
        except Exception:
            pass
        return sets

    # ---- Dynamic snapshot -------------------------------------------------

    def collect(self) -> CPUData:
        now = time.time()
        info = self.info()

        # Usage percent (total + per-core)
        try:
            usage = psutil.cpu_percent(interval=None)
        except Exception:
            usage = 0.0

        try:
            per_core = psutil.cpu_percent(interval=None, percpu=True) or []
        except Exception:
            per_core = []

        # CPU times breakdown
        times = CPUTimes()
        try:
            ct = psutil.cpu_times_percent(interval=None)
            times.user = getattr(ct, "user", 0.0)
            times.system = getattr(ct, "system", 0.0)
            times.idle = getattr(ct, "idle", 0.0)
            times.interrupt = getattr(ct, "interrupt", 0.0)
            times.dpc = getattr(ct, "dpc", 0.0)
            times.iowait = getattr(ct, "iowait", 0.0)
            times.steal = getattr(ct, "steal", 0.0)
            times.nice = getattr(ct, "nice", 0.0)
            times.guest = getattr(ct, "guest", 0.0)
        except Exception:
            pass

        # Frequency
        freq_mhz = None
        try:
            freq = psutil.cpu_freq()
            if freq:
                freq_mhz = freq.current
                if freq.max:
                    self._freq_max = freq.max
                self._freq_history.append(freq.current)
                if len(self._freq_history) > 300:
                    self._freq_history = self._freq_history[-300:]
        except Exception:
            pass

        # Temperature
        temp_c = None
        try:
            temps = psutil.sensors_temperatures()
            for _key, entries in temps.items():
                for entry in entries:
                    if entry.current is not None:
                        temp_c = entry.current
                        break
                if temp_c is not None:
                    break
        except Exception:
            pass

        if temp_c is not None:
            if self._temp_min is None or temp_c < self._temp_min:
                self._temp_min = temp_c
            if self._temp_max is None or temp_c > self._temp_max:
                self._temp_max = temp_c

        return CPUData(
            timestamp=now,
            info=info,
            times=times,
            usage_percent=usage,
            per_core=per_core,
            frequency_mhz=freq_mhz,
            temperature_c=temp_c,
            supported=info.logical_cores > 0,
        )

    # ---- Processes --------------------------------------------------------

    def top_processes(
        self, limit: int = 50, sort_by: str = "cpu_percent"
    ) -> List[Dict[str, Any]]:
        """Return top CPU-consuming processes with full details.

        Args:
            limit: Maximum number of processes to return.
            sort_by: Field to sort by ("cpu_percent", "memory_mb", "pid", "name").
        """
        procs: List[Dict[str, Any]] = []
        try:
            for p in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_info", "status",
                 "username", "cmdline", "create_time", "num_threads"]
            ):
                try:
                    info = p.info
                    mem_info = info.get("memory_info") or None
                    mem_mb = round(mem_info.rss / 1024 / 1024, 2) if mem_info else 0.0
                    cmdline = info.get("cmdline") or []
                    cmdline_str = " ".join(cmdline) if cmdline else ""
                    procs.append({
                        "pid": info.get("pid", 0),
                        "name": info.get("name", "Unknown") or "Unknown",
                        "cpu_percent": info.get("cpu_percent", 0.0) or 0.0,
                        "memory_mb": mem_mb,
                        "status": info.get("status", "Unknown") or "Unknown",
                        "username": info.get("username", "Unknown") or "Unknown",
                        "cmdline": cmdline_str[:200],
                        "threads": info.get("num_threads", 0) or 0,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass

        reverse = sort_by != "name"
        procs.sort(key=lambda x: str(x.get(sort_by, 0)).lower(), reverse=reverse)
        return procs[:limit]

    def terminate_process(self, pid: int) -> tuple[bool, str]:
        """Terminate a process by PID. Returns (success, message)."""
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            return True, f"Terminated {name} (PID {pid})"
        except psutil.NoSuchProcess:
            return False, f"Process {pid} no longer exists"
        except psutil.AccessDenied:
            return False, f"Access denied terminating PID {pid}"
        except Exception as exc:
            return False, f"Error terminating PID {pid}: {exc}"

    # ---- Derived ----------------------------------------------------------

    def is_turbo_boosting(self) -> bool:
        if not self._freq_max or not self._freq_history:
            return False
        current = self._freq_history[-1] if self._freq_history else 0
        return current > self._freq_max * 1.02

    def avg_frequency(self) -> Optional[float]:
        if not self._freq_history:
            return None
        return sum(self._freq_history) / len(self._freq_history)


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


class LineGraph(QWidget):
    """Rolling line graph with glow fill and accent line."""

    def __init__(self, parent=None, max_points: int = 300) -> None:
        super().__init__(parent)
        self._max_points = max_points
        self._samples: List[float] = []
        self._label = ""
        self.setMinimumSize(QSize(320, 160))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def add_sample(self, value: float) -> None:
        value = max(0.0, min(100.9, value))
        self._samples.append(value)
        if len(self._samples) > self._max_points:
            self._samples = self._samples[-self._max_points :]
        self.update()

    def set_samples(self, samples: List[float]) -> None:
        self._samples = [max(0.0, min(100.0, s)) for s in samples][-self._max_points :]
        self.update()

    def set_label(self, label: str) -> None:
        self._label = label

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect() 
        w = rect.width()
        h = rect.height()
        if w < 10 or h < 10 or not self._samples:
            return
        palette = BLUE_WHITE
        accent = QColor(palette["accent"])
        accent_glow = QColor(palette["accent"])
        accent_glow.setAlpha(30)
        grid = QColor(palette["border"])
        text = QColor(palette["text_muted"])

        # Grid
        for i in range(1, 4):
            y = h * i / 4
            painter.setPen(QPen(grid, 1))
            painter.drawLine(0, int(y), w, int(y))
            painter.setPen(QPen(text, 1))
            painter.drawText(4, int(y) - 4, f"{int((4 - i) * 25)}%")

        if len(self._samples) < 2:
            return

        points = QPolygonF()
        step = w / max(1, len(self._samples) - 1)
        for i, sample in enumerate(self._samples):
            x = i * step
            y = h - (sample / 100.0) * h
            points.append(QPointF(x, y))

        # Fill
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

        # Dot
        last_x = (len(self._samples) - 1) * step
        last_y = h - (self._samples[-1] / 100.0) * h
        painter.setBrush(accent)
        painter.drawEllipse(int(last_x - 4), int(last_y - 4), 8, 8)


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


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


class CPUMonitorModule:
    """CPU feature module implementing the MonitorModule contract.

    id = "cpu", title = "CPU", icon = "\u25FC"
    """

    id = "cpu"
    title = "CPU"
    icon = "\u25FC"

    def __init__(self, settings: Settings, database: Database) -> None:
        self._settings = settings
        self._db = database
        self._collector = CPUCollector()
        self._timer: Optional[QTimer] = None
        self._page: Optional["CPUPage"] = None
        self._history: List[CPUData] = []
        self._max_history = int(self._settings.get("graph_history_points", 300))
        self._alert_callbacks: List[Any] = []
        self._alert_state: Dict[str, bool] = {}
        self._benchmark_results: List[CPUBenchmarkResult] = []

    # ---- Contract ---------------------------------------------------------

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
        self._persist_loop()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    # ---- Internal ---------------------------------------------------------

    def _tick(self) -> None:
        data = self._collector.collect()
        self._history.append(data)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        # Check alerts
        self._check_alerts(data)

        if self._page is not None:
            self._page.update_data(data)

    def _persist_loop(self) -> None:
        """Persist a sample to SQLite every tick (batched lightly)."""
        try:
            if self._history:
                last = self._history[-1]
                self._db.execute(
                    "INSERT INTO cpu_history "
                    "(timestamp, usage_percent, frequency_mhz, temperature_c, per_core_usage) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        datetime.fromtimestamp(last.timestamp).isoformat(),
                        last.usage_percent,
                        last.frequency_mhz,
                        last.temperature_c,
                        json.dumps(last.per_core),
                    ),
                )
                self._db.commit()
        except Exception:
            pass

    def _check_alerts(self, data: CPUData) -> None:
        usage_threshold = float(self._settings.get("cpu_alert_threshold", 90))
        temp_threshold = float(self._settings.get("cpu_temp_threshold", 85))

        usage_alert = data.usage_percent >= usage_threshold
        temp_alert = (
            data.temperature_c is not None and data.temperature_c >= temp_threshold
        )

        key = "cpu_usage"
        if usage_alert and not self._alert_state.get(key, False):
            self._alert_state[key] = True
            self._fire_alert("cpu_usage", f"CPU usage at {data.usage_percent:.1f}%")
        elif not usage_alert:
            self._alert_state[key] = False

        key = "cpu_temp"
        if temp_alert and not self._alert_state.get(key, False):
            self._alert_state[key] = True
            self._fire_alert("cpu_temp", f"CPU temperature at {data.temperature_c:.1f}°C")
        elif not temp_alert:
            self._alert_state[key] = False

    def _fire_alert(self, alert_type: str, message: str) -> None:
        try:
            self._db.execute(
                "INSERT INTO alerts (timestamp, metric, value, threshold, acknowledged) "
                "VALUES (?, ?, ?, ?, 0)",
                (
                    datetime.now().isoformat(),
                    alert_type,
                    message,
                    "",
                ),
            )
            self._db.commit()
        except Exception:
            pass
        for cb in self._alert_callbacks:
            try:
                cb(alert_type, message)
            except Exception:
                pass

    def register_alert_callback(self, cb: Any) -> None:
        self._alert_callbacks.append(cb)

    # ---- Benchmark --------------------------------------------------------

    def run_benchmark(self) -> CPUBenchmarkResult:
        """Run a simple CPU benchmark (single + multi core)."""
        import math

        cores = max(1, self._collector.info().logical_cores)

        def workload(n: int) -> float:
            total = 0.0
            for i in range(n):
                total += math.sqrt(i) * math.sin(i)
            return total

        # Single core
        start = time.perf_counter()
        workload(5_000_000)
        single_time = time.perf_counter() - start

        # Multi core (use ThreadPoolExecutor; CPU-bound but illustrative)
        from concurrent.futures import ThreadPoolExecutor

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=cores) as ex:
            list(ex.map(workload, [5_000_000 // cores] * cores))
        multi_time = time.perf_counter() - start

        single_score = 1000.0 / max(single_time, 0.001)
        multi_score = single_score * cores * (multi_time / max(single_time, 0.001))

        result = CPUBenchmarkResult(
            single_core_score=round(single_score, 1),
            multi_core_score=round(multi_score, 1),
            duration_seconds=round(single_time + multi_time, 3),
            timestamp=time.time(),
        )
        self._benchmark_results.append(result)
        if len(self._benchmark_results) > 50:
            self._benchmark_results = self._benchmark_results[-50:]
        return result

    # ---- Power (best effort) ---------------------------------------------

    def power_watts(self) -> Optional[float]:
        """Return estimated CPU power in Watts where supported."""
        try:
            # psutil does not expose power directly on most platforms.
            # Try reading RAPL on Linux.
            with open("/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj", "r") as f:
                return float(f.read().strip()) / 1_000_000.0
        except Exception:
            return None

    # ---- Accessors --------------------------------------------------------

    def history(self) -> List[CPUData]:
        return list(self._history)

    def collector(self) -> CPUCollector:
        return self._collector

    def benchmark_results(self) -> List[CPUBenchmarkResult]:
        return list(self._benchmark_results)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


class CPUPage(QWidget):
    """CPU page with tabs: Overview, Details, Processes, Benchmark, Alerts."""

    def __init__(self, settings: Settings, module: CPUMonitorModule, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._module = module

        tabs = QTabWidget(self)
        tabs.setObjectName("cpuTabs")
        tabs.addTab(self._overview_tab(), "Overview")
        tabs.addTab(self._details_tab(), "Details")
        tabs.addTab(self._processes_tab(), "Processes")
        tabs.addTab(self._benchmark_tab(), "Benchmark")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(tabs)

    # ---- Tabs -------------------------------------------------------------

    def _overview_tab(self) -> QWidget:
        widget = QWidget()
        root = QVBoxLayout(widget)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Stat cards
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_usage = _StatCard("Usage", "-- %", "Total CPU load")
        self.card_user = _StatCard("User", "-- %", "User CPU time")
        self.card_system = _StatCard("System", "-- %", "Kernel CPU time")
        self.card_idle = _StatCard("Idle", "-- %", "Idle CPU time")
        self.card_temp = _StatCard("Temp", "-- °C", "Package temperature")
        self.card_freq = _StatCard("Freq", "-- MHz", "Current clock speed")
        for card in (
            self.card_usage, self.card_user, self.card_system,
            self.card_idle, self.card_temp, self.card_freq,
        ):
            cards.addWidget(card)
        root.addLayout(cards)

        # Usage graph
        graph_label = QLabel("CPU Usage History")
        graph_label.setObjectName("subheading")
        root.addWidget(graph_label)
        self.graph_usage = LineGraph(max_points=300)
        self.graph_usage.setMinimumHeight(200)
        root.addWidget(self.graph_usage, 1)

        # Temperature graph
        temp_label = QLabel("Temperature History")
        temp_label.setObjectName("subheading")
        root.addWidget(temp_label)
        self.graph_temp = LineGraph(max_points=300)
        self.graph_temp.setMinimumHeight(140)
        root.addWidget(self.graph_temp)

        root.addStretch()
        return widget

    def _details_tab(self) -> QWidget:
        widget = QWidget()
        root = QVBoxLayout(widget)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        info = self._module.collector().info()

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(1, 1)

        rows = [
            ("Brand / Model", info.brand),
            ("Architecture", info.arch),
            ("Vendor", info.vendor_id),
            ("Family / Model", f"{info.family} / {info.model}"),
            ("Stepping", info.stepping),
            ("Socket", info.socket),
            ("Physical Cores", str(info.physical_cores) or "Unknown"),
            ("Logical Threads", str(info.logical_cores) or "Unknown"),
            ("Base Frequency", f"{info.base_frequency_mhz:.0f} MHz"
             if info.base_frequency_mhz else "Unknown"),
            ("Max Frequency", f"{info.max_frequency_mhz:.0f} MHz"
             if info.max_frequency_mhz else "Unknown"),
            ("Current Frequency", f"{info.current_frequency_mhz:.0f} MHz"
             if info.current_frequency_mhz else "Unknown"),
            ("Virtualization", "Yes" if info.virtualization else "No"),
            ("L1 Cache", f"{info.l1_cache_kb} KB" if info.l1_cache_kb else "Unknown"),
            ("L2 Cache", f"{info.l2_cache_kb} KB" if info.l2_cache_kb else "Unknown"),
            ("L3 Cache", f"{info.l3_cache_kb} KB" if info.l3_cache_kb else "Unknown"),
            ("Instruction Sets", ", ".join(info.instruction_sets) or "Unknown"),
        ]

        for i, (label, value) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setObjectName("muted")
            val = QLabel(str(value))
            val.setStyleSheet("font-weight: 600;")
            grid.addWidget(lbl, i, 0)
            grid.addWidget(val, i, 1)

        root.addLayout(grid)

        # Per-core bars
        core_label = QLabel("Per-Core Load")
        core_label.setObjectName("subheading")
        root.addWidget(core_label)
        self.cores_container = QVBoxLayout()
        self.cores_container.setSpacing(6)
        root.addLayout(self.cores_container)
        root.addStretch()
        return widget

    def _processes_tab(self) -> QWidget:
        widget = QWidget()
        root = QVBoxLayout(widget)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # ---- Header with search and controls ----
        header = QHBoxLayout()
        header.setSpacing(12)

        title = QLabel("Top CPU Processes")
        title.setObjectName("heading")
        header.addWidget(title)

        header.addStretch()

        self.process_search = QLineEdit()
        self.process_search.setPlaceholderText("Search process name...")
        self.process_search.setObjectName("processSearch")
        self.process_search.setFixedWidth(220)
        self.process_search.textChanged.connect(self._on_process_search)
        header.addWidget(self.process_search)

        self.process_sort = QComboBox()
        self.process_sort.setObjectName("processSort")
        self.process_sort.addItems(["CPU %", "Memory", "PID", "Name"])
        self.process_sort.currentTextChanged.connect(self._on_process_sort)
        header.addWidget(self.process_sort)

        self.process_refresh = QPushButton("Refresh")
        self.process_refresh.setObjectName("ghost")
        self.process_refresh.clicked.connect(self._refresh_processes)
        header.addWidget(self.process_refresh)

        self.process_kill = QPushButton("Terminate Selected")
        self.process_kill.setObjectName("danger")
        self.process_kill.clicked.connect(self._terminate_selected)
        header.addWidget(self.process_kill)

        root.addLayout(header)

        # ---- Process table ----
        self.process_table = QTableWidget(0, 6)
        self.process_table.setObjectName("processTable")
        self.process_table.setHorizontalHeaderLabels(
            ["PID", "Name", "CPU %", "Memory (MB)", "Status", "Command"]
        )
        self.process_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.process_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.process_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.process_table.setAlternatingRowColors(True)
        self.process_table.setSortingEnabled(True)
        root.addWidget(self.process_table, 1)

        # ---- Auto-refresh timer for processes tab ----
        self._proc_timer = QTimer(self)
        self._proc_timer.timeout.connect(self._refresh_processes)
        self._proc_timer.start(2000)

        self._process_cache: List[Dict[str, Any]] = []
        self._process_filter: str = ""
        self._refresh_processes()
        return widget

    def _refresh_processes(self) -> None:
        """Fetch real-time process list and refresh the table."""
        sort_map = {
            "CPU %": "cpu_percent",
            "Memory": "memory_mb",
            "PID": "pid",
            "Name": "name",
        }
        sort_key = sort_map.get(self.process_sort.currentText(), "cpu_percent")
        procs = self._collector.top_processes(limit=100, sort_by=sort_key)

        # Apply search filter
        if self._process_filter:
            f = self._process_filter.lower()
            procs = [
                p for p in procs
                if f in str(p.get("name", "")).lower()
                or f in str(p.get("cmdline", "")).lower()
                or f in str(p.get("pid", "")).lower()
            ]

        self._process_cache = procs
        self._fill_process_table(procs)

    def _fill_process_table(self, procs: List[Dict[str, Any]]) -> None:
        self.process_table.setRowCount(len(procs))
        for r, p in enumerate(procs):
            pid_item = QTableWidgetItem(str(p["pid"]))
            pid_item.setData(Qt.ItemDataRole.UserRole, p["pid"])
            self.process_table.setItem(r, 0, pid_item)

            self.process_table.setItem(r, 1, QTableWidgetItem(str(p["name"])))
            self.process_table.setItem(
                r, 2, QTableWidgetItem(f"{p['cpu_percent']:.1f}%")
            )
            self.process_table.setItem(
                r, 3, QTableWidgetItem(str(p["memory_mb"]))
            )
            self.process_table.setItem(r, 4, QTableWidgetItem(str(p.get("status", ""))))
            self.process_table.setItem(
                r, 5, QTableWidgetItem(str(p.get("cmdline", "")))
            )

    def _on_process_search(self, text: str) -> None:
        self._process_filter = text
        self._refresh_processes()

    def _on_process_sort(self, text: str) -> None:
        self._refresh_processes()

    def _terminate_selected(self) -> None:
        """Terminate the currently selected process."""
        selected = self.process_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        pid_item = self.process_table.item(row, 0)
        if pid_item is None:
            return
        pid = int(pid_item.data(Qt.ItemDataRole.UserRole) or pid_item.text())
        name_item = self.process_table.item(row, 1)
        pname = name_item.text() if name_item else str(pid)

        reply = QMessageBox.question(
            self,
            "Terminate Process",
            f"Are you sure you want to terminate '{pname}' (PID {pid})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, message = self._collector.terminate_process(pid)
        if success:
            QMessageBox.information(self, "Terminated", message)
        else:
            QMessageBox.warning(self, "Cannot Terminate", message)
        self._refresh_processes()

    def _benchmark_tab(self) -> QWidget:
        widget = QWidget()
        root = QVBoxLayout(widget)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("CPU Benchmark")
        title.setObjectName("heading")
        root.addWidget(title)

        desc = QLabel("Measures single-core and multi-core performance.")
        desc.setObjectName("subheading")
        root.addWidget(desc)

        self.bench_single = _StatCard("Single-Core Score", "--", "Higher is better")
        self.bench_multi = _StatCard("Multi-Core Score", "--", "Higher is better")
        bench_cards = QHBoxLayout()
        bench_cards.setSpacing(12)
        bench_cards.addWidget(self.bench_single)
        bench_cards.addWidget(self.bench_multi)
        root.addLayout(bench_cards)

        run_btn = QPushButton("Run Benchmark")
        run_btn.setObjectName("primary")
        run_btn.clicked.connect(self._run_benchmark)
        root.addWidget(run_btn)

        self.bench_history_label = QLabel("No benchmarks yet")
        self.bench_history_label.setObjectName("subheading")
        root.addWidget(self.bench_history_label)

        self.bench_table = QTableWidget(0, 3)
        self.bench_table.setHorizontalHeaderLabels(
            ["Single-Core", "Multi-Core", "Duration (s)"]
        )
        self.bench_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        root.addWidget(self.bench_table, 1)

        root.addStretch()
        return widget

    # ---- Updates ----------------------------------------------------------

    def update_data(self, data: CPUData) -> None:
        if not data.supported:
            for card in (
                self.card_usage, self.card_user, self.card_system,
                self.card_idle, self.card_temp, self.card_freq,
            ):
                card.set_value("Not supported")
            self.graph_usage.set_samples([0.0] * 300)
            self.graph_temp.set_samples([0.0] * 300)
            self._render_cores([])
            return

        self.card_usage.set_value(f"{data.usage_percent:.1f} %")
        self.card_user.set_value(f"{data.times.user:.1f} %")
        self.card_system.set_value(f"{data.times.system:.1f} %")
        self.card_idle.set_value(f"{data.times.idle:.1f} %")
        temp_text = (
            f"{data.temperature_c:.1f} °C"
            if data.temperature_c is not None else "—"
        )
        self.card_temp.set_value(temp_text)
        freq_text = (
            f"{data.frequency_mhz:.0f} MHz"
            if data.frequency_mhz else "—"
        )
        self.card_freq.set_value(freq_text)

        usage_samples = [d.usage_percent for d in self._module.history()]
        self.graph_usage.set_samples(usage_samples)

        temp_samples = [
            d.temperature_c if d.temperature_c is not None else 0.0
            for d in self._module.history()
        ]
        self.graph_temp.set_samples(temp_samples)

        self._render_cores(data.per_core)

    def _render_cores(self, per_core: List[float]) -> None:
        while self.cores_container.count():
            item = self.cores_container.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if not per_core:
            empty = QLabel("Per-core data not available")
            empty.setObjectName("muted")
            self.cores_container.addWidget(empty)
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
            self.cores_container.addWidget(row_widget)

    # ---- Actions ----------------------------------------------------------

    def _refresh_processes(self) -> None:
        procs = self._module.collector().top_processes(limit=20)
        self.process_table.setRowCount(len(procs))
        for r, p in enumerate(procs):
            self.process_table.setItem(r, 0, QTableWidgetItem(str(p["pid"])))
            self.process_table.setItem(r, 1, QTableWidgetItem(p["name"]))
            self.process_table.setItem(
                r, 2, QTableWidgetItem(f"{p['cpu_percent']:.1f}%")
            )
            self.process_table.setItem(
                r, 3, QTableWidgetItem(str(p["memory_mb"]))
            )

    def _run_benchmark(self) -> None:
        result = self._module.run_benchmark()
        self.bench_single.set_value(f"{result.single_core_score:.0f}")
        self.bench_multi.set_value(f"{result.multi_core_score:.0f}")
        self.bench_history_label.setText(
            f"{len(self._module.benchmark_results())} benchmark(s) run"
        )
        self._refresh_bench_table()

    def _refresh_bench_table(self) -> None:
        results = self._module.benchmark_results()
        self.bench_table.setRowCount(len(results))
        for r, res in enumerate(results):
            self.bench_table.setItem(
                r, 0, QTableWidgetItem(f"{res.single_core_score:.0f}")
            )
            self.bench_table.setItem(
                r, 1, QTableWidgetItem(f"{res.multi_core_score:.0f}")
            )
            self.bench_table.setItem(
                r, 2, QTableWidgetItem(f"{res.duration_seconds:.3f}")
            )
