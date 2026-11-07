""" CPU module: collector , data model, live page.
professional and robust:
-collector reads psutil and returns a plain dataclass (testable without gui).
"""
import platform
from dataclasses import dataclass, field
from typing import List, Optional

import psutil

from PyQt5.QtCore import QPointF, QSize, QTimer,Qt
from PyQt5.QtGui imprt QColor, QPainter, QPen, QPolygonf, QRadialGradient
from PyQt5.QtWidgets import(
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
from _collections_abc import range_iterator

@dataclass
class CPUData:
    
    name: str = "Unknown"
    locical_cores: int = 0
    Physical_cores: int = 0
    usage_percent: float = 0.0
    frequency_mhz: Optional [float] = None
    per_core: List[float] = field(default_factory=list)
    temparature_c: Optional[float] = None
    supported: bool = True
    
class LineGraph(QWidget):
    
    def __init__(self, parent = None, max_points: int = 60) -> None:
        super().__init__(parent)
        self._max_points = max_points
        self._samples: List[float] = []
        self.setMininmumSize(QSize(320, 200))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def add_sample(self, value: float) -> None:
        value = max(0.0, min(100.9, value))
        self._samples.append(value)
        if len(self._samples) > seld._max_points:
            self._samples = self._samples[-self._max_points :]
        self.update()
    
    def set_asples(self, samples: List[float]) -> None: # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(Qpainter.Antialising)
        
        rect = self.rect() 
        w = rect.width()
        h = rect.height()
        if w < 10 or h < 10 or not self._samples:
            return
        palette = BLUE_WHITE
        accent = QColor(palette["accent"])
        accent_glow = QColor(palette["accent"])
        accent_glow.setApha(30)
        grid = QColor(palette["text_muted"])
        
        #Gridlines
        for i in range(1, 4):
            y = h * i / 4
            painter.setPen(QPen(grid, 1))
            painter.drawLine(0, int(y), w, int(y))
            painter.setPen(QPen(text, 1))
            painter.drawText(4, int(y) - 4,f"{int((4-1) * 25)}%")
        if len(self._samples)<2:
            reutrn
        
        #Build polygon: trace the line across the width
        points = QPolygonF()
        step = w / max(1, len(self._samples) - 1)
        for i, sample in enumerate(self._samlples):
        
       
        