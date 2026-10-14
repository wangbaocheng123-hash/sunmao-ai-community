from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


EXPECTED_REPOSITORY = "wangbaocheng123-hash/sunmao-ai-community"
EXPECTED_REF = "refs/heads/production"
SIGNATURE_PATTERN = re.compile(r"sha256=([0-9a-f]{64})")
REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class WebhookDecision:
    status: int
    payload: Mapping[str, Any]
    revision: str = ""

    @property
    def should_trigger(self) -> bool:
        return bool(self.revision)


def load_webhook_secret(path: Path) -> bytes:
    try:
        secret = path.read_bytes().strip()
    except OSError:
        return b""
    if len(secret) < 32 or len(secret) > 1024 or b"\x00" in secret:
        return b""
    return secret


def evaluate_github_webhook(
    *,
    headers: Mapping[str, str],
    body: bytes,
    secret: bytes,
) -> WebhookDecision:
    signature = str(headers.get("X-Hub-Signature-256") or "").strip().lower()
    match = SIGNATURE_PATTERN.fullmatch(signature)
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    if match is None or not hmac.compare_digest(signature, expected):
        return WebhookDecision(403, {"error": "invalid_webhook_signature"})

    event = str(headers.get("X-GitHub-Event") or "").strip().lower()
    if event == "ping":
        return WebhookDecision(200, {"accepted": True, "event": "ping"})
    if event != "push":
        return WebhookDecision(202, {"accepted": False, "reason": "event_ignored"})

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return WebhookDecision(400, {"error": "invalid_webhook_payload"})
    if not isinstance(payload, dict):
        return WebhookDecision(400, {"error": "invalid_webhook_payload"})

    repository = payload.get("repository")
    full_name = repository.get("full_name") if isinstance(repository, dict) else ""
    if full_name != EXPECTED_REPOSITORY:
        return WebhookDecision(403, {"error": "unexpected_repository"})
    if payload.get("ref") != EXPECTED_REF or bool(payload.get("deleted")):
        return WebhookDecision(202, {"accepted": False, "reason": "ref_ignored"})

    revision = str(payload.get("after") or "").strip().lower()
    if REVISION_PATTERN.fullmatch(revision) is None:
        return WebhookDecision(400, {"error": "invalid_revision"})
    return WebhookDecision(
        202,
        {"accepted": True, "revision": revision},
        revision=revision,
    )


def write_deploy_trigger(path: Path, revision: str) -> None:
    if REVISION_PATTERN.fullmatch(revision) is None:
        raise ValueError("invalid deployment revision")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, f"{revision}\n".encode("ascii"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
