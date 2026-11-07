"""Dashboard landing page with placeholder summary cards."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


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
        value_lbl.setStyleSheet("font-size: 30px; font-weight: 800;")

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("muted")
        sub_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)

        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(value_lbl)
        layout.addWidget(sub_lbl)


class Dashboard(QWidget):
    """Overview page: grid of summary cards. Phase 1 shows placeholders."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(16)
        grid.setContentsMargins(24, 24, 24, 24)

        cards = [
            ("CPU", "-- %", "No data", "Processor usage"),
            ("Memory", "-- %", "No data", "RAM usage"),
            ("Storage", "-- %", "No data", "Disk usage"),
            ("Network", "-- KB/s", "No data", "Upload / download"),
        ]

        for i, (title, value, subtitle, _) in enumerate(cards):
            card = _StatCard(title, value, subtitle)
            grid.addWidget(card, 0, i)

        grid.setColumnStretch(len(cards), 1)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 8)
        heading = QLabel("Dashboard")
        heading.setObjectName("heading")
        sub = QLabel("System overview — live metrics appear once modules are added.")
        sub.setObjectName("subheading")
        header_layout.addWidget(heading)
        header_layout.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(header)
        root.addWidget(scroll)
        scroll.setWidget(container)
