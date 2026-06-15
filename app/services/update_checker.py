"""GitHub release update checker."""
from __future__ import annotations

import json
import os
from urllib import request

from PyQt5.QtCore import QObject, QThread, pyqtSignal


def _repo_slug() -> str:
    raw = (os.getenv("MTA_GITHUB_REPO") or "DOUBTMYSANITY/Prime-Autoclicker").strip().strip("/")
    return raw if "/" in raw else ""


def _parse_version(tag: str) -> tuple[int, ...]:
    digits: list[int] = []
    for part in str(tag).lstrip("vV").replace("-", ".").split("."):
        if part.isdigit():
            digits.append(int(part))
        elif part and part[0].isdigit():
            num = ""
            for ch in part:
                if ch.isdigit():
                    num += ch
                else:
                    break
            if num:
                digits.append(int(num))
    return tuple(digits) if digits else (0,)


class UpdateCheckWorker(QThread):
    finished = pyqtSignal(bool, str, str)  # has_update, latest_tag, release_name

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current = current_version

    def run(self) -> None:
        repo = _repo_slug()
        if not repo:
            self.finished.emit(False, "", "")
            return
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            with request.urlopen(api_url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            tag = str(data.get("tag_name", "")).strip()
            name = str(data.get("name", tag)).strip()
            if _parse_version(tag) > _parse_version(self._current):
                self.finished.emit(True, tag, name)
            else:
                self.finished.emit(False, tag, name)
        except Exception:
            self.finished.emit(False, "", "")


class UpdateChecker(QObject):
    update_available = pyqtSignal(str, str)  # tag, name

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current = current_version
        self._worker: UpdateCheckWorker | None = None

    def check_async(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._worker = UpdateCheckWorker(self._current, self)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, has_update: bool, tag: str, name: str) -> None:
        if has_update and tag:
            self.update_available.emit(tag, name or tag)
