from __future__ import annotations

import os
import sys
import platform
import subprocess
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QScrollArea, QCheckBox, QComboBox,
)

from app.gui.widgets import Card, add_shadow, FocusClearSpinBox
from app.services.stats_tracker import StatsTracker, _SECRET_KEYS
from app.styling.themes import (
    THEMES, THEME_MAP, _save_theme_prefs, _load_theme_prefs,
    get_unlocked_ids, mark_unlocked, get_selected_theme_id,
    set_selected_theme_id,
)
from app.services.plugin_system import PluginManager

_AUTOCLICKER_SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".mtautoclicker_settings.json")


class AdminPanel(QWidget):
    """Hidden admin panel — edit stats, achievements, and all tracked data."""
    stats_reset = pyqtSignal()
    theme_applied = pyqtSignal()  # emitted when theme unlocks/selection change

    def __init__(self, tracker: StatsTracker, plugin_manager: PluginManager | None = None, parent=None):
        super().__init__(parent)
        self.tracker = tracker
        self.plugin_manager = plugin_manager

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # Hero
        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=28, y=10, alpha=110)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(28, 22, 28, 22)
        hl.setSpacing(8)
        t = QLabel("\U0001f6e0  Admin Panel")
        t.setObjectName("HeroTitle")
        s = QLabel("Secret control panel — edit all stats and achievements directly.")
        s.setObjectName("HeroSub")
        hl.addWidget(t)
        hl.addWidget(s)
        hl.addStretch(1)

        # --- Stats editor card ---
        stats_card = Card()
        stats_card.setObjectName("ConfigCard")
        add_shadow(stats_card, blur=26, y=10, alpha=110)
        sc_lay = QVBoxLayout(stats_card)
        sc_lay.setContentsMargins(20, 18, 20, 18)
        sc_lay.setSpacing(14)

        sc_h = QHBoxLayout()
        sc_h.setSpacing(10)
        sc_icon = QLabel("\U0001f4ca")
        sc_icon.setObjectName("HeaderIcon")
        sc_icon.setFixedSize(34, 34)
        sc_icon.setAlignment(Qt.AlignCenter)
        sc_title = QLabel("Edit Statistics")
        sc_title.setObjectName("CardHeader")
        sc_h.addWidget(sc_icon)
        sc_h.addWidget(sc_title)
        sc_h.addStretch(1)
        sc_lay.addLayout(sc_h)

        inner_stats = Card(radius=16)
        inner_stats.setObjectName("InnerPanel")
        is_lay = QVBoxLayout(inner_stats)
        is_lay.setContentsMargins(14, 14, 14, 14)
        is_lay.setSpacing(10)

        # Total clicks
        self.spin_total_clicks = self._make_spin_row(is_lay, "Total Clicks", 0, 999_999_999)
        # Total sessions
        self.spin_total_sessions = self._make_spin_row(is_lay, "Total Sessions", 0, 999_999)
        # Total session time (seconds)
        self.spin_total_time = self._make_spin_row(is_lay, "Total Active Time (seconds)", 0, 99_999_999)
        # Today's clicks
        self.spin_today = self._make_spin_row(is_lay, "Clicks Today", 0, 999_999_999)

        is_lay.addStretch(1)
        sc_lay.addWidget(inner_stats)

        # Apply button for stats
        self.btn_apply_stats = QPushButton("\u2714  Apply Stats")
        self.btn_apply_stats.setObjectName("StartStopBtn")
        self.btn_apply_stats.setCursor(Qt.PointingHandCursor)
        self.btn_apply_stats.setFixedHeight(42)
        self.btn_apply_stats.clicked.connect(self._apply_stats)
        sc_lay.addWidget(self.btn_apply_stats)
        sc_lay.addStretch(1)

        # --- Achievements editor card ---
        ach_card = Card()
        ach_card.setObjectName("ConfigCard")
        add_shadow(ach_card, blur=26, y=10, alpha=110)
        ac_lay = QVBoxLayout(ach_card)
        ac_lay.setContentsMargins(20, 18, 20, 18)
        ac_lay.setSpacing(14)

        ac_h = QHBoxLayout()
        ac_h.setSpacing(10)
        ac_icon = QLabel("\U0001f3c5")
        ac_icon.setObjectName("HeaderIcon")
        ac_icon.setFixedSize(34, 34)
        ac_icon.setAlignment(Qt.AlignCenter)
        ac_title = QLabel("Force Achievements")
        ac_title.setObjectName("CardHeader")
        ac_h.addWidget(ac_icon)
        ac_h.addWidget(ac_title)
        ac_h.addStretch(1)
        ac_lay.addLayout(ac_h)

        ach_hint = QLabel(
            "Check a box to force-unlock an achievement by setting "
            "your stats just high enough. Uncheck to reset progress."
        )
        ach_hint.setObjectName("WarnText")
        ach_hint.setWordWrap(True)
        ac_lay.addWidget(ach_hint)

        # Scrollable achievement checkboxes
        ach_scroll = QScrollArea()
        ach_scroll.setWidgetResizable(True)
        ach_scroll.setFrameShape(QFrame.NoFrame)
        ach_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ach_scroll.setMinimumHeight(300)
        ach_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        ach_scroll_w = QWidget()
        ach_scroll_w.setStyleSheet("background: transparent;")
        self.ach_grid = QGridLayout(ach_scroll_w)
        self.ach_grid.setSpacing(8)
        self.ach_grid.setContentsMargins(0, 0, 0, 40)
        ach_scroll.setWidget(ach_scroll_w)
        ac_lay.addWidget(ach_scroll)

        self.btn_unlock_all = QPushButton("\U0001f513  Unlock All")
        self.btn_unlock_all.setObjectName("ToggleButton")
        self.btn_unlock_all.setProperty("active", True)
        self.btn_unlock_all.setCursor(Qt.PointingHandCursor)
        self.btn_unlock_all.setFixedHeight(38)
        self.btn_unlock_all.clicked.connect(self._unlock_all)

        self.btn_lock_all = QPushButton("\U0001f512  Lock All")
        self.btn_lock_all.setObjectName("ToggleButton")
        self.btn_lock_all.setProperty("active", False)
        self.btn_lock_all.setCursor(Qt.PointingHandCursor)
        self.btn_lock_all.setFixedHeight(38)
        self.btn_lock_all.clicked.connect(self._lock_all)

        ach_btn_row = QHBoxLayout()
        ach_btn_row.setSpacing(10)
        ach_btn_row.addWidget(self.btn_unlock_all)
        ach_btn_row.addWidget(self.btn_lock_all)
        ach_btn_row.addStretch(1)
        ac_lay.addLayout(ach_btn_row)
        ac_lay.addStretch(1)

        # --- Danger zone card ---
        danger_card = Card()
        danger_card.setObjectName("ConfigCard")
        add_shadow(danger_card, blur=26, y=10, alpha=110)
        dc_lay = QVBoxLayout(danger_card)
        dc_lay.setContentsMargins(20, 18, 20, 18)
        dc_lay.setSpacing(14)

        dc_h = QHBoxLayout()
        dc_h.setSpacing(10)
        dc_icon = QLabel("\u26a0")
        dc_icon.setObjectName("HeaderIcon")
        dc_icon.setFixedSize(34, 34)
        dc_icon.setAlignment(Qt.AlignCenter)
        dc_title = QLabel("Danger Zone")
        dc_title.setObjectName("CardHeader")
        dc_h.addWidget(dc_icon)
        dc_h.addWidget(dc_title)
        dc_h.addStretch(1)
        dc_lay.addLayout(dc_h)

        self.btn_reset_all = QPushButton("\U0001f5d1  Reset ALL Stats")
        self.btn_reset_all.setObjectName("ToggleButton")
        self.btn_reset_all.setProperty("active", False)
        self.btn_reset_all.setCursor(Qt.PointingHandCursor)
        self.btn_reset_all.setFixedHeight(42)
        self.btn_reset_all.setStyleSheet(
            "QPushButton { background: rgba(255, 60, 60, 0.15); "
            "border: 1px solid rgba(255, 60, 60, 0.3); border-radius: 12px; "
            "color: #FF9C9C; font-weight: 700; font-size: 13px; }"
            "QPushButton:hover { background: rgba(255, 60, 60, 0.25); }"
        )
        self.btn_reset_all.clicked.connect(self._reset_all)

        self.btn_reset_heatmap = QPushButton("\U0001f5fa  Clear Heatmap")
        self.btn_reset_heatmap.setObjectName("ToggleButton")
        self.btn_reset_heatmap.setProperty("active", False)
        self.btn_reset_heatmap.setCursor(Qt.PointingHandCursor)
        self.btn_reset_heatmap.setFixedHeight(38)
        self.btn_reset_heatmap.clicked.connect(self._reset_heatmap)

        dc_lay.addWidget(self.btn_reset_all)
        dc_lay.addWidget(self.btn_reset_heatmap)
        dc_lay.addStretch(1)

        # --- XP / Level editor card ---
        xp_card = Card()
        xp_card.setObjectName("ConfigCard")
        add_shadow(xp_card, blur=26, y=10, alpha=110)
        xp_lay = QVBoxLayout(xp_card)
        xp_lay.setContentsMargins(20, 18, 20, 18)
        xp_lay.setSpacing(14)

        xp_h = QHBoxLayout()
        xp_h.setSpacing(10)
        xp_icon = QLabel("\u2728")
        xp_icon.setObjectName("HeaderIcon")
        xp_icon.setFixedSize(34, 34)
        xp_icon.setAlignment(Qt.AlignCenter)
        xp_title = QLabel("XP & Level")
        xp_title.setObjectName("CardHeader")
        xp_h.addWidget(xp_icon)
        xp_h.addWidget(xp_title)
        xp_h.addStretch(1)
        xp_lay.addLayout(xp_h)

        inner_xp = Card(radius=16)
        inner_xp.setObjectName("InnerPanel")
        ixp_lay = QVBoxLayout(inner_xp)
        ixp_lay.setContentsMargins(14, 14, 14, 14)
        ixp_lay.setSpacing(10)

        self.spin_xp = self._make_spin_row(ixp_lay, "Total XP", 0, 999_999_999)
        self.lbl_level_preview = QLabel("Level: —")
        self.lbl_level_preview.setObjectName("WarnText")
        ixp_lay.addWidget(self.lbl_level_preview)

        self.spin_xp.valueChanged.connect(self._preview_level)

        self.btn_apply_xp = QPushButton("\u2714  Apply XP")
        self.btn_apply_xp.setObjectName("StartStopBtn")
        self.btn_apply_xp.setCursor(Qt.PointingHandCursor)
        self.btn_apply_xp.setFixedHeight(42)
        self.btn_apply_xp.clicked.connect(self._apply_xp)
        ixp_lay.addStretch(1)

        xp_lay.addWidget(inner_xp)
        xp_lay.addWidget(self.btn_apply_xp)
        xp_lay.addStretch(1)

        # --- Secrets editor card ---
        sec_card = Card()
        sec_card.setObjectName("ConfigCard")
        add_shadow(sec_card, blur=26, y=10, alpha=110)
        sec_lay = QVBoxLayout(sec_card)
        sec_lay.setContentsMargins(20, 18, 20, 18)
        sec_lay.setSpacing(14)

        sec_h = QHBoxLayout()
        sec_h.setSpacing(10)
        sec_icon = QLabel("\U0001f52e")
        sec_icon.setObjectName("HeaderIcon")
        sec_icon.setFixedSize(34, 34)
        sec_icon.setAlignment(Qt.AlignCenter)
        sec_title = QLabel("Secret Achievements")
        sec_title.setObjectName("CardHeader")
        sec_h.addWidget(sec_icon)
        sec_h.addWidget(sec_title)
        sec_h.addStretch(1)
        sec_lay.addLayout(sec_h)

        sec_hint = QLabel("Toggle individual secret achievements on or off.")
        sec_hint.setObjectName("WarnText")
        sec_hint.setWordWrap(True)
        sec_lay.addWidget(sec_hint)

        inner_sec = Card(radius=16)
        inner_sec.setObjectName("InnerPanel")
        isec_lay = QVBoxLayout(inner_sec)
        isec_lay.setContentsMargins(14, 14, 14, 14)
        isec_lay.setSpacing(8)

        self._secret_checks: list[tuple[QCheckBox, str]] = []
        _secret_labels = {
            "konami_code": "\U0001f3ae  Konami Code",
            "speedrunner": "\u26a1  Speedrunner",
            "patience": "\U0001f9d8  Patience is a Virtue",
            "lucky_seven": "\U0001f340  Lucky Seven",
            "page_turner": "\U0001f4d6  Page Turner",
            "click_frenzy": "\U0001f4a5  Click Frenzy",
        }
        for key in _SECRET_KEYS:
            chk = QCheckBox(_secret_labels.get(key, key))
            chk.setStyleSheet(
                "QCheckBox { color: rgba(233,237,255,0.85); font-size: 12.5px; spacing: 8px; }"
                "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; "
                "border: 1px solid rgba(255,255,255,0.15); background: rgba(0,0,0,0.20); }"
                "QCheckBox::indicator:checked { background: rgba(78,141,255,0.50); "
                "border: 1px solid rgba(78,141,255,0.6); }"
            )
            isec_lay.addWidget(chk)
            self._secret_checks.append((chk, key))

        self.btn_apply_secrets = QPushButton("\u2714  Apply Secrets")
        self.btn_apply_secrets.setObjectName("StartStopBtn")
        self.btn_apply_secrets.setCursor(Qt.PointingHandCursor)
        self.btn_apply_secrets.setFixedHeight(42)
        self.btn_apply_secrets.clicked.connect(self._apply_secrets)
        isec_lay.addStretch(1)

        sec_lay.addWidget(inner_sec)
        sec_lay.addWidget(self.btn_apply_secrets)
        sec_lay.addStretch(1)

        # --- Theme manager card ---
        tm_card = Card()
        tm_card.setObjectName("ConfigCard")
        add_shadow(tm_card, blur=26, y=10, alpha=110)
        tm_lay = QVBoxLayout(tm_card)
        tm_lay.setContentsMargins(20, 18, 20, 18)
        tm_lay.setSpacing(14)

        tm_h = QHBoxLayout()
        tm_h.setSpacing(10)
        tm_icon = QLabel("\U0001f3a8")
        tm_icon.setObjectName("HeaderIcon")
        tm_icon.setFixedSize(34, 34)
        tm_icon.setAlignment(Qt.AlignCenter)
        tm_title = QLabel("Theme Manager")
        tm_title.setObjectName("CardHeader")
        tm_h.addWidget(tm_icon)
        tm_h.addWidget(tm_title)
        tm_h.addStretch(1)
        tm_lay.addLayout(tm_h)

        tm_hint = QLabel("Force-unlock any theme (including Admin Override) and switch instantly.")
        tm_hint.setObjectName("WarnText")
        tm_hint.setWordWrap(True)
        tm_lay.addWidget(tm_hint)

        inner_tm = Card(radius=16)
        inner_tm.setObjectName("InnerPanel")
        itm_lay = QVBoxLayout(inner_tm)
        itm_lay.setContentsMargins(14, 14, 14, 14)
        itm_lay.setSpacing(8)

        self._theme_checks: list[tuple[QCheckBox, str]] = []
        for t in THEMES:
            tid = t["id"]
            chk = QCheckBox(f"{t['icon']}  {t['name']}  —  {t.get('unlock_desc', 'default')}")
            chk.setStyleSheet(
                "QCheckBox { color: rgba(233,237,255,0.85); font-size: 12.5px; spacing: 8px; }"
                "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; "
                "border: 1px solid rgba(255,255,255,0.15); background: rgba(0,0,0,0.20); }"
                "QCheckBox::indicator:checked { background: rgba(78,141,255,0.50); "
                "border: 1px solid rgba(78,141,255,0.6); }"
            )
            itm_lay.addWidget(chk)
            self._theme_checks.append((chk, tid))

        itm_lay.addStretch(1)

        self.btn_unlock_themes = QPushButton("\U0001f513  Apply Theme Unlocks")
        self.btn_unlock_themes.setObjectName("StartStopBtn")
        self.btn_unlock_themes.setCursor(Qt.PointingHandCursor)
        self.btn_unlock_themes.setFixedHeight(42)
        self.btn_unlock_themes.clicked.connect(self._apply_theme_unlocks)

        # Theme selector
        sel_row = QHBoxLayout()
        sel_row.setSpacing(10)
        lbl_sel = QLabel("Active Theme:")
        lbl_sel.setObjectName("TimeUnit")
        self.combo_theme = QComboBox()
        self.combo_theme.setObjectName("UnitDrop")
        self.combo_theme.setFixedHeight(38)
        for t in THEMES:
            self.combo_theme.addItem(f"{t['icon']}  {t['name']}", t["id"])
        sel_row.addWidget(lbl_sel)
        sel_row.addWidget(self.combo_theme, 1)

        self.btn_apply_theme = QPushButton("\U0001f3a8  Apply Theme")
        self.btn_apply_theme.setObjectName("StartStopBtn")
        self.btn_apply_theme.setCursor(Qt.PointingHandCursor)
        self.btn_apply_theme.setFixedHeight(42)
        self.btn_apply_theme.clicked.connect(self._apply_active_theme)

        tm_lay.addWidget(inner_tm)
        tm_lay.addWidget(self.btn_unlock_themes)
        tm_lay.addLayout(sel_row)
        tm_lay.addWidget(self.btn_apply_theme)
        tm_lay.addStretch(1)

        # ─── System Info card ─────────────────────────
        sys_card = Card()
        sys_card.setObjectName("ConfigCard")
        add_shadow(sys_card, blur=26, y=10, alpha=110)
        sys_lay = QVBoxLayout(sys_card)
        sys_lay.setContentsMargins(20, 18, 20, 18)
        sys_lay.setSpacing(12)

        sy_h = QHBoxLayout(); sy_h.setSpacing(10)
        sy_icon = QLabel("🖥"); sy_icon.setObjectName("HeaderIcon"); sy_icon.setFixedSize(34,34); sy_icon.setAlignment(Qt.AlignCenter)
        sy_title = QLabel("System Info"); sy_title.setObjectName("CardHeader")
        sy_h.addWidget(sy_icon); sy_h.addWidget(sy_title); sy_h.addStretch(1)
        sys_lay.addLayout(sy_h)

        def _info_row(label: str, value: str):
            row = QHBoxLayout(); row.setSpacing(12)
            lbl = QLabel(label); lbl.setObjectName("TimeUnit"); lbl.setFixedWidth(200)
            val = QLabel(value); val.setObjectName("WarnText"); val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row.addWidget(lbl); row.addWidget(val, 1)
            sys_lay.addLayout(row)

        _info_row("App Version:", "1.0.0")
        _info_row("Python:", f"{sys.version.split()[0]}  ({platform.python_implementation()})")
        _info_row("OS:", f"{platform.system()} {platform.release()}")
        _info_row("AutoClicker Settings:", _AUTOCLICKER_SETTINGS_FILE)

        sys_btn_row = QHBoxLayout(); sys_btn_row.setSpacing(10)
        def _open_folder(path: str):
            folder = os.path.dirname(path)
            try:
                if platform.system() == "Windows":
                    os.startfile(folder)
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", folder])
                else:
                    subprocess.Popen(["xdg-open", folder])
            except Exception:
                pass

        btn_open_cfg = QPushButton("📂  Open Config Folder")
        btn_open_cfg.setObjectName("ToggleButton"); btn_open_cfg.setProperty("active", True)
        btn_open_cfg.setCursor(Qt.PointingHandCursor); btn_open_cfg.setFixedHeight(38)
        btn_open_cfg.clicked.connect(lambda: _open_folder(_AUTOCLICKER_SETTINGS_FILE))
        sys_btn_row.addWidget(btn_open_cfg)
        sys_btn_row.addStretch(1)
        sys_lay.addLayout(sys_btn_row)
        sys_lay.addStretch(1)

        # --- Plugin manager card ---
        pl_card = Card()
        pl_card.setObjectName("ConfigCard")
        add_shadow(pl_card, blur=26, y=10, alpha=110)
        pl_lay = QVBoxLayout(pl_card)
        pl_lay.setContentsMargins(20, 18, 20, 18)
        pl_lay.setSpacing(12)

        ph = QHBoxLayout(); ph.setSpacing(10)
        pl_icon = QLabel("PL")
        pl_icon.setObjectName("HeaderIcon")
        pl_icon.setFixedSize(34, 34)
        pl_icon.setAlignment(Qt.AlignCenter)
        pl_title = QLabel("Plugin Manager")
        pl_title.setObjectName("CardHeader")
        ph.addWidget(pl_icon); ph.addWidget(pl_title); ph.addStretch(1)
        pl_lay.addLayout(ph)

        self.lbl_plugin_summary = QLabel("No plugin manager available.")
        self.lbl_plugin_summary.setObjectName("WarnText")
        self.lbl_plugin_summary.setWordWrap(True)
        pl_lay.addWidget(self.lbl_plugin_summary)

        self.lbl_plugin_rows = QLabel("")
        self.lbl_plugin_rows.setObjectName("WarnText")
        self.lbl_plugin_rows.setWordWrap(True)
        self.lbl_plugin_rows.setTextInteractionFlags(Qt.TextSelectableByMouse)
        pl_lay.addWidget(self.lbl_plugin_rows)

        pl_btn_row = QHBoxLayout(); pl_btn_row.setSpacing(10)
        self.btn_reload_plugins = QPushButton("Reload Plugins")
        self.btn_reload_plugins.setObjectName("ToggleButton")
        self.btn_reload_plugins.setProperty("active", True)
        self.btn_reload_plugins.setCursor(Qt.PointingHandCursor)
        self.btn_reload_plugins.setFixedHeight(38)
        self.btn_reload_plugins.clicked.connect(self._reload_plugins)
        pl_btn_row.addWidget(self.btn_reload_plugins)
        pl_btn_row.addStretch(1)
        pl_lay.addLayout(pl_btn_row)
        pl_lay.addStretch(1)

        # ─── Assemble layout ──────────────────────────
        lay.addWidget(hero)
        lay.addWidget(stats_card)
        lay.addWidget(xp_card)
        lay.addWidget(ach_card)
        lay.addWidget(sec_card)
        lay.addWidget(tm_card)
        lay.addWidget(pl_card)
        lay.addWidget(sys_card)
        lay.addWidget(danger_card)
        lay.addStretch(1)

        self._ach_checks: list[tuple[QCheckBox, str, str, bool]] = []

    def _make_spin_row(self, parent_lay: QVBoxLayout, label: str,
                       min_val: int, max_val: int) -> FocusClearSpinBox:
        row = QHBoxLayout()
        row.setSpacing(10)
        lbl = QLabel(label)
        lbl.setObjectName("TimeUnit")
        lbl.setFixedWidth(220)
        spin = FocusClearSpinBox()
        spin.setObjectName("TimeSpin")
        spin.setRange(min_val, max_val)
        spin.setFixedHeight(38)
        spin.setFixedWidth(160)
        spin.setAlignment(Qt.AlignCenter)
        row.addWidget(lbl)
        row.addWidget(spin)
        row.addStretch(1)
        parent_lay.addLayout(row)
        return spin

    def refresh(self):
        """Load current stats into the spin boxes and rebuild achievement checkboxes."""
        t = self.tracker
        self.spin_total_clicks.setValue(min(t.total_clicks, 999_999_999))
        self.spin_total_sessions.setValue(min(t.total_sessions, 999_999))
        self.spin_total_time.setValue(min(int(t.total_session_time), 99_999_999))
        self.spin_today.setValue(min(t.clicks_today(), 999_999_999))

        # XP
        self.spin_xp.setValue(min(t.xp, 999_999_999))
        self._preview_level(t.xp)

        # Secrets
        for chk, key in self._secret_checks:
            chk.setChecked(t.is_secret_unlocked(key))

        # Theme unlock checkboxes
        unlocked = get_unlocked_ids()
        for chk, tid in self._theme_checks:
            chk.setChecked(tid in unlocked or tid == "default")

        # Theme selector
        current = get_selected_theme_id()
        for i in range(self.combo_theme.count()):
            if self.combo_theme.itemData(i) == current:
                self.combo_theme.setCurrentIndex(i)
                break

        self._refresh_plugin_info()

        while self.ach_grid.count():
            item = self.ach_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._ach_checks.clear()
        achievements = t.get_achievements()
        for i, (icon, name, unlocked_ach) in enumerate(achievements):
            chk = QCheckBox(f"{icon}  {name}")
            chk.setChecked(unlocked_ach)
            chk.setStyleSheet(
                "QCheckBox { color: rgba(233,237,255,0.85); font-size: 12.5px; spacing: 8px; }"
                "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; "
                "border: 1px solid rgba(255,255,255,0.15); background: rgba(0,0,0,0.20); }"
                "QCheckBox::indicator:checked { background: rgba(78,141,255,0.50); "
                "border: 1px solid rgba(78,141,255,0.6); }"
            )
            row = i // 3
            col = i % 3
            self.ach_grid.addWidget(chk, row, col)
            self._ach_checks.append((chk, icon, name, unlocked_ach))

    def _apply_stats(self):
        """Write the spin box values back into the tracker."""
        t = self.tracker
        t._data["total_clicks"] = self.spin_total_clicks.value()
        t._data["total_sessions"] = self.spin_total_sessions.value()
        t._data["total_session_seconds"] = float(self.spin_total_time.value())

        today = datetime.now().strftime("%Y-%m-%d")
        t._data.setdefault("daily", {})[today] = self.spin_today.value()

        t.save()
        self.refresh()

    def _unlock_all(self):
        """Set stats high enough to unlock every achievement."""
        from datetime import timedelta
        t = self.tracker
        t._data["total_clicks"] = max(t._data.get("total_clicks", 0), 50_000_000)
        t._data["total_sessions"] = max(t._data.get("total_sessions", 0), 1_000)
        t._data["total_session_seconds"] = max(t._data.get("total_session_seconds", 0), 360_000)

        now = datetime.now()
        daily = t._data.setdefault("daily", {})

        # Set today to 100K (satisfies daily record achievements)
        today = now.strftime("%Y-%m-%d")
        daily[today] = max(daily.get(today, 0), 100_000)

        # Ensure 365-day history with at least 1 click per day (Active 365 Days + 30-Day Streak)
        for i in range(365):
            day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            daily[day] = max(daily.get(day, 0), 1)

        # Ensure this week has enough clicks (Week Warrior + Week Champion)
        start = now - timedelta(days=now.weekday())
        for i in range(7):
            day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            daily[day] = max(daily.get(day, 0), 5_000)

        # Ensure hourly coverage for Night Owl, Early Bird, High Noon, Golden Hour, Around the Clock
        hourly = t._data.setdefault("hourly", {})
        for h in range(24):
            key = f"{h:02d}"
            hourly[key] = max(hourly.get(key, 0), 1)

        # Ensure heatmap has enough points
        hm = t._data.setdefault("heatmap", [])
        while len(hm) < 500:
            hm.append([960, 540])

        # Set install date far enough back
        t._data["install_date"] = (now - timedelta(days=400)).isoformat()

        # Unlock all secrets
        for key in _SECRET_KEYS:
            t._data.setdefault("secrets", {})[key] = True

        # Unlock all themes including admin
        for theme in THEMES:
            mark_unlocked(theme["id"])

        t.save()
        self.refresh()
        self.theme_applied.emit()

    def _preview_level(self, xp_val: int):
        from app.services.stats_tracker import level_from_xp
        lv = level_from_xp(xp_val)
        self.lbl_level_preview.setText(f"Level: {lv}  (at {xp_val:,} XP)")

    def _apply_xp(self):
        self.tracker._data["xp"] = self.spin_xp.value()
        self.tracker.save()
        self.refresh()

    def _apply_secrets(self):
        for chk, key in self._secret_checks:
            self.tracker._data.setdefault("secrets", {})[key] = chk.isChecked()
        self.tracker.save()
        self.refresh()

    def _apply_theme_unlocks(self):
        """Sync theme unlock state from the checkboxes."""
        prefs = _load_theme_prefs()
        unlocked = set()
        unlocked.add("default")
        for chk, tid in self._theme_checks:
            if chk.isChecked():
                unlocked.add(tid)
        prefs["unlocked"] = list(unlocked)
        _save_theme_prefs(prefs)
        self.refresh()
        self.theme_applied.emit()

    def _apply_active_theme(self):
        """Set the currently selected theme from the combo box."""
        tid = self.combo_theme.currentData()
        if tid:
            # Make sure it's also unlocked
            mark_unlocked(tid)
            set_selected_theme_id(tid)
            self.refresh()
            self.theme_applied.emit()

    def _lock_all(self):
        """Reset stats to zero."""
        self._reset_all()

    def _reset_all(self):
        """Reset all stats to zero and clear theme unlocks."""
        t = self.tracker
        t._data["total_clicks"] = 0
        t._data["total_sessions"] = 0
        t._data["total_session_seconds"] = 0.0
        t._data["daily"] = {}
        t._data["hourly"] = {}
        t._data["heatmap"] = []
        t._data["install_date"] = datetime.now().isoformat()
        t.save()
        # Reset themes: clear all unlocks and revert to default
        _save_theme_prefs({"selected": "default", "unlocked": []})
        self.refresh()
        self.stats_reset.emit()

    def _reset_heatmap(self):
        """Clear only heatmap data."""
        self.tracker._data["heatmap"] = []
        self.tracker.save()
        self.refresh()

    def _reload_plugins(self):
        if self.plugin_manager is None:
            self._refresh_plugin_info()
            return
        self.plugin_manager.load_all()
        self._refresh_plugin_info()

    def _refresh_plugin_info(self):
        if self.plugin_manager is None:
            self.lbl_plugin_summary.setText("Plugin manager is not connected.")
            self.lbl_plugin_rows.setText("-")
            return

        records = self.plugin_manager.records()
        if not records:
            self.lbl_plugin_summary.setText("No plugins discovered in plugins/.")
            self.lbl_plugin_rows.setText("Drop .py plugin files into the workspace plugins folder.")
            return

        summary = self.plugin_manager.summary()
        self.lbl_plugin_summary.setText(
            f"Discovered: {summary['total']} | Loaded: {summary['loaded']} | Failed: {summary['failed']}"
        )

        lines: list[str] = []
        for rec in records:
            status = "OK" if rec.loaded else "ERR"
            line = f"[{status}] {rec.name} ({rec.version}) - {rec.file_path}"
            if rec.error and not rec.loaded:
                line += f"\n    {rec.error.splitlines()[0]}"
            lines.append(line)
        self.lbl_plugin_rows.setText("\n".join(lines))
