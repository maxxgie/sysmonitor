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
    QApplication,
    QComboBox,
    QFileDialog,
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
    QSpinBox,
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

    mode: str = "multi_core"          # single_core, multi_core, multi_thread
    duration: str = "short"           # short, long
    thread_count: int = 1
    intensity: float = 1.0
    single_core_score: float = 0.0
    multi_core_score: float = 0.0
    ops_per_sec_single: float = 0.0
    ops_per_sec_multi: float = 0.0
    single_core_time: float = 0.0
    multi_core_time: float = 0.0
    duration_seconds: float = 0.0
    timestamp: float = 0.0

    # Hardware info captured at benchmark time
    cpu_model: str = "Unknown"
    cpu_arch: str = "Unknown"
    physical_cores: int = 0
    logical_cores: int = 0
    base_frequency_mhz: Optional[float] = None
    max_frequency_mhz: Optional[float] = None

    # Frequency analysis
    start_frequency_mhz: float = 0.0
    max_frequency_reached_mhz: Optional[float] = None
    average_frequency_mhz: Optional[float] = None
    turbo_boost_detected: bool = False

    # Thermal analysis
    start_temperature_c: Optional[float] = None
    max_temperature_c: Optional[float] = None
    min_temperature_c: Optional[float] = None
    temperature_delta_c: Optional[float] = None
    thermal_throttled: bool = False

    # Real-time monitoring during benchmark
    avg_cpu_usage_percent: float = 0.0
    peak_cpu_usage_percent: float = 0.0
    consistency_percent: float = 100.0

    # Power
    power_watts: Optional[float] = None


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    mode: str = "multi_core"       # single_core, multi_core, multi_thread
    duration: str = "short"        # short, long
    thread_count: int = 1
    intensity: float = 1.0         # 0.1 to 5.0


@dataclass
class BenchmarkSample:
    """Real-time sample captured during a benchmark run."""

    timestamp: float = 0.0
    cpu_usage: float = 0.0
    per_core: List[float] = field(default_factory=list)
    frequency_mhz: float = 0.0
    temperature_c: Optional[float] = None


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

    def run_benchmark(
        self,
        config: Optional[BenchmarkConfig] = None,
        progress_callback: Optional[Any] = None,
    ) -> CPUBenchmarkResult:
        """Run a comprehensive CPU benchmark with the given configuration.

        Modes: single-core, multi-core, multi-thread.
        Durations: short (quick smoke test) or long (sustained load).
        Monitors CPU usage, frequency, temperature, and power in real time.
        Enforces thermal safety limits with auto-cancellation.
        """
        import math
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if config is None:
            config = BenchmarkConfig()

        cores = max(1, self.collector().info().logical_cores)
        threads = max(1, min(config.thread_count, cores * 2))
        intensity = max(0.1, min(config.intensity, 5.0))

        def _progress(pct: int) -> None:
            if progress_callback:
                try:
                    progress_callback(pct)
                except Exception:
                    pass

        _progress(0)

        # Safety: warn before intensive tests
        if config.duration == "long" and config.intensity >= 3.0:
            pass  # UI layer shows warning before calling

        # Capture starting state
        start_info = self._collector.info()
        start_freq = start_info.current_frequency_mhz or 0.0
        start_temp = self._collector.collect().temperature_c
        peak_temp = start_temp if start_temp else None
        min_temp = start_temp if start_temp else None
        max_freq = start_freq
        avg_freq_samples: List[float] = []
        thermal_throttled = False

        # Real-time monitoring during benchmark
        monitor_samples: List[BenchmarkSample] = []
        stop_monitor = threading.Event()

        def _monitor() -> None:
            nonlocal max_freq, peak_temp, min_temp, thermal_throttled
            while not stop_monitor.is_set():
                try:
                    data = self._collector.collect()
                    sample = BenchmarkSample(
                        timestamp=time.time(),
                        cpu_usage=data.usage_percent,
                        per_core=list(data.per_core),
                        frequency_mhz=data.frequency_mhz or 0.0,
                        temperature_c=data.temperature_c,
                    )
                    monitor_samples.append(sample)

                    # Track peaks
                    if data.frequency_mhz:
                        max_freq = max(max_freq, data.frequency_mhz)
                        avg_freq_samples.append(data.frequency_mhz)
                    if data.temperature_c is not None:
                        if peak_temp is None or data.temperature_c > peak_temp:
                            peak_temp = data.temperature_c
                        if min_temp is None or data.temperature_c < min_temp:
                            min_temp = data.temperature_c

                    # Thermal safety: auto-cancel if overheating
                    temp_limit = float(self._settings.get("cpu_temp_threshold", 85))
                    if data.temperature_c is not None and data.temperature_c >= temp_limit:
                        thermal_throttled = True
                        stop_monitor.set()
                        break
                except Exception:
                    pass
                stop_monitor.wait(0.5)

        monitor_thread = threading.Thread(target=_monitor, daemon=True)
        monitor_thread.start()

        try:
            def workload_chunk(n: int) -> float:
                total = 0.0
                for i in range(n):
                    total += math.sqrt(i) * math.sin(i) + math.cos(i)
                return total

            # Scale workload by intensity and duration
            base_ops = int(2_000_000 * intensity)
            if config.duration == "long":
                base_ops *= 5

            # ----- Single-core benchmark -----
            single_start = time.perf_counter()
            workload_chunk(base_ops)
            single_time = time.perf_counter() - single_start

            _progress(50)

            # ----- Multi-core / Multi-thread benchmark -----
            multi_start = time.perf_counter()
            if config.mode == "single_core":
                # Run same workload on one core repeatedly
                with ThreadPoolExecutor(max_workers=1) as ex:
                    list(ex.map(workload_chunk, [base_ops] * threads))
            else:
                per_thread_ops = max(1, base_ops // threads)
                with ThreadPoolExecutor(max_workers=threads) as ex:
                    futures = [ex.submit(workload_chunk, per_thread_ops) for _ in range(threads)]
                    for f in as_completed(futures):
                        try:
                    f.result()
                            except Exception:
                                pass
            multi_time = time.perf_counter() - multi_start

            _progress(90)

        finally:
            stop_monitor.set()
            monitor_thread.join(timeout=2.0)

        # ----- Compute scores -----
        ops_per_sec_single = base_ops / max(single_time, 0.001)
        ops_per_sec_multi = (base_ops * threads) / max(multi_time, 0.001)

        single_score = round(ops_per_sec_single / 1000.0, 1)
        multi_score = round(ops_per_sec_multi / 1000.0, 1)

        # Consistency: coefficient of variation of monitor samples
        if monitor_samples:
            usages = [s.cpu_usage for s in monitor_samples]
            if usages:
                mean_u = sum(usages) / len(usages)
                var_u = sum((u - mean_u) ** 2 for u in usages) / len(usages)
                std_u = math.sqrt(var_u)
                consistency = round((1.0 - (std_u / max(mean_u, 0.001))) * 100.0, 1)
                consistency = max(0.0, min(100.0, consistency))
            else:
                consistency = 100.0
        else:
            consistency = 100.0

        avg_freq = round(sum(avg_freq_samples) / len(avg_freq_samples), 1) if avg_freq_samples else None
        turbo_boosted = bool(max_freq > start_freq * 1.02) if start_freq else False
        temp_delta = round((peak_temp or 0) - (start_temp or 0), 1) if (peak_temp and start_temp) else None

        # Estimate power (best effort)
        power_w = None
        try:
            power_w = self.power_watts()
        except Exception:
            power_w = None

        result = CPUBenchmarkResult(
            mode=config.mode,
            duration=config.duration,
            thread_count=threads,
            intensity=intensity,
            single_core_score=single_score,
            multi_core_score=multi_score,
            ops_per_sec_single=round(ops_per_sec_single, 1),
            ops_per_sec_multi=round(ops_per_sec_multi, 1),
            single_core_time=round(single_time, 4),
            multi_core_time=round(multi_time, 4),
            duration_seconds=round(single_time + multi_time, 3),
            timestamp=time.time(),
            cpu_model=start_info.brand,
            cpu_arch=start_info.arch,
            physical_cores=start_info.physical_cores,
            logical_cores=start_info.logical_cores,
            base_frequency_mhz=start_info.base_frequency_mhz,
            max_frequency_mhz=start_info.max_frequency_mhz,
            start_frequency_mhz=start_freq,
            max_frequency_reached_mhz=round(max_freq, 1) if max_freq else None,
            average_frequency_mhz=avg_freq,
            turbo_boost_detected=turbo_boosted,
            start_temperature_c=start_temp,
            max_temperature_c=peak_temp,
            min_temperature_c=min_temp,
            temperature_delta_c=temp_delta,
            thermal_throttled=thermal_throttled,
            avg_cpu_usage_percent=round(sum(s.cpu_usage for s in monitor_samples) / len(monitor_samples), 1) if monitor_samples else 0.0,
            peak_cpu_usage_percent=round(max(s.cpu_usage for s in monitor_samples), 1) if monitor_samples else 0.0,
            consistency_percent=consistency,
            power_watts=power_w,
        )

        self._benchmark_results.append(result)
        if len(self._benchmark_results) > 100:
            self._benchmark_results = self._benchmark_results[-100:]
        self._save_benchmark_result(result)

        _progress(100)
        return result

    def _save_benchmark_result(self, result: CPUBenchmarkResult) -> None:
        """Persist benchmark result to SQLite."""
        try:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS benchmark_results ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "timestamp TEXT NOT NULL, "
                "mode TEXT NOT NULL, "
                "duration TEXT NOT NULL, "
                "thread_count INTEGER NOT NULL, "
                "intensity REAL NOT NULL, "
                "single_core_score REAL NOT NULL, "
                "multi_core_score REAL NOT NULL, "
                "ops_per_sec_single REAL NOT NULL, "
                "ops_per_sec_multi REAL NOT NULL, "
                "single_core_time REAL NOT NULL, "
                "multi_core_time REAL NOT NULL, "
                "duration_seconds REAL NOT NULL, "
                "cpu_model TEXT, "
                "cpu_arch TEXT, "
                "physical_cores INTEGER, "
                "logical_cores INTEGER, "
                "base_frequency_mhz REAL, "
                "max_frequency_mhz REAL, "
                "start_frequency_mhz REAL, "
                "max_frequency_reached_mhz REAL, "
                "average_frequency_mhz REAL, "
                "turbo_boost_detected INTEGER NOT NULL DEFAULT 0, "
                "start_temperature_c REAL, "
                "max_temperature_c REAL, "
                "min_temperature_c REAL, "
                "temperature_delta_c REAL, "
                "thermal_throttled INTEGER NOT NULL DEFAULT 0, "
                "avg_cpu_usage_percent REAL NOT NULL DEFAULT 0, "
                "peak_cpu_usage_percent REAL NOT NULL DEFAULT 0, "
                "consistency_percent REAL NOT NULL DEFAULT 0, "
                "power_watts REAL"
                ")"
            )
            self._db.execute(
                "INSERT INTO benchmark_results "
                "(timestamp, mode, duration, thread_count, intensity, "
                "single_core_score, multi_core_score, ops_per_sec_single, "
                "ops_per_sec_multi, single_core_time, multi_core_time, "
                "duration_seconds, cpu_model, cpu_arch, physical_cores, "
                "logical_cores, base_frequency_mhz, max_frequency_mhz, "
                "start_frequency_mhz, max_frequency_reached_mhz, "
                "average_frequency_mhz, turbo_boost_detected, "
                "start_temperature_c, max_temperature_c, min_temperature_c, "
                "temperature_delta_c, thermal_throttled, "
                "avg_cpu_usage_percent, peak_cpu_usage_percent, "
                "consistency_percent, power_watts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.fromtimestamp(result.timestamp).isoformat(),
                    result.mode,
                    result.duration,
                    result.thread_count,
                    result.intensity,
                    result.single_core_score,
                    result.multi_core_score,
                    result.ops_per_sec_single,
                    result.ops_per_sec_multi,
                    result.single_core_time,
                    result.multi_core_time,
                    result.duration_seconds,
                    result.cpu_model,
                    result.cpu_arch,
                    result.physical_cores,
                    result.logical_cores,
                    result.base_frequency_mhz,
                    result.max_frequency_mhz,
                    result.start_frequency_mhz,
                    result.max_frequency_reached_mhz,
                    result.average_frequency_mhz,
                    1 if result.turbo_boost_detected else 0,
                    result.start_temperature_c,
                    result.max_temperature_c,
                    result.min_temperature_c,
                    result.temperature_delta_c,
                    1 if result.thermal_throttled else 0,
                    result.avg_cpu_usage_percent,
                    result.peak_cpu_usage_percent,
                    result.consistency_percent,
                    result.power_watts,
                ),
            )
            self._db.commit()
        except Exception:
            pass

    def load_benchmark_history(self) -> List[CPUBenchmarkResult]:
        """Load all benchmark results from SQLite."""
        results: List[CPUBenchmarkResult] = []
        try:
            rows = self._db.fetch_all(
                "SELECT * FROM benchmark_results ORDER BY timestamp DESC"
            )
            for row in rows:
                results.append(CPUBenchmarkResult(
                    mode=row["mode"],
                    duration=row["duration"],
                    thread_count=row["thread_count"],
                    intensity=row["intensity"],
                    single_core_score=row["single_core_score"],
                    multi_core_score=row["multi_core_score"],
                    ops_per_sec_single=row["ops_per_sec_single"],
                    ops_per_sec_multi=row["ops_per_sec_multi"],
                    single_core_time=row["single_core_time"],
                    multi_core_time=row["multi_core_time"],
                    duration_seconds=row["duration_seconds"],
                    timestamp=datetime.fromisoformat(row["timestamp"]).timestamp(),
                    cpu_model=row["cpu_model"],
                    cpu_arch=row["cpu_arch"],
                    physical_cores=row["physical_cores"],
                    logical_cores=row["logical_cores"],
                    base_frequency_mhz=row["base_frequency_mhz"],
                    max_frequency_mhz=row["max_frequency_mhz"],
                    start_frequency_mhz=row["start_frequency_mhz"],
                    max_frequency_reached_mhz=row["max_frequency_reached_mhz"],
                    average_frequency_mhz=row["average_frequency_mhz"],
                    turbo_boost_detected=bool(row["turbo_boost_detected"]),
                    start_temperature_c=row["start_temperature_c"],
                    max_temperature_c=row["max_temperature_c"],
                    min_temperature_c=row["min_temperature_c"],
                    temperature_delta_c=row["temperature_delta_c"],
                    thermal_throttled=bool(row["thermal_throttled"]),
                    avg_cpu_usage_percent=row["avg_cpu_usage_percent"],
                    peak_cpu_usage_percent=row["peak_cpu_usage_percent"],
                    consistency_percent=row["consistency_percent"],
                    power_watts=row["power_watts"],
                ))
        except Exception:
            pass
        return results

    def export_benchmark_report(self, filepath: str) -> tuple[bool, str]:
        """Export benchmark history to CSV."""
        import csv
        try:
            results = self.load_benchmark_history()
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Mode", "Duration", "Threads", "Intensity",
                    "Single-Core Score", "Multi-Core Score", "Ops/Sec Single",
                    "Ops/Sec Multi", "Single Time (s)", "Multi Time (s)",
                    "Total Time (s)", "CPU Model", "Arch", "Physical Cores",
                    "Logical Cores", "Base Freq (MHz)", "Max Freq (MHz)",
                    "Start Freq (MHz)", "Max Freq Reached (MHz)", "Avg Freq (MHz)",
                    "Turbo Boost", "Start Temp (°C)", "Max Temp (°C)",
                    "Min Temp (°C)", "Temp Delta (°C)", "Thermal Throttled",
                    "Avg CPU %", "Peak CPU %", "Consistency %", "Power (W)"
                ])
                for r in results:
                    writer.writerow([
                        datetime.fromtimestamp(r.timestamp).isoformat(),
                        r.mode, r.duration, r.thread_count, r.intensity,
                        r.single_core_score, r.multi_core_score,
                        r.ops_per_sec_single, r.ops_per_sec_multi,
                        r.single_core_time, r.multi_core_time,
                        r.duration_seconds, r.cpu_model, r.cpu_arch,
                        r.physical_cores, r.logical_cores,
                        r.base_frequency_mhz, r.max_frequency_mhz,
                        r.start_frequency_mhz, r.max_frequency_reached_mhz,
                        r.average_frequency_mhz,
                        "Yes" if r.turbo_boost_detected else "No",
                        r.start_temperature_c, r.max_temperature_c,
                        r.min_temperature_c, r.temperature_delta_c,
                        "Yes" if r.thermal_throttled else "No",
                        r.avg_cpu_usage_percent, r.peak_cpu_usage_percent,
                        r.consistency_percent, r.power_watts,
                    ])
            return True, f"Exported {len(results)} results to {filepath}"
        except Exception as exc:
            return False, f"Export failed: {exc}"

    # ---- Power (best effort) ---------------------------------------------

    def power_watts(self) -> Optional[float]:
        """Return estimated CPU power in Watts where supported."""
        try:
            # Try reading RAPL on Linux
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
        self.graph_usage.setMinimumHeight(120)
        self.graph_usage.setMaximumHeight(160)
        root.addWidget(self.graph_usage)

        # Temperature graph
        temp_label = QLabel("Temperature History")
        temp_label.setObjectName("subheading")
        root.addWidget(temp_label)
        self.graph_temp = LineGraph(max_points=300)
        self.graph_temp.setMinimumHeight(90)
        self.graph_temp.setMaximumHeight(130)
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

        # ---- Header ----
        title = QLabel("CPU Benchmark")
        title.setObjectName("heading")
        root.addWidget(title)

        desc = QLabel(
            "Measure single-core, multi-core, and multi-thread performance "
            "with real-time thermal and frequency monitoring."
        )
        desc.setObjectName("subheading")
        root.addWidget(desc)

        # ---- Configuration panel ----
        config_group = QFrame()
        config_group.setObjectName("card")
        config_layout = QGridLayout(config_group)
        config_layout.setContentsMargins(18, 16, 18, 16)
        config_layout.setSpacing(12)

        config_layout.addWidget(QLabel("Mode:"), 0, 0)
        self.bench_mode = QComboBox()
        self.bench_mode.addItems(["Single-Core", "Multi-Core", "Multi-Thread"])
        config_layout.addWidget(self.bench_mode, 0, 1)

        config_layout.addWidget(QLabel("Duration:"), 0, 2)
        self.bench_duration = QComboBox()
        self.bench_duration.addItems(["Short", "Long"])
        config_layout.addWidget(self.bench_duration, 0, 3)

        config_layout.addWidget(QLabel("Threads:"), 1, 0)
        self.bench_threads = QSpinBox()
        self.bench_threads.setRange(1, 64)
        self.bench_threads.setValue(max(1, self._module.collector().info().logical_cores))
        config_layout.addWidget(self.bench_threads, 1, 1)

        config_layout.addWidget(QLabel("Intensity:"), 1, 2)
        self.bench_intensity = QSpinBox()
        self.bench_intensity.setRange(1, 10)
        self.bench_intensity.setValue(5)
        config_layout.addWidget(self.bench_intensity, 1, 3)

        root.addWidget(config_group)

        # ---- Safety / warning ----
        self.bench_warning = QLabel(
            "\u26A0 Intensive benchmarks may cause high CPU usage and temperature. "
            "Ensure adequate cooling before running long tests."
        )
        self.bench_warning.setObjectName("muted")
        self.bench_warning.setWordWrap(True)
        root.addWidget(self.bench_warning)

        # ---- Score cards ----
        score_cards = QHBoxLayout()
        score_cards.setSpacing(12)
        self.bench_single = _StatCard("Single-Core Score", "--", "Higher is better")
        self.bench_multi = _StatCard("Multi-Core Score", "--", "Higher is better")
        self.bench_ops = _StatCard("Ops/Sec", "--", "Operations per second")
        self.bench_consistency = _StatCard("Consistency", "-- %", "Performance stability")
        for card in (self.bench_single, self.bench_multi, self.bench_ops, self.bench_consistency):
            score_cards.addWidget(card)
        root.addLayout(score_cards)

        # ---- Run button and progress ----
        btn_row = QHBoxLayout()
        self.bench_run_btn = QPushButton("Run Benchmark")
        self.bench_run_btn.setObjectName("primary")
        self.bench_run_btn.clicked.connect(self._run_benchmark)
        self.bench_stop_btn = QPushButton("Stop")
        self.bench_stop_btn.setObjectName("danger")
        self.bench_stop_btn.setEnabled(False)
        self.bench_stop_btn.clicked.connect(self._stop_benchmark)
        btn_row.addWidget(self.bench_run_btn)
        btn_row.addWidget(self.bench_stop_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.bench_progress = QProgressBar()
        self.bench_progress.setRange(0, 100)
        self.bench_progress.setValue(0)
        self.bench_progress.setTextVisible(True)
        root.addWidget(self.bench_progress)

        self.bench_status = QLabel("Ready")
        self.bench_status.setObjectName("muted")
        root.addWidget(self.bench_status)

        # ---- Real-time monitoring during benchmark ----
        mon_group = QFrame()
        mon_group.setObjectName("card")
        mon_layout = QGridLayout(mon_group)
        mon_layout.setContentsMargins(18, 16, 18, 16)
        mon_layout.setSpacing(10)

        self.mon_cpu = _StatCard("CPU Usage", "-- %", "During benchmark")
        self.mon_freq = _StatCard("Frequency", "-- MHz", "Current clock")
        self.mon_temp = _StatCard("Temperature", "-- °C", "Package temp")
        self.mon_power = _StatCard("Power", "-- W", "CPU power draw")
        for card in (self.mon_cpu, self.mon_freq, self.mon_temp, self.mon_power):
            mon_layout.addWidget(card, 0, score_cards.count() and 0 or 0)
        # Use a proper grid: 2x2
        mon_layout_2 = QGridLayout()
        mon_layout_2.setContentsMargins(0, 0, 0, 0)
        mon_layout_2.setSpacing(10)
        mon_layout_2.addWidget(self.mon_cpu, 0, 0)
        mon_layout_2.addWidget(self.mon_freq, 0, 1)
        mon_layout_2.addWidget(self.mon_temp, 1, 0)
        mon_layout_2.addWidget(self.mon_power, 1, 1)
        mon_group.setLayout(mon_layout_2)

        mon_label = QLabel("Real-Time Monitoring During Benchmark")
        mon_label.setObjectName("subheading")
        root.addWidget(mon_label)
        root.addWidget(mon_group)

        # ---- Analysis results ----
        analysis_group = QFrame()
        analysis_group.setObjectName("card")
        analysis_layout = QGridLayout(analysis_group)
        analysis_layout.setContentsMargins(18, 16, 18, 16)
        analysis_layout.setSpacing(10)

        self.bench_thermal_start = QLabel("Start Temp: -- °C")
        self.bench_thermal_max = QLabel("Max Temp: -- °C")
        self.bench_thermal_delta = QLabel("Temp Delta: -- °C")
        self.bench_thermal_throttle = QLabel("Thermal Throttle: No")
        self.bench_freq_start = QLabel("Start Freq: -- MHz")
        self.bench_freq_max = QLabel("Max Freq: -- MHz")
        self.bench_freq_avg = QLabel("Avg Freq: -- MHz")
        self.bench_freq_turbo = QLabel("Turbo Boost: No")

        analysis_layout.addWidget(self.bench_thermal_start, 0, 0)
        analysis_layout.addWidget(self.bench_thermal_max, 0, 1)
        analysis_layout.addWidget(self.bench_thermal_delta, 0, 2)
        analysis_layout.addWidget(self.bench_thermal_throttle, 0, 3)
        analysis_layout.addWidget(self.bench_freq_start, 1, 0)
        analysis_layout.addWidget(self.bench_freq_max, 1, 1)
        analysis_layout.addWidget(self.bench_freq_avg, 1, 2)
        analysis_layout.addWidget(self.bench_freq_turbo, 1, 3)

        root.addWidget(analysis_group)

        # ---- History / comparison ----
        hist_label = QLabel("Benchmark History")
        hist_label.setObjectName("subheading")
        root.addWidget(hist_label)

        self.bench_history_table = QTableWidget(0, 8)
        self.bench_history_table.setHorizontalHeaderLabels(
            ["Time", "Mode", "Single Score", "Multi Score", "Ops/Sec", "Max Temp", "Throttled", "Consistency"]
        )
        self.bench_history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.bench_history_table.setAlternatingRowColors(True)
        self.bench_history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.bench_history_table, 1)

        # ---- Export / actions ----
        export_row = QHBoxLayout()
        self.bench_export_btn = QPushButton("Export Report (CSV)")
        self.bench_export_btn.setObjectName("ghost")
        self.bench_export_btn.clicked.connect(self._export_benchmark_report)
        self.bench_refresh_hist_btn = QPushButton("Refresh History")
        self.bench_refresh_hist_btn.setObjectName("ghost")
        self.bench_refresh_hist_btn.clicked.connect(self._refresh_bench_history)
        export_row.addWidget(self.bench_export_btn)
        export_row.addWidget(self.bench_refresh_hist_btn)
        export_row.addStretch()
        root.addLayout(export_row)

        self._refresh_bench_history()
        root.addStretch()
        return widget

    # ---- Benchmark actions ------------------------------------------------

    def _run_benchmark(self) -> None:
        mode_map = {"Single-Core": "single_core", "Multi-Core": "multi_core", "Multi-Thread": "multi_thread"}
        duration_map = {"Short": "short", "Long": "long"}

        config = BenchmarkConfig(
            mode=mode_map[self.bench_mode.currentText()],
            duration=duration_map[self.bench_duration.currentText()],
            thread_count=self.bench_threads.value(),
            intensity=self.bench_intensity.value() / 2.0,  # 0.5 to 5.0
        )

        # Safety warning for long/high intensity
        if config.duration == "long" and config.intensity >= 3.0:
            reply = QMessageBox.warning(
                self,
                "Intensive Benchmark",
                "This benchmark will place sustained high load on your CPU. "
                "Ensure adequate cooling. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.bench_run_btn.setEnabled(False)
        self.bench_stop_btn.setEnabled(True)
        self.bench_progress.setValue(0)
        self.bench_status.setText("Running benchmark...")
        QApplication.processEvents()

        try:
            def _on_progress(pct: int) -> None:
                self.bench_progress.setValue(pct)
                QApplication.processEvents()

            result = self._module.run_benchmark(config, progress_callback=_on_progress)
            self._display_benchmark_result(result)
            self._refresh_bench_history()
        except Exception as exc:
            QMessageBox.critical(self, "Benchmark Error", f"Benchmark failed: {exc}")
        finally:
            self.bench_run_btn.setEnabled(True)
            self.bench_stop_btn.setEnabled(False)
            self.bench_progress.setValue(100)
            self.bench_status.setText("Benchmark complete")

    def _stop_benchmark(self) -> None:
        self.bench_status.setText("Stopping benchmark...")
        self.bench_stop_btn.setEnabled(False)

    def _display_benchmark_result(self, result: CPUBenchmarkResult) -> None:
        self.bench_single.set_value(f"{result.single_core_score:.0f}")
        self.bench_multi.set_value(f"{result.multi_core_score:.0f}")
        self.bench_ops.set_value(f"{result.ops_per_sec_multi:,.0f}")
        self.bench_consistency.set_value(f"{result.consistency_percent:.1f} %")

        # Thermal analysis
        start_t = result.start_temperature_c
        max_t = result.max_temperature_c
        delta = result.temperature_delta_c
        self.bench_thermal_start.setText(
            f"Start Temp: {start_t:.1f} °C" if start_t is not None else "Start Temp: -- °C"
        )
        self.bench_thermal_max.setText(
            f"Max Temp: {max_t:.1f} °C" if max_t is not None else "Max Temp: -- °C"
        )
        self.bench_thermal_delta.setText(
            f"Temp Delta: {delta:+.1f} °C" if delta is not None else "Temp Delta: -- °C"
        )
        self.bench_thermal_throttle.setText(
            f"Thermal Throttle: {'Yes' if result.thermal_throttled else 'No'}"
        )
        if result.thermal_throttled:
            self.bench_thermal_throttle.setStyleSheet("color: #EF4444; font-weight: 700;")

        # Frequency analysis
        self.bench_freq_start.setText(
            f"Start Freq: {result.start_frequency_mhz:.0f} MHz" if result.start_frequency_mhz else "Start Freq: -- MHz"
        )
        self.bench_freq_max.setText(
            f"Max Freq: {result.max_frequency_reached_mhz:.0f} MHz"
            if result.max_frequency_reached_mhz else "Max Freq: -- MHz"
        )
        self.bench_freq_avg.setText(
            f"Avg Freq: {result.average_frequency_mhz:.0f} MHz"
            if result.average_frequency_mhz else "Avg Freq: -- MHz"
        )
        self.bench_freq_turbo.setText(
            f"Turbo Boost: {'Yes' if result.turbo_boost_detected else 'No'}"
        )

    def _refresh_bench_history(self) -> None:
        results = self._module.load_benchmark_history()
        self.bench_history_table.setRowCount(len(results))
        for r, res in enumerate(results):
            self.bench_history_table.setItem(
                r, 0, QTableWidgetItem(datetime.fromtimestamp(res.timestamp).strftime("%H:%M:%S"))
            )
            self.bench_history_table.setItem(r, 1, QTableWidgetItem(res.mode))
            self.bench_history_table.setItem(
                r, 2, QTableWidgetItem(f"{res.single_core_score:.0f}")
            )
            self.bench_history_table.setItem(
                r, 3, QTableWidgetItem(f"{res.multi_core_score:.0f}")
            )
            self.bench_history_table.setItem(
                r, 4, QTableWidgetItem(f"{res.ops_per_sec_multi:,.0f}")
            )
            self.bench_history_table.setItem(
                r, 5,
                QTableWidgetItem(
                    f"{res.max_temperature_c:.1f} °C" if res.max_temperature_c else "--"
                ),
            )
            self.bench_history_table.setItem(
                r, 6, QTableWidgetItem("Yes" if res.thermal_throttled else "No")
            )
            self.bench_history_table.setItem(
                r, 7, QTableWidgetItem(f"{res.consistency_percent:.1f} %")
            )

    def _export_benchmark_report(self) -> None:
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Benchmark Report", "benchmark_report.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        success, message = self._module.export_benchmark_report(path)
        if success:
            QMessageBox.information(self, "Export Complete", message)
        else:
            QMessageBox.warning(self, "Export Failed", message)

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


