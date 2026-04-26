from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_DB = Path.home() / ".config" / "cyberdeck" / "cache.db"


@dataclass
class CacheEntry:
    payload: Any
    fetched_at: float = field(default_factory=time.time)


class Cache:
    def __init__(self, db_path: Path = DEFAULT_DB) -> None:
        self._db_path = db_path
        self._mem: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache(
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    fetched_at REAL NOT NULL
                )
                """
            )

    def get(self, key: str) -> Any | None:
        entry = self.get_entry(key)
        return entry.payload if entry else None

    def get_entry(self, key: str) -> CacheEntry | None:
        with self._lock:
            return self._mem.get(key)

    def set(self, key: str, payload: Any) -> bool:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        with self._lock:
            current = self._mem.get(key)
            if current is not None:
                current_serialized = json.dumps(
                    current.payload, sort_keys=True, default=str
                )
                if current_serialized == serialized:
                    return False

            fetched_at = time.time()
            self._mem[key] = CacheEntry(payload=payload, fetched_at=fetched_at)
            self._persist(key, serialized, fetched_at)
            return True

    def _persist(self, key: str, serialized: str, fetched_at: float) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO cache(key, payload, fetched_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    payload = excluded.payload,
                    fetched_at = excluded.fetched_at
                """,
                (key, serialized, fetched_at),
            )

    def load_from_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute("SELECT key, payload, fetched_at FROM cache").fetchall()

        loaded: dict[str, CacheEntry] = {}
        for key, payload_json, fetched_at in rows:
            loaded[key] = CacheEntry(payload=json.loads(payload_json), fetched_at=fetched_at)

        with self._lock:
            self._mem = loaded
