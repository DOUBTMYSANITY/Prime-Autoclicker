"""Read-only Phasmophobia save helpers for cheat-sheet version detection."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    CRYPTO_OK = True
except ImportError:
    CRYPTO_OK = False

# Public save-format key used by Phasmophobia (community-documented).
_PASSWORD = b"t36gref9u84y7f43g"


def default_save_path() -> Path:
    if os.name == "nt":
        return Path(os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\Kinetic Games\Phasmophobia\SaveFile.txt"))
    return Path.home() / ".config" / "unity3d" / "Kinetic Games" / "Phasmophobia" / "SaveFile.txt"


def read_game_version_from_save(text: str) -> str | None:
    match = re.search(
        r'"GameVersion"\s*:\s*\{\s*"__type"\s*:\s*"[^"]+"\s*,\s*"value"\s*:\s*"([^"]+)"',
        text,
    )
    return match.group(1) if match else None


def _key(iv: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha1", _PASSWORD, iv, 100, 16)


def _decrypt_save(raw: bytes) -> str:
    if not CRYPTO_OK:
        raise RuntimeError("cryptography package required for encrypted saves")
    if len(raw) < 32 or len(raw[16:]) % 16:
        raise ValueError("Not a valid encrypted Phasmophobia save.")
    iv = raw[:16]
    cipher = Cipher(algorithms.AES(_key(iv)), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    data = decryptor.update(raw[16:]) + decryptor.finalize()
    pad = data[-1]
    if 1 <= pad <= 16:
        data = data[:-pad]
    return data.decode("utf-8")


def load_save(path: str | Path) -> tuple[str, bytes | None, bool]:
    with open(path, "rb") as handle:
        raw = handle.read()
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            text = raw.decode(encoding).strip()
            if text.startswith("{"):
                return text, None, True
        except UnicodeDecodeError:
            pass
    return _decrypt_save(raw), raw[:16], False
