from __future__ import annotations

import os
import json
import webbrowser
from urllib import request
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QMessageBox,
)

from app.services.app_services import AppServices
from app.gui.widgets import Card, add_shadow


class SupportHubPage(QWidget):
    def __init__(self, services: AppServices, parent=None):
        super().__init__(parent)
        self.services = services
        self._session_events: list[str] = []
        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=28, y=10, alpha=110)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(28, 22, 28, 22)
        hl.setSpacing(8)
        t = QLabel("Support Hub")
        t.setObjectName("HeroTitle")
        s = QLabel("Profiles, sync, backups, diagnostics, bug report, session replay and changelog.")
        s.setObjectName("HeroSub")
        hl.addWidget(t)
        hl.addWidget(s)
        root.addWidget(hero)

        profile = Card(); profile.setObjectName("ConfigCard"); add_shadow(profile, blur=22, y=8, alpha=90)
        pl = QVBoxLayout(profile); pl.setContentsMargins(18, 16, 18, 16); pl.setSpacing(10)
        h = QLabel("Profiles")
        h.setObjectName("CardHeader")
        pl.addWidget(h)
        row = QHBoxLayout(); row.setSpacing(8)
        self.input_profile = QLineEdit(); self.input_profile.setPlaceholderText("Profile name")
        self.cmb_profiles = QComboBox(); self.cmb_profiles.setObjectName("UnitDrop")
        self.btn_profile_save = QPushButton("Save")
        self.btn_profile_load = QPushButton("Load")
        self.btn_profile_delete = QPushButton("Delete")
        for b in (self.btn_profile_save, self.btn_profile_load, self.btn_profile_delete):
            b.setObjectName("ToggleButton"); b.setProperty("active", True)
        row.addWidget(self.input_profile, 1)
        row.addWidget(self.btn_profile_save)
        row.addWidget(self.cmb_profiles, 1)
        row.addWidget(self.btn_profile_load)
        row.addWidget(self.btn_profile_delete)
        pl.addLayout(row)
        self.lbl_profile_status = QLabel("")
        self.lbl_profile_status.setObjectName("WarnText")
        pl.addWidget(self.lbl_profile_status)
        root.addWidget(profile)

        sync = Card(); sync.setObjectName("ConfigCard"); add_shadow(sync, blur=22, y=8, alpha=90)
        sl = QVBoxLayout(sync); sl.setContentsMargins(18, 16, 18, 16); sl.setSpacing(10)
        sh = QLabel("Import / Export / Backup / Cloud Sync")
        sh.setObjectName("CardHeader")
        sl.addWidget(sh)
        r1 = QHBoxLayout(); r1.setSpacing(8)
        self.input_bundle = QLineEdit(); self.input_bundle.setPlaceholderText("Bundle path, e.g. C:/Users/..../bundle.json")
        self.btn_export = QPushButton("Export")
        self.btn_import = QPushButton("Import")
        self.btn_backup = QPushButton("Create Backup")
        for b in (self.btn_export, self.btn_import, self.btn_backup):
            b.setObjectName("ToggleButton"); b.setProperty("active", True)
        r1.addWidget(self.input_bundle, 1)
        r1.addWidget(self.btn_export)
        r1.addWidget(self.btn_import)
        r1.addWidget(self.btn_backup)
        sl.addLayout(r1)
        r2 = QHBoxLayout(); r2.setSpacing(8)
        self.input_cloud = QLineEdit(); self.input_cloud.setPlaceholderText("Cloud folder path (OneDrive/Dropbox/etc.)")
        self.btn_cloud_sync = QPushButton("Sync")
        self.btn_cloud_sync.setObjectName("ToggleButton"); self.btn_cloud_sync.setProperty("active", True)
        r2.addWidget(self.input_cloud, 1)
        r2.addWidget(self.btn_cloud_sync)
        sl.addLayout(r2)
        self.lbl_sync_status = QLabel("")
        self.lbl_sync_status.setObjectName("WarnText")
        sl.addWidget(self.lbl_sync_status)
        root.addWidget(sync)

        diag = Card(); diag.setObjectName("ConfigCard"); add_shadow(diag, blur=22, y=8, alpha=90)
        dl = QVBoxLayout(diag); dl.setContentsMargins(18, 16, 18, 16); dl.setSpacing(10)
        dh = QLabel("Diagnostics + Bug Report + Session Replay")
        dh.setObjectName("CardHeader")
        dl.addWidget(dh)
        drow = QHBoxLayout(); drow.setSpacing(8)
        self.btn_diag = QPushButton("Refresh Diagnostics")
        self.btn_bug = QPushButton("Generate Bug Report")
        self.btn_diag.setObjectName("ToggleButton"); self.btn_diag.setProperty("active", True)
        self.btn_bug.setObjectName("ToggleButton"); self.btn_bug.setProperty("active", True)
        drow.addWidget(self.btn_diag)
        drow.addWidget(self.btn_bug)
        drow.addStretch(1)
        dl.addLayout(drow)
        self.txt_diag = QTextEdit(); self.txt_diag.setObjectName("PresetList"); self.txt_diag.setReadOnly(True); self.txt_diag.setMinimumHeight(130)
        self.txt_replay = QTextEdit(); self.txt_replay.setObjectName("PresetList"); self.txt_replay.setReadOnly(True); self.txt_replay.setMinimumHeight(110)
        dl.addWidget(self.txt_diag)
        dl.addWidget(self.txt_replay)
        self.lbl_bug_status = QLabel(""); self.lbl_bug_status.setObjectName("WarnText")
        dl.addWidget(self.lbl_bug_status)
        root.addWidget(diag)

        info = Card(); info.setObjectName("ConfigCard"); add_shadow(info, blur=22, y=8, alpha=90)
        il = QVBoxLayout(info); il.setContentsMargins(18, 16, 18, 16); il.setSpacing(8)
        ih = QLabel("Changelog")
        ih.setObjectName("CardHeader")
        il.addWidget(ih)
        txt = QLabel(
            "What is new:\n"
            "- Plugin system with admin visibility\n"
            "- Macro Builder page\n"
            "- Support Hub (profiles/sync/backup/diagnostics)\n"
            "- Global search\n"
            "- Emergency stop and improved live overlay"
        )
        txt.setObjectName("WarnText")
        txt.setWordWrap(True)
        il.addWidget(txt)

        self.btn_open_plugin_guide = QPushButton("Open Plugin Guide")
        self.btn_open_plugin_guide.setObjectName("ToggleButton")
        self.btn_open_plugin_guide.setProperty("active", True)
        il.addWidget(self.btn_open_plugin_guide, 0, Qt.AlignLeft)

        self.lbl_plugin_guide = QLabel("")
        self.lbl_plugin_guide.setObjectName("WarnText")
        self.lbl_plugin_guide.setWordWrap(True)
        il.addWidget(self.lbl_plugin_guide)
        root.addWidget(info)

        updates = Card(); updates.setObjectName("ConfigCard"); add_shadow(updates, blur=22, y=8, alpha=90)
        ul = QVBoxLayout(updates); ul.setContentsMargins(18, 16, 18, 16); ul.setSpacing(8)
        uh = QLabel("Update Checker")
        uh.setObjectName("CardHeader")
        us = QLabel("Check latest GitHub releases and open downloads instantly.")
        us.setObjectName("WarnText")
        us.setWordWrap(True)
        ul.addWidget(uh)
        ul.addWidget(us)

        urow = QHBoxLayout(); urow.setSpacing(8)
        default_repo = (os.getenv("MTA_GITHUB_REPO") or "").strip().strip("/")
        self.input_repo = QLineEdit(default_repo if "/" in default_repo else "")
        self.input_repo.setPlaceholderText("owner/Prime-Autoclicker")
        self.btn_check_release = QPushButton("Check Latest")
        self.btn_open_latest = QPushButton("Open Latest Release")
        self.btn_download_latest = QPushButton("Download First Asset")
        for b in (self.btn_check_release, self.btn_open_latest, self.btn_download_latest):
            b.setObjectName("ToggleButton"); b.setProperty("active", True)
        urow.addWidget(self.input_repo, 1)
        urow.addWidget(self.btn_check_release)
        urow.addWidget(self.btn_open_latest)
        urow.addWidget(self.btn_download_latest)
        ul.addLayout(urow)

        self.lbl_update_status = QLabel("No release checked yet.")
        self.lbl_update_status.setObjectName("WarnText")
        self.lbl_update_status.setWordWrap(True)
        ul.addWidget(self.lbl_update_status)
        root.addWidget(updates)
        root.addStretch(1)

        self.btn_profile_save.clicked.connect(self._save_profile)
        self.btn_profile_load.clicked.connect(self._load_profile)
        self.btn_profile_delete.clicked.connect(self._delete_profile)

        self.btn_export.clicked.connect(self._export_bundle)
        self.btn_import.clicked.connect(self._import_bundle)
        self.btn_backup.clicked.connect(self._create_backup)
        self.btn_cloud_sync.clicked.connect(self._sync_cloud)

        self.btn_diag.clicked.connect(self._refresh_diag)
        self.btn_bug.clicked.connect(self._create_bug_report)
        self.btn_open_plugin_guide.clicked.connect(self._open_plugin_guide)
        self.btn_check_release.clicked.connect(self._check_latest_release)
        self.btn_open_latest.clicked.connect(self._open_latest_release)
        self.btn_download_latest.clicked.connect(self._download_latest_asset)
        self._latest_release_cache = None

    def set_session_events(self, events: list[str]):
        self._session_events = list(events)
        self._refresh_replay()

    def refresh_all(self):
        self.cmb_profiles.clear()
        self.cmb_profiles.addItems(self.services.list_profiles())
        self._refresh_diag()
        self._refresh_replay()

    def _save_profile(self):
        name = self.input_profile.text().strip()
        ok = self.services.save_profile(name)
        self.lbl_profile_status.setText("Profile saved." if ok else "Profile save failed.")
        self.refresh_all()

    def _load_profile(self):
        name = self.cmb_profiles.currentText().strip()
        ok = self.services.load_profile(name)
        self.lbl_profile_status.setText("Profile loaded. Restart page state may be required." if ok else "Profile load failed.")

    def _delete_profile(self):
        name = self.cmb_profiles.currentText().strip()
        ok = self.services.delete_profile(name)
        self.lbl_profile_status.setText("Profile deleted." if ok else "Profile delete failed.")
        self.refresh_all()

    def _export_bundle(self):
        path = self.input_bundle.text().strip()
        ok = self.services.export_bundle(path)
        self.lbl_sync_status.setText("Export successful." if ok else "Export failed.")

    def _import_bundle(self):
        path = self.input_bundle.text().strip()
        if not path:
            self.lbl_sync_status.setText("Import failed: bundle path is empty.")
            return
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Warning)
        confirm.setWindowTitle("Import Warning")
        confirm.setText(
            "Import will overwrite current settings, presets, stats, and theme data.\n"
            "Only import bundles from trusted sources."
        )
        confirm.setInformativeText("Continue with import?")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setDefaultButton(QMessageBox.No)
        if confirm.exec_() != QMessageBox.Yes:
            self.lbl_sync_status.setText("Import cancelled.")
            return
        ok, msg = self.services.import_bundle(path)
        self.lbl_sync_status.setText(
            "Import successful. Restart app to fully apply." if ok else f"Import failed: {msg}"
        )

    def _create_backup(self):
        path = self.services.create_backup()
        self.lbl_sync_status.setText(f"Backup created: {path}" if path else "Backup failed.")

    def _sync_cloud(self):
        ok, msg = self.services.sync_with_cloud_folder(self.input_cloud.text().strip())
        self.lbl_sync_status.setText(msg if ok else f"Error: {msg}")

    def _refresh_diag(self):
        d = self.services.diagnostics()
        lines = [
            f"Time: {d['timestamp']}",
            f"Python: {d['python'].split()[0]}",
            f"Platform: {d['platform']}",
            "",
            "Modules:",
        ]
        lines.extend([f"- {k}: {v}" for k, v in d["modules"].items()])
        lines.append("")
        lines.append("Config files:")
        lines.extend([f"- {k}: {'ok' if v else 'missing'}" for k, v in d["files"].items()])
        self.txt_diag.setPlainText("\n".join(lines))

    def _create_bug_report(self):
        path = self.services.create_bug_report(self._session_events)
        self.lbl_bug_status.setText(f"Bug report created: {path}" if path else "Bug report failed.")

    def _refresh_replay(self):
        if not self._session_events:
            self.txt_replay.setPlainText("No session events yet.")
            return
        self.txt_replay.setPlainText("\n".join(self._session_events[-100:]))

    def _open_plugin_guide(self):
        guide_path = Path(__file__).resolve().parent.parent.parent / "plugins" / "registry" / "PLUGIN_GUIDE.md"
        if not guide_path.exists():
            self.lbl_plugin_guide.setText("Plugin guide not found.")
            return
        try:
            os.startfile(str(guide_path))
            self.lbl_plugin_guide.setText(f"Opened: {guide_path}")
        except Exception as exc:
            self.lbl_plugin_guide.setText(f"Failed to open plugin guide: {exc}")

    def _repo_slug(self) -> str | None:
        raw = self.input_repo.text().strip().strip("/")
        if raw and "/" in raw:
            return raw
        env = (os.getenv("MTA_GITHUB_REPO") or "").strip().strip("/")
        if env and "/" in env:
            return env
        return None

    def _require_repo_slug(self) -> str | None:
        repo = self._repo_slug()
        if repo:
            return repo
        self.lbl_update_status.setText(
            "Enter owner/repo above (e.g. PrimeTeam/Prime-Autoclicker) "
            "or set MTA_GITHUB_REPO."
        )
        return None

    def _check_latest_release(self):
        repo = self._require_repo_slug()
        if not repo:
            return
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            with request.urlopen(api_url, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._latest_release_cache = data
            tag = str(data.get("tag_name", "unknown"))
            name = str(data.get("name", "Latest release"))
            assets = data.get("assets", []) or []
            self.lbl_update_status.setText(f"Latest: {name} ({tag}) | Assets: {len(assets)}")
        except Exception as exc:
            self.lbl_update_status.setText(f"Release check failed: {exc}")

    def _open_latest_release(self):
        repo = self._require_repo_slug()
        if not repo:
            return
        webbrowser.open(f"https://github.com/{repo}/releases/latest")
        self.lbl_update_status.setText("Opened latest release page in browser.")

    def _download_latest_asset(self):
        if not self._latest_release_cache:
            self._check_latest_release()
        data = self._latest_release_cache or {}
        assets = data.get("assets", []) or []
        if not assets:
            self.lbl_update_status.setText("No downloadable assets found in latest release.")
            return
        url = str(assets[0].get("browser_download_url", "")).strip()
        if not url:
            self.lbl_update_status.setText("Latest release has no valid download URL.")
            return
        webbrowser.open(url)
        self.lbl_update_status.setText("Opened latest release asset download in browser.")
