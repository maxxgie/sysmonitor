"""Settings page: theme, refresh interval, history points.

Theme changes are applied live via the Settings.setting_changed signal,
so no restart is required.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.settings import Settings


class SettingsPage(QWidget):
    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._settings.setting_changed.connect(self._on_setting_changed)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(18)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Blue & White", "Dark"])
        self.theme_combo.setCurrentIndex(
            0 if settings.get("theme") == "blue_white" else 1
        )
        self.theme_combo.currentTextChanged.connect(self._on_theme_combo)

        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(500, 60000)
        self.refresh_spin.setSingleStep(100)
        self.refresh_spin.setSuffix(" ms")
        self.refresh_spin.setValue(int(settings.get("refresh_interval_ms", 1000)))
        self.refresh_spin.valueChanged.connect(
            lambda v: settings.set("refresh_interval_ms", int(v))
        )

        self.history_spin = QSpinBox()
        self.history_spin.setRange(10, 600)
        self.history_spin.setSuffix(" points")
        self.history_spin.setValue(int(settings.get("graph_history_points", 60)))
        self.history_spin.valueChanged.connect(
            lambda v: settings.set("graph_history_points", int(v))
        )

        form.addRow("Theme", self.theme_combo)
        form.addRow("Refresh interval", self.refresh_spin)
        form.addRow("Graph history", self.history_spin)

        container = QWidget()
        container.setLayout(form)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(0)
        heading = QLabel("Settings")
        heading.setObjectName("heading")
        sub = QLabel("Preferences save automatically and apply immediately.")
        sub.setObjectName("subheading")
        root.addWidget(heading)
        root.addWidget(sub)
        root.addSpacing(20)
        root.addWidget(scroll)
        scroll.setWidget(container)

    def _on_theme_combo(self, text: str) -> None:
        theme = "blue_white" if text == "Blue & White" else "dark"
        self._settings.set("theme", theme)

    def _on_setting_changed(self, key: str, value) -> None:
        if key == "theme":
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(
                0 if value == "blue_white" else 1
            )
            self.theme_combo.blockSignals(False)
