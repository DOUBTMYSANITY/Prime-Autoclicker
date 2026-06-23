"""
about_page.py – About / Info page that replaces the old Login placeholder.
"""
from __future__ import annotations

import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox,
)

from app.gui.widgets import Card, add_shadow
from plugins.Phasmo.phasmo_fan_disclaimer import ABOUT_PHASMO_DISCLAIMER, show_fan_content_disclaimer

_VERSION = "1.1.0"
_DISCORD_URL = "https://discord.gg/nkQT7XCX"


def _github_repo_slug() -> str:
    raw = (os.getenv("MTA_GITHUB_REPO") or "").strip().strip("/")
    if raw and "/" in raw:
        return raw
    return ""


def _github_url() -> str:
    slug = _github_repo_slug()
    return f"https://github.com/{slug}" if slug else ""


def _open_github(parent: QWidget | None = None) -> None:
    url = _github_url()
    if url:
        QDesktopServices.openUrl(QUrl(url))
        return
    QMessageBox.information(
        parent,
        "GitHub",
        "No repository configured.\n\n"
        "Set the MTA_GITHUB_REPO environment variable to owner/repo "
        "(for example PrimeTeam/Prime-Autoclicker), "
        "or enter it under Support → Update Checker.",
    )


class AboutPage(QWidget):
    """Info page: version, GitHub link, features, keyboard shortcuts, credits."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # ── Hero ──────────────────────────────────────────
        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=28, y=10, alpha=110)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(28, 22, 28, 22)
        hl.setSpacing(8)
        t = QLabel("ℹ️  About  ·  Prime Autoclicker")
        t.setObjectName("HeroTitle")
        s = QLabel(
            f"Version {_VERSION}  ·  Free & Open Source (GPL-3.0)\n"
            "Desktop autoclicker with plugins, stats, and macro tools."
        )
        s.setObjectName("HeroSub")
        s.setWordWrap(True)
        hl.addWidget(t)
        hl.addWidget(s)
        hl.addStretch(1)
        lay.addWidget(hero)

        # ── Three info cards ──────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Community card
        gh = Card()
        gh.setObjectName("ConfigCard")
        add_shadow(gh, blur=22, y=8, alpha=100)
        gcl = QVBoxLayout(gh)
        gcl.setContentsMargins(22, 20, 22, 20)
        gcl.setSpacing(10)
        gh_icon = QLabel("💬")
        gh_icon.setObjectName("HeaderIcon")
        gh_icon.setFixedSize(44, 44)
        gh_icon.setAlignment(Qt.AlignCenter)
        gh_icon.setStyleSheet("font-size: 22px;")
        gh_title = QLabel("Community")
        gh_title.setObjectName("CardHeader")
        gh_desc = QLabel(
            "Source code and releases on GitHub.\n"
            "Chat, support, and updates on the Prime Projects Discord."
        )
        gh_desc.setObjectName("HeroSub")
        gh_desc.setWordWrap(True)
        link_row = QHBoxLayout()
        link_row.setSpacing(8)
        gh_btn = QPushButton("GitHub  →")
        gh_btn.setCursor(Qt.PointingHandCursor)
        gh_btn.setObjectName("StartStopBtn")
        gh_btn.setFixedHeight(34)
        gh_btn.clicked.connect(lambda: _open_github(self))
        dc_btn = QPushButton("Discord  →")
        dc_btn.setCursor(Qt.PointingHandCursor)
        dc_btn.setObjectName("StartStopBtn")
        dc_btn.setFixedHeight(34)
        dc_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(_DISCORD_URL))
        )
        link_row.addWidget(gh_btn, 1)
        link_row.addWidget(dc_btn, 1)
        gcl.addWidget(gh_icon)
        gcl.addWidget(gh_title)
        gcl.addWidget(gh_desc)
        gcl.addStretch(1)
        gcl.addLayout(link_row)
        row1.addWidget(gh)

        # Key features card
        fc = Card()
        fc.setObjectName("ConfigCard")
        add_shadow(fc, blur=22, y=8, alpha=100)
        fcl = QVBoxLayout(fc)
        fcl.setContentsMargins(22, 20, 22, 20)
        fcl.setSpacing(6)
        feat_icon = QLabel("✨")
        feat_icon.setObjectName("HeaderIcon")
        feat_icon.setFixedSize(44, 44)
        feat_icon.setAlignment(Qt.AlignCenter)
        feat_icon.setStyleSheet("font-size: 22px;")
        feat_title = QLabel("Key Features")
        feat_title.setObjectName("CardHeader")
        fcl.addWidget(feat_icon)
        fcl.addWidget(feat_title)
        for feat in [
            "⌨️  Customizable global hotkey & emergency stop",
            "📊  Stats, XP, and 100+ achievements",
            "🎨  Unlockable themes",
            "💾  Auto-saved settings, presets, and profiles",
            "🔌  Plugin marketplace (Route Recorder, Input Humanization, …)",
            "🧩  Macro builder & preset hotkeys",
            "👻  Unofficial Phasmophobia reference (offline guide, timers)",
            "🔒  HMAC-signed profile import/export",
        ]:
            lbl = QLabel(feat)
            lbl.setObjectName("HeroSub")
            lbl.setWordWrap(True)
            fcl.addWidget(lbl)
        fcl.addStretch(1)
        row1.addWidget(fc)

        # Credits / info card
        cc = Card()
        cc.setObjectName("ConfigCard")
        add_shadow(cc, blur=22, y=8, alpha=100)
        ccl = QVBoxLayout(cc)
        ccl.setContentsMargins(22, 20, 22, 20)
        ccl.setSpacing(8)
        cred_icon = QLabel("💜")
        cred_icon.setObjectName("HeaderIcon")
        cred_icon.setFixedSize(44, 44)
        cred_icon.setAlignment(Qt.AlignCenter)
        cred_icon.setStyleSheet("font-size: 22px;")
        cred_title = QLabel("App Info")
        cred_title.setObjectName("CardHeader")
        ccl.addWidget(cred_icon)
        ccl.addWidget(cred_title)
        for key, val in [
            ("Version", f"v{_VERSION}"),
            ("Framework", "Python / PyQt5"),
            ("Platform", "Windows"),
            ("License", "GPL-3.0"),
            ("Stats file", "~/.mtautoclicker_stats.json"),
            ("Config file", "~/.mtautoclicker_settings.json"),
        ]:
            r = QHBoxLayout()
            kl = QLabel(key)
            kl.setObjectName("HeroSub")
            vl = QLabel(val)
            vl.setObjectName("AboutValueStrong")
            r.addWidget(kl)
            r.addStretch(1)
            r.addWidget(vl)
            ccl.addLayout(r)

        disclaimer = QLabel(
            "Use automation responsibly. Not affiliated with Mojang or any game publisher. "
            "May violate third-party Terms of Service — use at your own risk."
        )
        disclaimer.setObjectName("HeroSub")
        disclaimer.setWordWrap(True)
        ccl.addWidget(disclaimer)
        phasmo_disclaimer = QLabel(ABOUT_PHASMO_DISCLAIMER)
        phasmo_disclaimer.setObjectName("HeroSub")
        phasmo_disclaimer.setWordWrap(True)
        ccl.addWidget(phasmo_disclaimer)
        phasmo_notice_btn = QPushButton("Phasmophobia fan content notice")
        phasmo_notice_btn.setCursor(Qt.PointingHandCursor)
        phasmo_notice_btn.setObjectName("StartStopBtn")
        phasmo_notice_btn.setFixedHeight(34)
        phasmo_notice_btn.clicked.connect(lambda: show_fan_content_disclaimer(self))
        ccl.addWidget(phasmo_notice_btn)
        ccl.addStretch(1)
        row1.addWidget(cc)

        lay.addLayout(row1)

        # ── Keyboard shortcuts card ───────────────────────
        sc = Card()
        sc.setObjectName("ConfigCard")
        add_shadow(sc, blur=22, y=8, alpha=100)
        scl = QVBoxLayout(sc)
        scl.setContentsMargins(22, 20, 22, 20)
        scl.setSpacing(8)
        sc_title = QLabel("⌨️  Keyboard Shortcuts")
        sc_title.setObjectName("CardHeader")
        scl.addWidget(sc_title)
        sc_hint = QLabel("Most keys are configurable under Settings → Keybinds.")
        sc_hint.setObjectName("HeroSub")
        sc_hint.setWordWrap(True)
        scl.addWidget(sc_hint)
        for key, action in [
            ("Toggle hotkey  (default: top bar / Settings)", "Start or stop the autoclicker"),
            ("Emergency stop  (default: Z)", "Instantly stop clicking while running"),
            ("Scroll key  (Settings)", "Toggle continuous mouse scrolling"),
            ("F8 / F9  (Route Recorder plugin)", "Record / replay input routes"),
            ("Ctrl+K  (Unofficial Phasmo plugin)", "Global search in the reference guide"),
            ("↑ ↑ ↓ ↓ ← → ← → B A", "Konami Code easter egg on the home page"),
        ]:
            r = QHBoxLayout()
            kl = QLabel(key)
            kl.setObjectName("AboutKeyStrong")
            al = QLabel(action)
            al.setObjectName("HeroSub")
            al.setWordWrap(True)
            r.addWidget(kl, 1)
            r.addStretch(1)
            r.addWidget(al, 1)
            scl.addLayout(r)
        lay.addWidget(sc)

        lay.addStretch(1)
