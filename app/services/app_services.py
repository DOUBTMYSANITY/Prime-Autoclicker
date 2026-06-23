from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.pages.presets_page import PRESETS_FILE
from app.pages.settings_page import SETTINGS_FILE
from app.services.stats_tracker import STATS_FILE
from app.services.bundle_security import sign_bundle, verify_bundle
from app.styling.themes import THEME_FILE

APP_META_FILE = os.path.join(os.path.expanduser("~"), ".mtautoclicker_appmeta.json")
PROFILES_DIR = os.path.join(os.path.expanduser("~"), ".mtautoclicker_profiles")
BACKUPS_DIR = os.path.join(os.path.expanduser("~"), ".mtautoclicker_backups")
BUGREPORTS_DIR = os.path.join(os.path.expanduser("~"), ".mtautoclicker_bugreports")


def _read_json(path: str, default: Any):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


class AppServices:
    def __init__(self):
        self.config_files = {
            "settings": SETTINGS_FILE,
            "presets": PRESETS_FILE,
            "stats": STATS_FILE,
            "themes": THEME_FILE,
        }

    def is_first_start(self) -> bool:
        meta = _read_json(APP_META_FILE, {})
        return not bool(meta.get("onboarding_completed"))

    def mark_onboarding_completed(self):
        meta = _read_json(APP_META_FILE, {})
        meta["onboarding_completed"] = True
        meta["onboarding_completed_at"] = datetime.now().isoformat()
        _write_json(APP_META_FILE, meta)

    def save_profile(self, name: str) -> bool:
        name = name.strip()
        if not name or "/" in name or "\\" in name or ".." in name:
            return False
        Path(PROFILES_DIR).mkdir(parents=True, exist_ok=True)
        payload = {}
        for key, path in self.config_files.items():
            payload[key] = _read_json(path, {})
        payload["_created_at"] = datetime.now().isoformat()
        return _write_json(os.path.join(PROFILES_DIR, f"{name}.json"), payload)

    def load_profile(self, name: str) -> bool:
        if not name.strip() or ".." in name:
            return False
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        payload = _read_json(path, None)
        if not isinstance(payload, dict):
            return False
        ok = True
        for key, file_path in self.config_files.items():
            data = payload.get(key, {} if key != "presets" else [])
            ok = _write_json(file_path, data) and ok
        return ok

    def delete_profile(self, name: str) -> bool:
        if not name.strip() or ".." in name:
            return False
        try:
            os.remove(os.path.join(PROFILES_DIR, f"{name}.json"))
            return True
        except Exception:
            return False

    def list_profiles(self) -> list[str]:
        if not os.path.isdir(PROFILES_DIR):
            return []
        return sorted([Path(p).stem for p in Path(PROFILES_DIR).glob("*.json")])

    def export_bundle(self, dest_path: str) -> bool:
        dest_path = dest_path.strip()
        if not dest_path or ".." in dest_path:
            return False
        bundle = sign_bundle({
            "created_at": datetime.now().isoformat(),
            "files": {
                key: _read_json(path, {} if key != "presets" else [])
                for key, path in self.config_files.items()
            },
        })
        return _write_json(dest_path, bundle)

    def import_bundle(self, src_path: str) -> tuple[bool, str]:
        src_path = src_path.strip()
        if not src_path or ".." in src_path:
            return False, "Invalid bundle path."
        data = _read_json(src_path, None)
        if not isinstance(data, dict):
            return False, "Bundle is not valid JSON."
        ok, msg = verify_bundle(data)
        if not ok:
            return False, msg
        files = data.get("files", {})
        wrote = True
        for key, path in self.config_files.items():
            if key in files:
                wrote = _write_json(path, files[key]) and wrote
        return wrote, "Import successful." if wrote else "Import failed while writing files."

    def create_backup(self) -> str | None:
        Path(BACKUPS_DIR).mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUPS_DIR, f"backup_{stamp}.json")
        return backup_file if self.export_bundle(backup_file) else None

    def sync_with_cloud_folder(self, cloud_dir: str) -> tuple[bool, str]:
        cloud_dir = cloud_dir.strip()
        if not cloud_dir or ".." in cloud_dir:
            return False, "Cloud folder path is invalid."
        try:
            Path(cloud_dir).mkdir(parents=True, exist_ok=True)
            for key, src in self.config_files.items():
                dst = os.path.join(cloud_dir, Path(src).name)
                src_exists = os.path.exists(src)
                dst_exists = os.path.exists(dst)

                if src_exists and not dst_exists:
                    shutil.copy2(src, dst)
                    continue
                if dst_exists and not src_exists:
                    if dst.endswith(".json"):
                        data = _read_json(dst, None)
                        if isinstance(data, dict) and "signature" in data:
                            ok, msg = verify_bundle(data)
                            if not ok:
                                continue
                    shutil.copy2(dst, src)
                    continue
                if src_exists and dst_exists:
                    if os.path.getmtime(src) >= os.path.getmtime(dst):
                        shutil.copy2(src, dst)
                    else:
                        if dst.endswith(".json"):
                            data = _read_json(dst, None)
                            if isinstance(data, dict) and "signature" in data:
                                ok, msg = verify_bundle(data)
                                if not ok:
                                    continue
                        shutil.copy2(dst, src)
            return True, "Cloud folder sync completed."
        except Exception as exc:
            return False, f"Cloud sync failed: {exc}"

    def diagnostics(self) -> dict[str, Any]:
        mods = ["PyQt5", "pynput", "pyautogui", "psutil", "numpy", "PIL", "screen_brightness_control"]
        module_state: dict[str, str] = {}
        for m in mods:
            try:
                __import__(m)
                module_state[m] = "ok"
            except Exception:
                module_state[m] = "missing"

        files = {k: os.path.exists(v) for k, v in self.config_files.items()}
        return {
            "timestamp": datetime.now().isoformat(),
            "python": sys.version,
            "platform": sys.platform,
            "modules": module_state,
            "files": files,
        }

    def create_bug_report(self, events: list[str]) -> str | None:
        Path(BUGREPORTS_DIR).mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(BUGREPORTS_DIR, f"bugreport_{stamp}.json")
        payload = {
            "generated_at": datetime.now().isoformat(),
            "diagnostics": self.diagnostics(),
            "recent_events": events[-200:],
        }
        return path if _write_json(path, payload) else None
