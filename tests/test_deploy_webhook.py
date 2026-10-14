from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from sunmao_community.app import create_http_server


class GitHubDeployWebhookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.secret = b"test-only-webhook-secret-0123456789abcdef"
        self.trigger = self.root / "deploy.trigger"
        self.server = create_http_server(
            port=0,
            database_path=self.root / "community.sqlite3",
            github_webhook_secret=self.secret,
            deploy_trigger_path=self.trigger,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temporary_directory.cleanup()

    def request(self, payload: dict, *, event: str = "push", valid_signature: bool = True):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        if not valid_signature:
            signature = "0" * 64
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=3
        )
        connection.request(
            "POST",
            "/api/deploy/github",
            body=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": event,
                "X-GitHub-Delivery": "11111111-2222-3333-4444-555555555555",
                "X-Hub-Signature-256": f"sha256={signature}",
            },
        )
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    @staticmethod
    def push_payload(*, ref: str = "refs/heads/production", repository: str = "wangbaocheng123-hash/sunmao-ai-community") -> dict:
        return {
            "ref": ref,
            "after": "a" * 40,
            "deleted": False,
            "repository": {"full_name": repository},
        }

    def test_signed_production_push_creates_one_deploy_trigger(self) -> None:
        status, payload = self.request(self.push_payload())
        self.assertEqual(status, 202)
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["revision"], "a" * 40)
        self.assertEqual(self.trigger.read_text(encoding="ascii"), "a" * 40 + "\n")

    def test_main_push_is_ignored_without_creating_a_trigger(self) -> None:
        status, payload = self.request(self.push_payload(ref="refs/heads/main"))
        self.assertEqual(status, 202)
        self.assertFalse(payload["accepted"])
        self.assertFalse(self.trigger.exists())

    def test_invalid_signature_and_wrong_repository_are_rejected(self) -> None:
        status, payload = self.request(self.push_payload(), valid_signature=False)
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "invalid_webhook_signature")
        self.assertFalse(self.trigger.exists())

        status, payload = self.request(
            self.push_payload(repository="attacker/unrelated-repository")
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "unexpected_repository")
        self.assertFalse(self.trigger.exists())

    def test_signed_ping_checks_the_endpoint_without_deploying(self) -> None:
        status, payload = self.request({"zen": "test"}, event="ping")
        self.assertEqual(status, 200)
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["event"], "ping")
        self.assertFalse(self.trigger.exists())


if __name__ == "__main__":
    unittest.main()
