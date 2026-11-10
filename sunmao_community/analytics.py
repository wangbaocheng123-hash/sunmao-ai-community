from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


ANALYTICS_RETENTION_DAYS = 365
VALID_ANALYTICS_VIEWS = frozenset({"exchange", "sizes", "joints"})
BEIJING_TIME = ZoneInfo("Asia/Shanghai")


def classify_device(user_agent: Any) -> str:
    value = str(user_agent or "").lower()
    if any(marker in value for marker in ("bot", "spider", "crawler", "slurp")):
        return "bot"
    if any(marker in value for marker in ("ipad", "tablet", "kindle")):
        return "tablet"
    if any(marker in value for marker in ("mobile", "iphone", "android")):
        return "mobile"
    return "desktop"


def normalize_referrer(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "direct"
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return "direct"
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "direct"
    host = parsed.hostname.rstrip(".").lower()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return "direct"
    return host[:160] or "direct"


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


class CommunityAnalyticsStore:
    """Privacy-minded first-party analytics stored beside community data."""

    def __init__(
        self,
        database_path: Path,
        *,
        retention_days: int = ANALYTICS_RETENTION_DAYS,
    ) -> None:
        self.database_path = Path(database_path).expanduser().resolve()
        self.retention_days = max(30, int(retention_days))
        self._write_lock = threading.Lock()
        self._last_purge_epoch = 0
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS analytics_totals (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    visitors INTEGER NOT NULL DEFAULT 0,
                    visits INTEGER NOT NULL DEFAULT 0,
                    pageviews INTEGER NOT NULL DEFAULT 0,
                    first_event_at TEXT NOT NULL DEFAULT '',
                    last_event_at TEXT NOT NULL DEFAULT ''
                );
                INSERT OR IGNORE INTO analytics_totals (id) VALUES (1);

                CREATE TABLE IF NOT EXISTS analytics_visitors (
                    visitor_hash TEXT PRIMARY KEY,
                    visitor_label TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    first_seen_epoch INTEGER NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    last_seen_epoch INTEGER NOT NULL,
                    visits INTEGER NOT NULL DEFAULT 0,
                    pageviews INTEGER NOT NULL DEFAULT 0,
                    last_view TEXT NOT NULL,
                    referrer_host TEXT NOT NULL,
                    device_type TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS analytics_visitors_last_seen
                ON analytics_visitors (last_seen_epoch DESC);

                CREATE TABLE IF NOT EXISTS analytics_sessions (
                    session_hash TEXT PRIMARY KEY,
                    visitor_hash TEXT NOT NULL,
                    started_at_epoch INTEGER NOT NULL,
                    last_seen_epoch INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS analytics_sessions_last_seen
                ON analytics_sessions (last_seen_epoch);

                CREATE TABLE IF NOT EXISTS analytics_daily (
                    day TEXT PRIMARY KEY,
                    visits INTEGER NOT NULL DEFAULT 0,
                    pageviews INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS analytics_daily_visitors (
                    day TEXT NOT NULL,
                    visitor_hash TEXT NOT NULL,
                    PRIMARY KEY (day, visitor_hash)
                );
                CREATE TABLE IF NOT EXISTS analytics_daily_pages (
                    day TEXT NOT NULL,
                    view TEXT NOT NULL,
                    pageviews INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (day, view)
                );
                CREATE TABLE IF NOT EXISTS analytics_daily_sources (
                    day TEXT NOT NULL,
                    source TEXT NOT NULL,
                    visits INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (day, source)
                );
                CREATE TABLE IF NOT EXISTS analytics_daily_devices (
                    day TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    visits INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (day, device_type)
                );
                CREATE TABLE IF NOT EXISTS analytics_owner_aliases (
                    visitor_hash TEXT PRIMARY KEY,
                    visitors INTEGER NOT NULL DEFAULT 0,
                    visits INTEGER NOT NULL DEFAULT 0,
                    pageviews INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS analytics_browser_daily (
                    day TEXT NOT NULL,
                    visitor_hash TEXT NOT NULL,
                    view TEXT NOT NULL,
                    source TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    visits INTEGER NOT NULL DEFAULT 0,
                    pageviews INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (day, visitor_hash, view, source, device_type)
                );
                CREATE TABLE IF NOT EXISTS analytics_identity_metadata (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    started_at TEXT NOT NULL,
                    legacy_data INTEGER NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO analytics_identity_metadata VALUES (1, ?, "
                "(SELECT CASE WHEN pageviews > 0 THEN 1 ELSE 0 END FROM analytics_totals WHERE id = 1))",
                (datetime.now(UTC).isoformat(),),
            )
            current_epoch = int(time.time())
            self._purge_expired(connection, current_epoch)
            self._last_purge_epoch = current_epoch

    @staticmethod
    def _day_for_epoch(now_epoch: int) -> str:
        return datetime.fromtimestamp(now_epoch, BEIJING_TIME).date().isoformat()

    def _purge_expired(self, connection: sqlite3.Connection, now_epoch: int) -> None:
        cutoff_epoch = now_epoch - (self.retention_days * 24 * 60 * 60)
        cutoff_day = self._day_for_epoch(cutoff_epoch)
        connection.execute(
            "DELETE FROM analytics_sessions WHERE last_seen_epoch < ?", (cutoff_epoch,)
        )
        connection.execute(
            "DELETE FROM analytics_visitors WHERE last_seen_epoch < ?", (cutoff_epoch,)
        )
        for table in (
            "analytics_daily",
            "analytics_daily_visitors",
            "analytics_daily_pages",
            "analytics_daily_sources",
            "analytics_daily_devices",
            "analytics_browser_daily",
        ):
            connection.execute(f"DELETE FROM {table} WHERE day < ?", (cutoff_day,))

    def identify_owner(self, visitor_token: str) -> None:
        """Called only after server-side admin authentication, never by page data."""
        visitor_hash = _token_hash(visitor_token)
        with self._write_lock, closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT OR IGNORE INTO analytics_owner_aliases (visitor_hash, visitors, visits, pageviews) "
                "SELECT ?, 1, visits, pageviews FROM analytics_visitors WHERE visitor_hash = ?",
                (visitor_hash, visitor_hash),
            )
            connection.execute(
                "INSERT OR IGNORE INTO analytics_owner_aliases (visitor_hash) VALUES (?)",
                (visitor_hash,),
            )

    def record_pageview(
        self,
        *,
        visitor_token: str,
        session_token: str,
        view: str,
        referrer: Any = "",
        user_agent: Any = "",
        now_epoch: int | None = None,
    ) -> None:
        if view not in VALID_ANALYTICS_VIEWS:
            raise ValueError("invalid_analytics_view")
        visitor_hash = _token_hash(visitor_token)
        session_hash = _token_hash(session_token)
        visitor_label = f"木友-{visitor_hash[:6].upper()}"
        event_epoch = int(time.time()) if now_epoch is None else int(now_epoch)
        event_time = datetime.fromtimestamp(event_epoch, UTC).isoformat()
        event_day = self._day_for_epoch(event_epoch)
        source = normalize_referrer(referrer)
        device = classify_device(user_agent)

        with self._write_lock:
            with closing(self._connect()) as connection, connection:
                visitor_exists = connection.execute(
                    "SELECT 1 FROM analytics_visitors WHERE visitor_hash = ?",
                    (visitor_hash,),
                ).fetchone() is not None
                session_exists = connection.execute(
                    "SELECT 1 FROM analytics_sessions WHERE session_hash = ?",
                    (session_hash,),
                ).fetchone() is not None
                is_new_visitor = int(not visitor_exists)
                is_new_session = int(not session_exists)

                if visitor_exists:
                    connection.execute(
                        """
                        UPDATE analytics_visitors
                        SET last_seen_at = ?, last_seen_epoch = ?,
                            visits = visits + ?, pageviews = pageviews + 1,
                            last_view = ?, device_type = ?
                        WHERE visitor_hash = ?
                        """,
                        (
                            event_time,
                            event_epoch,
                            is_new_session,
                            view,
                            device,
                            visitor_hash,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO analytics_visitors (
                            visitor_hash, visitor_label, first_seen_at, first_seen_epoch,
                            last_seen_at, last_seen_epoch, visits, pageviews,
                            last_view, referrer_host, device_type
                        ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?)
                        """,
                        (
                            visitor_hash,
                            visitor_label,
                            event_time,
                            event_epoch,
                            event_time,
                            event_epoch,
                            view,
                            source,
                            device,
                        ),
                    )

                if session_exists:
                    connection.execute(
                        "UPDATE analytics_sessions SET last_seen_epoch = ? WHERE session_hash = ?",
                        (event_epoch, session_hash),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO analytics_sessions (
                            session_hash, visitor_hash, started_at_epoch, last_seen_epoch
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (session_hash, visitor_hash, event_epoch, event_epoch),
                    )

                connection.execute(
                    """
                    UPDATE analytics_totals
                    SET visitors = visitors + ?, visits = visits + ?,
                        pageviews = pageviews + 1,
                        first_event_at = CASE WHEN first_event_at = '' THEN ? ELSE first_event_at END,
                        last_event_at = ?
                    WHERE id = 1
                    """,
                    (is_new_visitor, is_new_session, event_time, event_time),
                )
                connection.execute(
                    """
                    INSERT INTO analytics_daily (day, visits, pageviews)
                    VALUES (?, ?, 1)
                    ON CONFLICT(day) DO UPDATE SET
                        visits = visits + excluded.visits,
                        pageviews = pageviews + 1
                    """,
                    (event_day, is_new_session),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO analytics_daily_visitors (day, visitor_hash) VALUES (?, ?)",
                    (event_day, visitor_hash),
                )
                connection.execute(
                    """
                    INSERT INTO analytics_daily_pages (day, view, pageviews)
                    VALUES (?, ?, 1)
                    ON CONFLICT(day, view) DO UPDATE SET pageviews = pageviews + 1
                    """,
                    (event_day, view),
                )
                if is_new_session:
                    connection.execute(
                        """
                        INSERT INTO analytics_daily_sources (day, source, visits)
                        VALUES (?, ?, 1)
                        ON CONFLICT(day, source) DO UPDATE SET visits = visits + 1
                        """,
                        (event_day, source),
                    )
                    connection.execute(
                        """
                        INSERT INTO analytics_daily_devices (day, device_type, visits)
                        VALUES (?, ?, 1)
                        ON CONFLICT(day, device_type) DO UPDATE SET visits = visits + 1
                        """,
                        (event_day, device),
                    )

                connection.execute(
                    "INSERT INTO analytics_browser_daily VALUES (?, ?, ?, ?, ?, ?, 1) "
                    "ON CONFLICT(day, visitor_hash, view, source, device_type) DO UPDATE SET "
                    "visits = visits + excluded.visits, pageviews = pageviews + 1",
                    (event_day, visitor_hash, view, source, device, is_new_session),
                )
                connection.execute(
                    "UPDATE analytics_owner_aliases SET visitors = visitors + ?, "
                    "visits = visits + ?, pageviews = pageviews + 1 WHERE visitor_hash = ?",
                    (is_new_visitor, is_new_session, visitor_hash),
                )

                if event_epoch - self._last_purge_epoch >= 24 * 60 * 60:
                    self._purge_expired(connection, event_epoch)
                    self._last_purge_epoch = event_epoch

    def dashboard(
        self,
        *,
        days: int = 14,
        recent_limit: int = 50,
        now_epoch: int | None = None,
        exclude_owner: bool = False,
    ) -> dict[str, Any]:
        safe_days = max(1, min(90, int(days)))
        safe_limit = max(1, min(100, int(recent_limit)))
        current_epoch = int(time.time()) if now_epoch is None else int(now_epoch)
        today = datetime.fromtimestamp(current_epoch, BEIJING_TIME).date()
        first_day = today - timedelta(days=safe_days - 1)

        with closing(self._connect()) as connection:
            connection.execute("BEGIN")
            totals = connection.execute(
                "SELECT visitors, visits, pageviews, first_event_at, last_event_at FROM analytics_totals WHERE id = 1"
            ).fetchone()
            daily_rows = connection.execute(
                """
                SELECT daily.day, daily.visits, daily.pageviews,
                       COUNT(visitor.visitor_hash) AS visitors
                FROM analytics_daily AS daily
                LEFT JOIN analytics_daily_visitors AS visitor ON visitor.day = daily.day
                WHERE daily.day >= ? AND daily.day <= ?
                GROUP BY daily.day, daily.visits, daily.pageviews
                ORDER BY daily.day
                """,
                (first_day.isoformat(), today.isoformat()),
            ).fetchall()
            page_rows = connection.execute(
                """
                SELECT view, SUM(pageviews) AS pageviews
                FROM analytics_daily_pages WHERE day >= ?
                GROUP BY view ORDER BY pageviews DESC, view
                """,
                (first_day.isoformat(),),
            ).fetchall()
            source_rows = connection.execute(
                """
                SELECT source, SUM(visits) AS visits
                FROM analytics_daily_sources WHERE day >= ?
                GROUP BY source ORDER BY visits DESC, source
                """,
                (first_day.isoformat(),),
            ).fetchall()
            device_rows = connection.execute(
                """
                SELECT device_type, SUM(visits) AS visits
                FROM analytics_daily_devices WHERE day >= ?
                GROUP BY device_type ORDER BY visits DESC, device_type
                """,
                (first_day.isoformat(),),
            ).fetchall()
            visitor_rows = connection.execute(
                """
                SELECT visitor_label, first_seen_at, last_seen_at, visits, pageviews,
                       last_view, referrer_host, device_type, visitor_hash
                FROM analytics_visitors
                ORDER BY last_seen_epoch DESC
                """,
            ).fetchall()

            owner_aliases = {row["visitor_hash"] for row in connection.execute(
                "SELECT visitor_hash FROM analytics_owner_aliases"
            )}
            owner_totals = connection.execute(
                "SELECT COALESCE(SUM(visitors), 0), COALESCE(SUM(visits), 0), "
                "COALESCE(SUM(pageviews), 0) FROM analytics_owner_aliases"
            ).fetchone()
            owner_daily = connection.execute(
                "SELECT day, SUM(b.visits) AS visits, SUM(b.pageviews) AS pageviews "
                "FROM analytics_browser_daily AS b JOIN analytics_owner_aliases USING(visitor_hash) "
                "WHERE day >= ? GROUP BY day", (first_day.isoformat(),),
            ).fetchall()
            day_visitors: dict[str, set[str]] = {}
            for row in connection.execute(
                "SELECT day, visitor_hash FROM analytics_daily_visitors WHERE day >= ?",
                (first_day.isoformat(),),
            ):
                identity = "owner" if row["visitor_hash"] in owner_aliases else row["visitor_hash"]
                if not (exclude_owner and identity == "owner"):
                    day_visitors.setdefault(row["day"], set()).add(identity)
            online_identities = {
                "owner" if row["visitor_hash"] in owner_aliases else row["visitor_hash"]
                for row in connection.execute(
                    "SELECT visitor_hash FROM analytics_visitors WHERE last_seen_epoch >= ?",
                    (current_epoch - 300,),
                )
            }
            if exclude_owner:
                online_identities.discard("owner")
            identity_metadata = connection.execute(
                "SELECT started_at, legacy_data FROM analytics_identity_metadata WHERE id = 1"
            ).fetchone()
            owner_dimensions = {}
            for dimension in ("view", "source", "device_type"):
                owner_dimensions[dimension] = {row[0]: int(row[1]) for row in connection.execute(
                    f"SELECT {dimension}, SUM(b.{'pageviews' if dimension == 'view' else 'visits'}) "
                    "FROM analytics_browser_daily AS b JOIN analytics_owner_aliases USING(visitor_hash) "
                    f"WHERE day >= ? GROUP BY {dimension}", (first_day.isoformat(),),
                )}

        trend_by_day = {
            str(row["day"]): {
                "day": str(row["day"]),
                "visitors": int(row["visitors"]),
                "visits": int(row["visits"]),
                "pageviews": int(row["pageviews"]),
            }
            for row in daily_rows
        }
        for row in owner_daily:
            if exclude_owner and row["day"] in trend_by_day:
                for metric in ("visits", "pageviews"):
                    trend_by_day[row["day"]][metric] = max(
                        0, trend_by_day[row["day"]][metric] - row[metric]
                    )
        for day, values in trend_by_day.items():
            values["visitors"] = len(day_visitors.get(day, set()))
        trend = []
        for offset in range(safe_days):
            current_day = first_day + timedelta(days=offset)
            key = current_day.isoformat()
            trend.append(
                trend_by_day.get(
                    key,
                    {"day": key, "visitors": 0, "visits": 0, "pageviews": 0},
                )
            )

        recent = []
        owner_rows = []
        for row in visitor_rows:
            item = dict(row)
            is_owner = item.pop("visitor_hash") in owner_aliases
            item["principal_id"] = "owner" if is_owner else ""
            if is_owner:
                owner_rows.append(item)
            else:
                recent.append(item)
        if owner_rows and not exclude_owner:
            owner = dict(owner_rows[0])
            owner.update(
                visitor_label="主理人 · 本人",
                first_seen_at=min(row["first_seen_at"] for row in owner_rows),
                visits=int(owner_totals[1]), pageviews=int(owner_totals[2]),
                device_type="multiple" if len({row["device_type"] for row in owner_rows}) > 1 else owner["device_type"],
            )
            recent.append(owner)
        recent.sort(key=lambda row: row["last_seen_at"], reverse=True)

        def filtered_dimensions(rows, dimension, metric):
            result = []
            for row in rows:
                value = dict(row)
                if exclude_owner:
                    value[metric] = max(0, value[metric] - owner_dimensions[dimension].get(value[dimension], 0))
                if value[metric]:
                    result.append(value)
            return sorted(result, key=lambda row: (-row[metric], row[dimension]))

        today_values = trend_by_day.get(today.isoformat(), {"visits": 0, "pageviews": 0})
        return {
            "generated_at": datetime.fromtimestamp(current_epoch, UTC).isoformat(),
            "timezone": "Asia/Shanghai",
            "retention_days": self.retention_days,
            "exclude_owner": exclude_owner,
            "identity_filter_started_at": identity_metadata["started_at"],
            "legacy_breakdown_unattributed": bool(identity_metadata["legacy_data"]),
            "summary": {
                "total_visitors": max(0, int(totals["visitors"]) - int(owner_totals[0])) + int(not exclude_owner and owner_totals[0] > 0),
                "total_visits": max(0, int(totals["visits"]) - (int(owner_totals[1]) if exclude_owner else 0)),
                "total_pageviews": max(0, int(totals["pageviews"]) - (int(owner_totals[2]) if exclude_owner else 0)),
                "today_visitors": len(day_visitors.get(today.isoformat(), set())),
                "today_visits": int(today_values["visits"]),
                "today_pageviews": int(today_values["pageviews"]),
                "online_now": len(online_identities),
                "first_event_at": str(totals["first_event_at"]),
                "last_event_at": str(totals["last_event_at"]),
            },
            "trend": trend,
            "pages": filtered_dimensions(page_rows, "view", "pageviews"),
            "sources": filtered_dimensions(source_rows, "source", "visits")[:10],
            "devices": filtered_dimensions(device_rows, "device_type", "visits"),
            "recent_visitors": recent[:safe_limit],
        }
