"""Typed read/write access to user preferences, backed by the database."""

import json
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from core.database import Database


class Settings(QObject):
    """Typed preferences store with defaults, persisted in SQLite.

    Emits ``setting_changed`` whenever a value is updated so open pages can
    refresh live.
    """

    setting_changed = pyqtSignal(str, object)

    DEFAULTS: Dict[str, Any] = {
        "theme": "blue_white",
        "refresh_interval_ms": 1000,
        "graph_history_points": 60,
        "start_page": "dashboard",
        "cpu_alert_threshold": 90,
        "ram_alert_threshold": 90,
        "window_geometry": "",
    }

    def __init__(self, database: Database) -> None:
        super().__init__()
        self._db = database
        self._cache: Dict[str, Any] = {}
        self._load_defaults()
        self._load_from_db()

    def _load_defaults(self) -> None:
        self._cache = dict(self.DEFAULTS)

    def _load_from_db(self) -> None:
        rows = self._db.fetch_all("SELECT key, value FROM settings")
        for row in rows:
            self._cache[row["key"]] = self._decode(row["value"])

    def _decode(self, value: str) -> Any:
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    def _encode(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._cache:
            return self._cache[key]
        return default

    def set(self, key: str, value: Any) -> None:
        encoded = self._encode(value)
        self._cache[key] = value
        self._db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (key, encoded),
        )
        self._db.commit()
        self.setting_changed.emit(key, value)

    def all(self) -> Dict[str, Any]:
        return dict(self._cache)