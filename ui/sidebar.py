"""Professional vertical navigation rail that switches pages."""

from typing import List

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QWidget):
    """Professional sidebar navigation rail.

    Uses checkable QPushButton items so Qt handles active/hover/pressed
    states natively via QSS — no custom event juggling needed.
    """

    page_selected = pyqtSignal(str)

    def __init__(self, entries: List[tuple], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(250)
        self.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Expanding
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---------- App header ----------
        header = QFrame()
        header.setObjectName("sidebarHeader")
        header.setFixedHeight(72)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)
        header_layout.setSpacing(12)

        app_icon = QLabel("\u2600")
        app_icon.setObjectName("sidebarIcon")
        app_icon.setStyleSheet("font-size: 22px;")

        app_title = QLabel("System Monitor")
        app_title.setObjectName("sidebarTitle")
        app_title.setStyleSheet("font-size: 15px; font-weight: 800;")

        app_sub = QLabel("Blue & White")
        app_sub.setObjectName("sidebarSubtitle")
        app_sub.setStyleSheet("font-size: 11px; font-weight: 500;")

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(1)
        title_col.addWidget(app_title)
        title_col.addWidget(app_sub)

        header_layout.addWidget(app_icon)
        header_layout.addLayout(title_col, 1)
        root.addWidget(header)

        # ---------- Divider ----------
        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # ---------- Nav items (scrollable) ----------
        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        nav_container = QWidget()
        nav_container.setObjectName("navContainer")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 10, 0, 10)
        nav_layout.setSpacing(4)

        self._buttons: dict = {}
        for page_id, label, icon in entries:
            btn = self._make_button(page_id, label, icon)
            nav_layout.addWidget(btn)
            self._buttons[page_id] = btn

        nav_layout.addStretch()
        scroll.setWidget(nav_container)
        layout.addWidget(scroll)

    def _make_button(self, page_id: str, label: str, icon: str) -> QPushButton:
        btn = QPushButton(f"{icon}   {label}")
        btn.setObjectName("navButton")
        btn.setProperty("pageId", page_id)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(46)
        btn.setLayoutDirection(Qt.LeftToRight)
        btn.setStyleSheet(
            "text-align: left; padding: 10px 18px; font-size: 13px; font-weight: 600;"
        )
        btn.clicked.connect(lambda _checked, pid=page_id: self._on_clicked(pid))
        return btn

    def _on_clicked(self, page_id: str) -> None:
        self.set_active_page(page_id)
        self.page_selected.emit(page_id)

    def set_active_page(self, page_id: str) -> None:
        for pid, btn in self._buttons.items():
            btn.setChecked(pid == page_id)
