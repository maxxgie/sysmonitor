"""SQLite connection, schema creation, migrations and simple query helpers."""

import os
import sqlite3
from typing import Any, Iterable, Optional

from PyQt5.QtCore import QStandardPaths

SCHEMA_VERSION = 1


def _app_data_dir() -> str:
    locations = QStandardPaths.standardLocations(QStandardPaths.AppDataLocation)
    if locations:
        dir_path = locations[0]
    else:
        dir_path = os.path.join(os.path.expanduser("~"), ".systemmonitor")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


class Database:
    """Thin wrapper around a single SQLite file in the app-data folder."""

    def __init__(self, db_name: str = "systemmonitor.db") -> None:
        self.db_path = os.path.join(_app_data_dir(), db_name)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def _initialize(self) -> None:
        self.execute(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "version INTEGER PRIMARY KEY"
            ")"
        )
        row = self.fetch_one("SELECT version FROM schema_version")
        current = row["version"] if row else 0
        self._migrate(current)

    def _migrate(self, current: int) -> None:
        if current < 1:
            self.execute(
                "CREATE TABLE IF NOT EXISTS settings ("
                "key TEXT PRIMARY KEY, "
                "value TEXT NOT NULL, "
                "updated_at TEXT NOT NULL DEFAULT (datetime('now'))"
                ")"
            )
            self.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                (1,),
            )
        self._conn.commit()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, tuple(params))

    def fetch_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        cur = self.execute(sql, params)
        return cur.fetchone()

    def fetch_all(self, sql: str, params: Iterable[Any] = ()) -> list:
        cur = self.execute(sql, params)
        return cur.fetchall()

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
