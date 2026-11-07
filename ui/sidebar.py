""" Vetical navigation rail that switches pages.    """

from typing import List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import(
    QAbstractItemView,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)



class _NavItem(QFrame):
    """Single Nav entry: icon + label, selectable"""

    def __init__(self, page_id: str, icon: str, parent = None) -> None:
        super().__init__(parent)
        self.page_id = page_id
        self.setObjectName("navItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)

        layout = QVBoxLayout(self)
        layout.setConetntMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        row = QLabel(f"{icon} {label}")
        row.setObjectName("navlabel")
        row.setAlignment(QtAlignVCentre | QtAlignLeft)
        layout.addWidget(row)

    def set_active(self, active: bool) -> None:
        self.setPreperty("active", "true" if acive else false)
        self.style().unpolish(self)
        self.style().polish(slef)

class Sidebar(QListWidget):
    """Sidebar Navigation. EMits page_selcted (page_id)."""

    page_selected = pyqtSignal(str)
    def __init__(self, entries: List[tuple], pare=None) ->None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setViewMode("QListWidget.ListMode")
        self.setMovement(QListWidget.static)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBArPolicy(Qt.ScrollBarAlwaysoff)

        self._widgets: dict = {}
        for page_id, label, icon in entries:
            self._add_item(page_id, label, icon)

        self.currentItemChanged.connect(self._on_current_changed)

    def set_active_page(self, page_id: str) -> None:
        for pid, (item,widget) in self._widgets.items():
            widget.set_active(pid == page_id)
        if pid == page_id:
            self.setCurrentItem(item)

    def _on_current_changes(self, current, previous) -> None:
        if current is None:
            return
        page_id = current.data(Qt.ItemDataRole.UserRole)
        self.page_selected.emit(page_id)


                
                         
                     
