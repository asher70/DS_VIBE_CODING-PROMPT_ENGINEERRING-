"""SQLite storage for WeatherVision Pro.

SQLite is a small database engine built into Python. It stores everything in
one local `.sqlite3` file, so the app can remember searches, settings, cached
API replies, and exported reports without needing a server.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import DATABASE_PATH, ensure_app_folders


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"


def utc_now() -> datetime:
    """Return the current UTC time without timezone complexity."""

    return datetime.utcnow()


class WeatherDatabase:
    """Small wrapper around SQLite so the rest of the app uses simple methods."""

    def __init__(self, db_path: Path = DATABASE_PATH) -> None:
        ensure_app_folders()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        """Create tables if this is the first time the app is launched."""

        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    country TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timezone TEXT,
                    searched_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS export_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    export_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    city TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            connection.commit()

    def save_search(
        self,
        city: str,
        country: str | None,
        latitude: float,
        longitude: float,
        timezone: str | None,
    ) -> None:
        """Save a successful search to the history list."""

        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO search_history
                    (city, country, latitude, longitude, timezone, searched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    city,
                    country,
                    latitude,
                    longitude,
                    timezone,
                    utc_now().strftime(ISO_FORMAT),
                ),
            )
            connection.commit()

    def recent_searches(self, limit: int = 8) -> list[dict[str, Any]]:
        """Return the newest unique city searches."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT city, country, latitude, longitude, timezone, MAX(searched_at) AS searched_at
                FROM search_history
                GROUP BY city, country, latitude, longitude, timezone
                ORDER BY searched_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_cached_response(
        self,
        cache_key: str,
        endpoint: str,
        response: dict[str, Any],
        ttl_minutes: int,
    ) -> None:
        """Store one API response until its expiry time."""

        created_at = utc_now()
        expires_at = created_at + timedelta(minutes=ttl_minutes)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO api_cache
                    (cache_key, endpoint, response_json, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    endpoint = excluded.endpoint,
                    response_json = excluded.response_json,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (
                    cache_key,
                    endpoint,
                    json.dumps(response),
                    created_at.strftime(ISO_FORMAT),
                    expires_at.strftime(ISO_FORMAT),
                ),
            )
            connection.commit()

    def get_cached_response(
        self,
        cache_key: str,
        allow_expired: bool = False,
    ) -> dict[str, Any] | None:
        """Return cached JSON if it exists and is still valid.

        When the internet is down, callers may set `allow_expired=True` so the
        app can still show the last known real Open-Meteo data.
        """

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT response_json, expires_at
                FROM api_cache
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()

        if row is None:
            return None

        expires_at = datetime.strptime(row["expires_at"], ISO_FORMAT)
        if not allow_expired and expires_at < utc_now():
            return None

        try:
            return json.loads(row["response_json"])
        except json.JSONDecodeError:
            return None

    def set_setting(self, key: str, value: Any) -> None:
        """Save a user preference such as theme or refresh interval."""

        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO user_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(value), utc_now().strftime(ISO_FORMAT)),
            )
            connection.commit()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Read one user preference."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT value FROM user_settings WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return default

    def log_export(self, export_type: str, file_path: str, city: str | None) -> None:
        """Remember a file the user exported."""

        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO export_history (export_type, file_path, city, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (export_type, file_path, city, utc_now().strftime(ISO_FORMAT)),
            )
            connection.commit()

    def export_history(self, limit: int = 15) -> list[dict[str, Any]]:
        """Return recent exported files for the Exports screen."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT export_type, file_path, city, created_at
                FROM export_history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_cache(self) -> int:
        """Delete cached API responses and return how many rows were removed."""

        with closing(self._connect()) as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM api_cache").fetchone()
            total = int(row["total"]) if row else 0
            connection.execute("DELETE FROM api_cache")
            connection.commit()
        return total
