"""Professional vertical navigation rail that switches pages."""

from typing import List, Optional

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class _NavItem(QFrame):
    """Single nav entry: icon + label with active/hover states."""

    def __init__(self, page_id: str, label: str, icon: str, parent=None) -> None:
        super().__init__(parent)
        self.page_id = page_id
        self._active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(52)
        self.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 0, 20, 0)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self._icon = QLabel(icon)
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setFixedSize(20, 20)
        self._icon.setStyleSheet("font-size: 16px;")

        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._label.setStyleSheet("font-size: 13px; font-weight: 600;")

        root.addWidget(self._icon)
        root.addWidget(self._label)
        root.addStretch()

        self.setObjectName("navItem")
        self._apply_style()

    def set_active(self, active: bool) -> None:
        if self._active == active:
            return
        self._active = active
        self._apply_style()

    def _apply_style(self) -> None:
        self.setProperty("active", "true" if self._active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        if self._active:
            self._label.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #1D4ED8;"
            )
            self._icon.setStyleSheet("font-size: 16px; color: #1D4ED8;")
        else:
            self._label.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #64748B;"
            )
            self._icon.setStyleSheet("font-size: 16px; color: #94A3B8;")


class Sidebar(QWidget):
    """Professional sidebar navigation rail. Emits page_selected(page_id)."""

    page_selected = pyqtSignal(str)

    def __init__(self, entries: List[tuple], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------- App header ----------
        header = QFrame()
        header.setObjectName("sidebarHeader")
        header.setFixedHeight(72)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)

        app_icon = QLabel("\u2600")
        app_icon.setStyleSheet("font-size: 24px;")
        app_title = QLabel("System Monitor")
        app_title.setObjectName("sidebarTitle")
        app_title.setStyleSheet("font-size: 16px; font-weight: 800;")
        app_sub = QLabel("Blue & White")
        app_sub.setObjectName("sidebarSubtitle")
        app_sub.setStyleSheet("font-size: 11px; font-weight: 500;")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(app_title)
        title_col.addWidget(app_sub)

        header_layout.addWidget(app_icon)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        root.addWidget(header)

        # ---------- Divider ----------
        div = QFrame()
        div.setObjectName("sidebarDivider")
        div.setFixedHeight(1)
        root.addWidget(div)

        # ---------- Nav list ----------
        self._list = QListWidget()
        self._list.setObjectName("sidebarList")
        self._list.setViewMode(QListWidget.ListMode)
        self._list.setMovement(QListWidget.Static)
        self._list.setSelectionMode(QListWidget.NoSelection)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._list.setFrameShape(QFrame.NoFrame)
        self._list.setFocusPolicy(Qt.NoFocus)

        self._items: dict = {}
        for page_id, label, icon in entries:
            self._add_item(page_id, label, icon)

        self._list.currentRowChanged.connect(self._on_row_changed)
        root.addWidget(self._list)

        # ---------- Spacer ----------
        root.addStretch()

        # ---------- Bottom: Settings always visible ----------
        # Settings is already in entries; keep it in the flow.

    def _add_item(self, page_id: str, label: str, icon: str) -> None:
        widget = _NavItem(page_id, label, icon, self)
        item = QListWidgetItem(self._list)
        item.setData(Qt.ItemDataRole.UserRole, page_id)
        item.setSizeHint(QSize(240, 52))
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)
        self._items[page_id] = (item, widget)

    def set_active_page(self, page_id: str) -> None:
        for pid, (item, widget) in self._items.items():
            is_active = pid == page_id
            widget.set_active(is_active)
            if is_active:
                self._list.setCurrentItem(item)

    def _on_row_changed(self, row: int) -> None:
        item = self._list.item(row)
        if item is None:
            return
        page_id = item.data(Qt.ItemDataRole.UserRole)
        self.page_selected.emit(page_id)

    def set_theme_palette(self, palette: dict) -> None:
        """Inject palette-derived colours into child items if needed."""
        # The QSS handles colours; this hook is available for future tweaks.
        pass
