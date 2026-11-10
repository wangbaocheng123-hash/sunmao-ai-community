from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path

from sunmao_community.analytics import CommunityAnalyticsStore
from sunmao_community.auth import ADMIN_SESSION_SECONDS, SHORT_SESSION_SECONDS, AdminSessionManager, create_password_hash


class OwnerSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "owner persistent test password"
        cls.encoded = create_password_hash(cls.password)

    def test_fixed_thirty_day_expiry_restart_password_change_and_revocation(self):
        with tempfile.TemporaryDirectory() as root:
            database = Path(root) / "community.sqlite3"
            sessions = AdminSessionManager(self.encoded, database_path=database)
            token = sessions.login(self.password, now_epoch=1000)
            self.assertIsNotNone(token)
            sessions.close()
            restarted = AdminSessionManager(self.encoded, database_path=database)
            self.assertTrue(restarted.authenticated(token, now_epoch=1000 + ADMIN_SESSION_SECONDS - 1))
            self.assertFalse(restarted.authenticated(token, now_epoch=1000 + ADMIN_SESSION_SECONDS))
            token = restarted.login(self.password, now_epoch=2000)
            other = restarted.login(self.password, now_epoch=2000)
            restarted.logout(token)
            self.assertFalse(restarted.authenticated(token, now_epoch=2001))
            self.assertTrue(restarted.authenticated(other, now_epoch=2001))
            with closing(sqlite3.connect(database)) as connection:
                stored = connection.execute("SELECT token_hash FROM admin_sessions").fetchone()[0]
                self.assertEqual(stored, hashlib.sha256(other.encode("ascii")).hexdigest())
                self.assertNotEqual(stored, other)
            restarted.close()
            changed = AdminSessionManager(create_password_hash("a different owner password"), database_path=database)
            self.assertFalse(changed.authenticated(other, now_epoch=2001))
            changed.close()

    def test_short_session_invalid_password_and_malformed_token(self):
        sessions = AdminSessionManager(self.encoded)
        self.assertIsNone(sessions.login("an incorrect password"))
        self.assertFalse(sessions.authenticated("不是登录凭证"))
        token = sessions.login(self.password, remember=False, now_epoch=1000)
        self.assertTrue(sessions.authenticated(token, now_epoch=1001))
        self.assertFalse(sessions.authenticated(token, now_epoch=1000 + SHORT_SESSION_SECONDS))
        sessions.close()

    def test_legacy_history_relabels_only_proven_browser_and_preserves_unknown_breakdowns(self):
        with tempfile.TemporaryDirectory() as root:
            database = Path(root) / "community.sqlite3"
            store = CommunityAnalyticsStore(database)
            now = int(time.time())
            store.record_pageview(visitor_token="legacy-owner", session_token="legacy-session", view="joints", now_epoch=now)
            store.record_pageview(visitor_token="unknown-guest", session_token="guest-session", view="sizes", now_epoch=now)
            # Recreate the state of an existing pre-upgrade installation: aggregates
            # exist but per-browser daily attribution has never been collected.
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("DELETE FROM analytics_browser_daily")
                connection.execute("DROP TABLE analytics_identity_metadata")
            upgraded = CommunityAnalyticsStore(database)
            upgraded.identify_owner("legacy-owner")
            upgraded.identify_owner("legacy-owner")
            all_rows = upgraded.dashboard(now_epoch=now)
            self.assertEqual({row["visitor_label"] for row in all_rows["recent_visitors"]},
                             {"主理人 · 本人", f"木友-{hashlib.sha256(b'unknown-guest').hexdigest()[:6].upper()}"})
            filtered = upgraded.dashboard(now_epoch=now, exclude_owner=True)
            self.assertEqual(filtered["summary"]["total_pageviews"], 1)
            self.assertTrue(filtered["legacy_breakdown_unattributed"])
            self.assertEqual(sum(row["pageviews"] for row in filtered["pages"]), 2)
            # New data is attributable, even if recognition happens after a visit.
            upgraded.record_pageview(visitor_token="legacy-owner", session_token="legacy-session", view="exchange", now_epoch=now + 1)
            filtered = upgraded.dashboard(now_epoch=now + 1, exclude_owner=True)
            self.assertEqual(filtered["summary"]["total_pageviews"], 1)
            self.assertEqual(sum(row["pageviews"] for row in filtered["pages"]), 2)


if __name__ == "__main__":
    unittest.main()
