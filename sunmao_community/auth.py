from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
ADMIN_SESSION_SECONDS = 30 * 24 * 60 * 60
SHORT_SESSION_SECONDS = 12 * 60 * 60
OWNER_ID = "owner"
OWNER_NAME = "主理人"


def create_password_hash(password: str, *, salt: bytes | None = None) -> str:
    if not isinstance(password, str) or len(password) < 12 or len(password) > 256:
        raise ValueError("admin password must contain 12 to 256 characters")
    password_salt = salt or secrets.token_bytes(18)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), password_salt, PASSWORD_ITERATIONS
    )
    encoded_salt = base64.urlsafe_b64encode(password_salt).decode("ascii").rstrip("=")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${encoded_salt}${encoded_digest}"


def _decode_base64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def _password_hash_parts(encoded: str) -> tuple[int, bytes, bytes] | None:
    try:
        scheme, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        iterations = int(iterations_text)
        salt = _decode_base64(salt_text)
        expected = _decode_base64(digest_text)
    except (ValueError, TypeError, binascii.Error):
        return None
    if (
        scheme != PASSWORD_SCHEME
        or iterations != PASSWORD_ITERATIONS
        or not (16 <= len(salt) <= 64)
        or len(expected) != 32
    ):
        return None
    return iterations, salt, expected


def verify_password(password: str, encoded: str) -> bool:
    parsed = _password_hash_parts(encoded)
    if parsed is None or not isinstance(password, str) or not (12 <= len(password) <= 256):
        return False
    iterations, salt, expected = parsed
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


class AdminSessionManager:
    """Revocable, fixed-expiry sessions. Only token digests are persisted."""

    def __init__(
        self,
        password_hash: str = "",
        *,
        session_seconds: int = ADMIN_SESSION_SECONDS,
        database_path: Path | None = None,
    ) -> None:
        self.password_hash = str(password_hash or "").strip()
        self.session_seconds = max(300, int(session_seconds))
        self._lock = threading.Lock()
        if database_path is not None:
            database_path = Path(database_path).expanduser().resolve()
            database_path.parent.mkdir(parents=True, exist_ok=True)
        self._database = sqlite3.connect(
            str(database_path) if database_path is not None else ":memory:",
            timeout=5, check_same_thread=False,
        )
        self._database.row_factory = sqlite3.Row
        self._database.executescript("""
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token_hash TEXT PRIMARY KEY,
                credential_version TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                remembered INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS admin_login_events (
                id INTEGER PRIMARY KEY,
                created_at_epoch INTEGER NOT NULL,
                method TEXT NOT NULL,
                device_type TEXT NOT NULL
            );
        """)
        with self._database:
            self._database.execute(
                "DELETE FROM admin_sessions WHERE credential_version != ?",
                (self._credential_version(),),
            )

    @property
    def configured(self) -> bool:
        return _password_hash_parts(self.password_hash) is not None

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def _credential_version(self) -> str:
        return hashlib.sha256(self.password_hash.encode("utf-8")).hexdigest()

    def login(
        self, password: str, *, now_epoch: int | None = None,
        remember: bool = True, device_type: str = "desktop",
    ) -> str | None:
        if not self.configured or not verify_password(password, self.password_hash):
            return None
        current = int(time.time()) if now_epoch is None else int(now_epoch)
        token = secrets.token_urlsafe(32)
        duration = self.session_seconds if remember else min(self.session_seconds, SHORT_SESSION_SECONDS)
        with self._lock, self._database:
            self._purge_locked(current)
            self._database.execute(
                "INSERT INTO admin_sessions VALUES (?, ?, ?, ?)",
                (self._token_hash(token), self._credential_version(), current + duration, int(remember)),
            )
            self._record_login_locked(current, "password", device_type)
        return token

    def session(self, token: str, *, now_epoch: int | None = None) -> dict | None:
        if not token or not self.configured:
            return None
        current = int(time.time()) if now_epoch is None else int(now_epoch)
        try:
            token_hash = self._token_hash(token)
        except (UnicodeEncodeError, AttributeError):
            return None
        with self._lock, self._database:
            self._purge_locked(current)
            row = self._database.execute(
                "SELECT expires_at, remembered FROM admin_sessions "
                "WHERE token_hash = ? AND credential_version = ?",
                (token_hash, self._credential_version()),
            ).fetchone()
        if row is None:
            return None
        return {
            "principal_id": OWNER_ID, "display_name": OWNER_NAME,
            "expires_at": datetime.fromtimestamp(row["expires_at"], UTC).isoformat(),
            "remembered": bool(row["remembered"]),
        }

    def authenticated(self, token: str, *, now_epoch: int | None = None) -> bool:
        return self.session(token, now_epoch=now_epoch) is not None

    def record_resume(self, token: str, *, device_type: str = "desktop") -> bool:
        if not self.authenticated(token):
            return False
        with self._lock, self._database:
            self._record_login_locked(int(time.time()), "automatic", device_type)
        return True

    def _record_login_locked(self, current: int, method: str, device_type: str) -> None:
        device = device_type if device_type in {"desktop", "mobile", "tablet", "bot"} else "desktop"
        self._database.execute(
            "INSERT INTO admin_login_events (created_at_epoch, method, device_type) VALUES (?, ?, ?)",
            (current, method, device),
        )

    def login_events(self, *, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._database.execute(
                "SELECT created_at_epoch, method, device_type FROM admin_login_events "
                "ORDER BY id DESC LIMIT ?", (max(1, min(100, int(limit))),),
            ).fetchall()
        return [dict(
            principal_id=OWNER_ID, display_name=OWNER_NAME,
            created_at=datetime.fromtimestamp(row["created_at_epoch"], UTC).isoformat(),
            method=row["method"], device_type=row["device_type"],
        ) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._database.close()

    def logout(self, token: str) -> None:
        if not token:
            return
        try:
            token_hash = self._token_hash(token)
        except (UnicodeEncodeError, AttributeError):
            return
        with self._lock, self._database:
            self._database.execute("DELETE FROM admin_sessions WHERE token_hash = ?", (token_hash,))

    def _purge_locked(self, current_epoch: int) -> None:
        self._database.execute("DELETE FROM admin_sessions WHERE expires_at <= ?", (current_epoch,))
        self._database.execute(
            "DELETE FROM admin_login_events WHERE created_at_epoch < ?",
            (current_epoch - 365 * 24 * 60 * 60,),
        )
