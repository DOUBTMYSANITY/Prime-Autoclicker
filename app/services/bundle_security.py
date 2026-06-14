"""HMAC signing and validation for profile import/export bundles."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

BUNDLE_FORMAT_VERSION = "1.1"
_SIGNATURE_KEY = "signature"
_DEFAULT_DEV_KEY = "mta-local-dev-bundle-key-change-in-production"


def _signing_key() -> bytes:
    raw = (os.getenv("MTA_BUNDLE_SIGNING_KEY") or _DEFAULT_DEV_KEY).strip()
    return raw.encode("utf-8")


def _canonical_payload(payload: dict[str, Any]) -> bytes:
    body = {k: v for k, v in payload.items() if k != _SIGNATURE_KEY}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    signed = dict(payload)
    signed.pop(_SIGNATURE_KEY, None)
    signed["version"] = BUNDLE_FORMAT_VERSION
    digest = hmac.new(_signing_key(), _canonical_payload(signed), hashlib.sha256).hexdigest()
    signed[_SIGNATURE_KEY] = digest
    return signed


def verify_bundle(payload: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "Bundle must be a JSON object."
    signature = payload.get(_SIGNATURE_KEY)
    if not signature or not isinstance(signature, str):
        return False, "Missing or invalid bundle signature."
    expected = hmac.new(_signing_key(), _canonical_payload(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False, "Bundle signature mismatch — file may be tampered with."
    version = str(payload.get("version", "")).strip()
    if version and version not in {BUNDLE_FORMAT_VERSION, "1.0"}:
        return False, f"Unsupported bundle version: {version}"
    files = payload.get("files")
    if not isinstance(files, dict):
        return False, "Bundle has no valid 'files' section."
    allowed = {"settings", "presets", "stats", "themes"}
    unknown = set(files.keys()) - allowed
    if unknown:
        return False, f"Bundle contains unknown sections: {', '.join(sorted(unknown))}"
    return True, ""
