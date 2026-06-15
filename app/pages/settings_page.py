from __future__ import annotations

import json
import os
import sys
try:
    import winreg
except ImportError:
    winreg = None
try:
    import winsound
except ImportError:
    winsound = None

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QSlider, QComboBox, QCheckBox, QLineEdit, QGridLayout, QFileDialog,
)

from app.styling.localization import tr
from app.gui.widgets import Card, add_shadow, FocusClearSpinBox, ToastNotification
from app.styling.themes import (
    THEMES, THEME_MAP, get_theme, get_selected_theme_id, set_selected_theme_id,
    get_unlocked_ids, is_theme_unlocked,
)


SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".mtautoclicker_settings.json")


def _load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _show_save_error_toast(message: str):
    try:
        theme = get_theme()
        p = theme.get("palette", {})
        toast = ToastNotification(
            message,
            bg_color=p.get("config_card", "rgba(31,42,68,0.96)"),
            border_color=p.get("pill_active_border", "rgba(91,115,232,0.28)"),
            text_color=p.get("text_primary", "#E9EDFF"),
            icon="⚠",
            parent=QApplication.activeWindow() if QApplication.instance() else None,
        )
        toast.show_toast()
    except Exception as exc:
        print(f"[Settings] Failed to show error toast: {exc}", file=sys.stderr)


def _save_settings(data: dict) -> bool:
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as exc:
        print(f"[Settings] Failed to save settings: {exc}", file=sys.stderr)
        _show_save_error_toast("Couldn't save settings. Check file permissions.")
        return False


class SettingsPage(QWidget):
    """Settings: sounds, jitter, delayed start, per-click sound, startup, language."""

    jitter_changed = pyqtSignal(int)
    delay_changed = pyqtSignal(int)
    sound_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    scroll_key_changed = pyqtSignal(str)
    scroll_as_changed = pyqtSignal(bool, str)  # (enabled, key)
    overlay_toggled = pyqtSignal(bool)  # compact overlay on/off
    theme_changed = pyqtSignal(str)
    emergency_key_changed = pyqtSignal(str)
    performance_mode_changed = pyqtSignal(bool)
    scroll_hotkey_enabled_changed = pyqtSignal(bool)
    switch_mouse_button_key_changed = pyqtSignal(str)
    toggle_both_mouse_key_changed = pyqtSignal(str)
    topbar_action_changed = pyqtSignal(str)
    sidebar_config_changed = pyqtSignal(dict)

    SOUND_OPTIONS = [
        ("None", ""),
        ("Default Beep", "beep"),
        ("Ding", "ding"),
        ("Chirp", "chirp"),
        ("Alert", "alert"),
        ("Soft Click", "soft_click"),
        ("Pulse", "pulse"),
        ("Arcade", "arcade"),
        ("Custom File (.wav)", "custom"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = _load_settings()
        defaults = {
            "sound": "beep",
            "custom_start_sound": "",
            "per_click_sound": False,
            "jitter_ms": 0,
            "delay_ms": 0,
            "delay_unit": "milliseconds",
            "advanced_tab": "function",
            "compact_overlay": False,
            "lock_to_window": True,
            "blocked_programs_enabled": False,
            "blocked_programs": "",
            "edge_stop_enabled": False,
            "edge_stop_margin_px": 6,
            "corner_stop_enabled": True,
            "corner_stop_size_px": 20,
            "lag_guard_enabled": False,
            "lag_guard_threshold": 65,
            "lag_guard_events": 6,
            "low_interval_warning_enabled": True,
            "scroll_key": "",
            "scroll_hotkey_enabled": True,
            "scroll_as_enabled": False,
            "scroll_as_key": "right click",
            "emergency_key": "z",
            "switch_mouse_button_key": "",
            "toggle_both_mouse_key": "",
            "performance_mode": False,
            "language": "en",
            "tray_minimize": True,
            "color_trigger_enabled": False,
            "color_trigger_x": 0,
            "color_trigger_y": 0,
            "color_trigger_r": 255,
            "color_trigger_g": 0,
            "color_trigger_b": 0,
            "color_trigger_tolerance": 12,
            "topbar_action": "search",
            "sidebar_basic_mode": False,
            "sidebar_order": "home,preset,settings,stats,achievements,projects,help",
            "sidebar_show_stats": True,
            "sidebar_show_achievements": True,
            "sidebar_show_projects": True,
            "sidebar_show_help": True,
            "startup_enabled": self._is_startup_enabled(),
            "disable_toasts": True,
            "selected_theme": get_selected_theme_id(),
        }
        for key, value in defaults.items():
            self._settings.setdefault(key, value)
        if self._settings.get("selected_theme"):
            set_selected_theme_id(str(self._settings.get("selected_theme", "default")))
        _save_settings(self._settings)
        self._capture_target = ""
        self._custom_start_sound = self._settings.get("custom_start_sound", "")

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
        self.hero_title = QLabel(tr("settings_title"))
        self.hero_title.setObjectName("HeroTitle")
        self.hero_sub = QLabel(tr("settings_sub"))
        self.hero_sub.setObjectName("HeroSub")
        hl.addWidget(self.hero_title)
        hl.addWidget(self.hero_sub)
        hl.addStretch(1)

        # Cards row
        row = QHBoxLayout()
        row.setSpacing(14)

        # --- Sound card ---
        sound_card = Card()
        sound_card.setObjectName("ConfigCard")
        add_shadow(sound_card, blur=26, y=10, alpha=110)
        sc_lay = QVBoxLayout(sound_card)
        sc_lay.setContentsMargins(20, 18, 20, 18)
        sc_lay.setSpacing(14)

        sh = QHBoxLayout()
        sh.setSpacing(10)
        si = QLabel("🔊")
        si.setObjectName("HeaderIcon")
        si.setFixedSize(34, 34)
        si.setAlignment(Qt.AlignCenter)
        self.lbl_sound_header = QLabel(tr("sound_effects"))
        self.lbl_sound_header.setObjectName("CardHeader")
        sh.addWidget(si)
        sh.addWidget(self.lbl_sound_header)
        sh.addStretch(1)
        sc_lay.addLayout(sh)

        inner_sound = Card(radius=16)
        inner_sound.setObjectName("InnerPanel")
        is_lay = QVBoxLayout(inner_sound)
        is_lay.setContentsMargins(14, 14, 14, 14)
        is_lay.setSpacing(8)

        self.lbl_start_stop_sound = QLabel(tr("start_stop_sound"))
        self.lbl_start_stop_sound.setObjectName("InnerTitle")
        is_lay.addWidget(self.lbl_start_stop_sound)

        saved_sound = self._settings.get("sound", "beep")
        self.sound_buttons = []
        for name, key in self.SOUND_OPTIONS:
            btn = QPushButton(f"{'●' if key == saved_sound or (key == '' and saved_sound == '') else '○'}   {name}")
            btn.setObjectName("ToggleButton")
            btn.setFlat(True)
            btn.setProperty("active", key == saved_sound or (key == "" and saved_sound == ""))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, k=key: self._select_sound(k))
            is_lay.addWidget(btn)
            self.sound_buttons.append((btn, key))

        self.btn_preview = QPushButton(tr("preview_sound"))
        self.btn_preview.setObjectName("ToggleButton")
        self.btn_preview.setFlat(True)
        self.btn_preview.setProperty("active", False)
        self.btn_preview.setCursor(Qt.PointingHandCursor)
        self.btn_preview.setFixedHeight(36)
        self.btn_preview.clicked.connect(self._preview_sound)
        is_lay.addWidget(self.btn_preview)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        self.btn_choose_custom_sound = QPushButton("Choose Custom Sound")
        self.btn_choose_custom_sound.setObjectName("ToggleButton")
        self.btn_choose_custom_sound.setFlat(True)
        self.btn_choose_custom_sound.setProperty("active", False)
        self.btn_choose_custom_sound.setCursor(Qt.PointingHandCursor)
        self.btn_choose_custom_sound.setFixedHeight(34)
        self.btn_choose_custom_sound.clicked.connect(self._choose_custom_sound)

        self.btn_clear_custom_sound = QPushButton("Clear Custom")
        self.btn_clear_custom_sound.setObjectName("ToggleButton")
        self.btn_clear_custom_sound.setFlat(True)
        self.btn_clear_custom_sound.setProperty("active", False)
        self.btn_clear_custom_sound.setCursor(Qt.PointingHandCursor)
        self.btn_clear_custom_sound.setFixedHeight(34)
        self.btn_clear_custom_sound.clicked.connect(self._clear_custom_sound)

        custom_row.addWidget(self.btn_choose_custom_sound, 1)
        custom_row.addWidget(self.btn_clear_custom_sound)
        is_lay.addLayout(custom_row)

        self.lbl_custom_sound = QLabel(self._custom_sound_label())
        self.lbl_custom_sound.setObjectName("WarnText")
        self.lbl_custom_sound.setWordWrap(True)
        is_lay.addWidget(self.lbl_custom_sound)

        self.chk_per_click = QCheckBox(tr("per_click_desc"))
        self.chk_per_click.setChecked(self._settings.get("per_click_sound", False))
        self.chk_per_click.setStyleSheet("")
        self.chk_per_click.stateChanged.connect(self._on_per_click_changed)
        is_lay.addWidget(self.chk_per_click)

        is_lay.addStretch(1)
        sc_lay.addWidget(inner_sound)
        sc_lay.addStretch(1)

        # --- Jitter + Delay card ---
        jd_card = Card()
        jd_card.setObjectName("ConfigCard")
        add_shadow(jd_card, blur=26, y=10, alpha=110)
        jd_lay = QVBoxLayout(jd_card)
        jd_lay.setContentsMargins(20, 18, 20, 18)
        jd_lay.setSpacing(14)

        jdh = QHBoxLayout()
        jdh.setSpacing(10)
        jdi = QLabel("🎛")
        jdi.setObjectName("HeaderIcon")
        jdi.setFixedSize(34, 34)
        jdi.setAlignment(Qt.AlignCenter)
        self.lbl_advanced_header = QLabel(tr("advanced"))
        self.lbl_advanced_header.setObjectName("CardHeader")
        jdh.addWidget(jdi)
        jdh.addWidget(self.lbl_advanced_header)
        jdh.addStretch(1)
        jd_lay.addLayout(jdh)

        inner_jd = Card(radius=16)
        inner_jd.setObjectName("InnerPanel")
        ij_lay = QVBoxLayout(inner_jd)
        ij_lay.setContentsMargins(14, 14, 14, 14)
        ij_lay.setSpacing(12)

        self.lbl_section_general = QLabel("General")
        self.lbl_section_general.setObjectName("CardHeader")
        ij_lay.addWidget(self.lbl_section_general)

        self.lbl_adv_sections = QLabel("Advanced Sections")
        self.lbl_adv_sections.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_adv_sections)

        adv_tabs = QHBoxLayout()
        adv_tabs.setSpacing(8)
        self.btn_adv_function = QPushButton("Function")
        self.btn_adv_keybinds = QPushButton("Keybinds")
        self.btn_adv_cosmetics = QPushButton("Cosmetics")
        for b in (self.btn_adv_function, self.btn_adv_keybinds, self.btn_adv_cosmetics):
            b.setObjectName("ToggleButton")
            b.setFlat(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(34)
            b.setProperty("active", False)
            adv_tabs.addWidget(b)
        adv_tabs.addStretch(1)
        ij_lay.addLayout(adv_tabs)

        self.btn_adv_function.clicked.connect(lambda: self._set_advanced_tab("function"))
        self.btn_adv_keybinds.clicked.connect(lambda: self._set_advanced_tab("keybinds"))
        self.btn_adv_cosmetics.clicked.connect(lambda: self._set_advanced_tab("cosmetics"))
        self._adv_tab = str(self._settings.get("advanced_tab", "function"))

        # Jitter slider
        self.lbl_jitter_title = QLabel(tr("random_jitter"))
        self.lbl_jitter_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_jitter_title)

        jitter_row = QHBoxLayout()
        jitter_row.setSpacing(10)
        self.jitter_slider = QSlider(Qt.Horizontal)
        self.jitter_slider.setRange(0, 500)
        self.jitter_slider.setValue(self._settings.get("jitter_ms", 0))
        self.jitter_slider.setObjectName("Slider")
        self.lbl_jitter_val = QLabel(f"{self.jitter_slider.value()} ms")
        self.lbl_jitter_val.setObjectName("TimeUnit")
        self.lbl_jitter_val.setFixedWidth(60)
        self.jitter_slider.valueChanged.connect(self._on_jitter_changed)
        jitter_row.addWidget(self.jitter_slider, 1)
        jitter_row.addWidget(self.lbl_jitter_val)
        ij_lay.addLayout(jitter_row)

        self.lbl_jitter_desc = QLabel(tr("jitter_desc"))
        self.lbl_jitter_desc.setObjectName("WarnText")
        self.lbl_jitter_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_jitter_desc)

        # Separator
        self.sep_general_1 = QFrame()
        self.sep_general_1.setObjectName("SettingsSeparator")
        self.sep_general_1.setFixedHeight(1)
        ij_lay.addWidget(self.sep_general_1)

        # Delayed start
        self.lbl_delay_title = QLabel(tr("delayed_start"))
        self.lbl_delay_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_delay_title)

        delay_row = QHBoxLayout()
        delay_row.setSpacing(10)
        self.spin_delay = FocusClearSpinBox()
        self.spin_delay.setObjectName("TimeSpin")
        self.spin_delay.setRange(0, 60000)
        self.spin_delay.setValue(self._settings.get("delay_ms", 0))
        self.spin_delay.setFixedHeight(40)
        self.spin_delay.valueChanged.connect(self._on_delay_changed)
        self.delay_unit = QComboBox()
        self.delay_unit.setObjectName("UnitDrop")
        self.delay_unit.addItems(["Milliseconds", "Seconds"])
        self.delay_unit.setFixedHeight(40)
        saved_delay_unit = str(self._settings.get("delay_unit", "milliseconds")).strip().lower()
        self.delay_unit.setCurrentIndex(1 if saved_delay_unit in ("sec", "second", "seconds", "1") else 0)
        self.delay_unit.currentIndexChanged.connect(self._on_delay_unit_changed)
        delay_row.addWidget(self.spin_delay, 1)
        delay_row.addWidget(self.delay_unit, 1)
        ij_lay.addLayout(delay_row)

        self.lbl_delay_desc = QLabel(tr("delay_desc"))
        self.lbl_delay_desc.setObjectName("WarnText")
        self.lbl_delay_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_delay_desc)

        # Separator
        self.sep_general_2 = QFrame()
        self.sep_general_2.setObjectName("SettingsSeparator")
        self.sep_general_2.setFixedHeight(1)
        ij_lay.addWidget(self.sep_general_2)

        # Startup with Windows
        self.lbl_startup_title = QLabel(tr("startup_windows"))
        self.lbl_startup_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_startup_title)
        self.chk_startup = QCheckBox(tr("startup_desc"))
        startup_enabled = bool(self._settings.get("startup_enabled", self._is_startup_enabled()))
        self.chk_startup.setChecked(startup_enabled)
        self.chk_startup.setStyleSheet("")
        self.chk_startup.stateChanged.connect(self._on_startup_changed)
        self._apply_startup_enabled(startup_enabled)
        ij_lay.addWidget(self.chk_startup)

        # Disable Toasts (global)
        self.chk_disable_toasts = QCheckBox("Disable Toasts")
        self.chk_disable_toasts.setChecked(bool(self._settings.get("disable_toasts", True)))
        self.chk_disable_toasts.stateChanged.connect(self._on_disable_toasts_changed)
        ij_lay.addWidget(self.chk_disable_toasts)

        # Separator
        self.sep_general_3 = QFrame()
        self.sep_general_3.setObjectName("SettingsSeparator")
        self.sep_general_3.setFixedHeight(1)
        ij_lay.addWidget(self.sep_general_3)

        # Language selector
        self.lbl_lang_title = QLabel(tr("language"))
        self.lbl_lang_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_lang_title)
        self.combo_lang = QComboBox()
        self.combo_lang.setObjectName("UnitDrop")
        self.combo_lang.addItems(["English", "Deutsch", "Fran\u00e7ais", "Espa\u00f1ol"])
        lang_map_load = {"en": 0, "de": 1, "fr": 2, "es": 3}
        self.combo_lang.setCurrentIndex(lang_map_load.get(self._settings.get("language", "en"), 0))
        self.combo_lang.setFixedHeight(40)
        self.combo_lang.currentIndexChanged.connect(self._on_language_changed)
        ij_lay.addWidget(self.combo_lang)

        # Separator
        self.sep_top_action = QFrame()
        self.sep_top_action.setObjectName("SettingsSeparator")
        self.sep_top_action.setFixedHeight(1)
        ij_lay.addWidget(self.sep_top_action)

        self.lbl_topbar_action_title = QLabel("Top Search Button Action")
        self.lbl_topbar_action_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_topbar_action_title)
        self.combo_topbar_action = QComboBox()
        self.combo_topbar_action.setObjectName("UnitDrop")
        self.combo_topbar_action.addItems([
            "Search",
            "Open Helldivers",
            "Open Support Hub",
            "Open Projects",
            "Open Marketplace",
            "Open About",
            "Toggle Autoclicker",
            "Open Workflow Studio",
        ])
        top_action_map = {
            "search": 0,
            "helldivers": 1,
            "support": 2,
            "projects": 3,
            "marketplace": 4,
            "about": 5,
            "toggle": 6,
            "workflow": 7,
        }
        self.combo_topbar_action.setCurrentIndex(top_action_map.get(self._settings.get("topbar_action", "search"), 0))
        self.combo_topbar_action.setFixedHeight(40)
        self.combo_topbar_action.currentIndexChanged.connect(self._on_topbar_action_changed)
        ij_lay.addWidget(self.combo_topbar_action)

        # Separator
        self.sep_sidebar = QFrame()
        self.sep_sidebar.setObjectName("SettingsSeparator")
        self.sep_sidebar.setFixedHeight(1)
        ij_lay.addWidget(self.sep_sidebar)

        # Sidebar customization
        self.lbl_sidebar_title = QLabel("Sidebar Layout")
        self.lbl_sidebar_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_sidebar_title)

        self.chk_sidebar_basic = QCheckBox("Simplify sidebar to basics only")
        self.chk_sidebar_basic.setChecked(bool(self._settings.get("sidebar_basic_mode", False)))
        self.chk_sidebar_basic.stateChanged.connect(self._on_sidebar_config_changed)
        ij_lay.addWidget(self.chk_sidebar_basic)

        self.chk_sidebar_stats = QCheckBox("Show Stats")
        self.chk_sidebar_stats.setChecked(bool(self._settings.get("sidebar_show_stats", True)))
        self.chk_sidebar_stats.stateChanged.connect(self._on_sidebar_config_changed)
        ij_lay.addWidget(self.chk_sidebar_stats)

        self.chk_sidebar_achievements = QCheckBox("Show Achievements")
        self.chk_sidebar_achievements.setChecked(bool(self._settings.get("sidebar_show_achievements", True)))
        self.chk_sidebar_achievements.stateChanged.connect(self._on_sidebar_config_changed)
        ij_lay.addWidget(self.chk_sidebar_achievements)

        self.chk_sidebar_projects = QCheckBox("Show Projects")
        self.chk_sidebar_projects.setChecked(bool(self._settings.get("sidebar_show_projects", True)))
        self.chk_sidebar_projects.stateChanged.connect(self._on_sidebar_config_changed)
        ij_lay.addWidget(self.chk_sidebar_projects)

        self.chk_sidebar_help = QCheckBox("Show Help Center")
        self.chk_sidebar_help.setChecked(bool(self._settings.get("sidebar_show_help", True)))
        self.chk_sidebar_help.stateChanged.connect(self._on_sidebar_config_changed)
        ij_lay.addWidget(self.chk_sidebar_help)

        self.lbl_sidebar_order = QLabel("Sidebar order (comma separated)")
        self.lbl_sidebar_order.setObjectName("WarnText")
        ij_lay.addWidget(self.lbl_sidebar_order)

        self.input_sidebar_order = QLineEdit()
        self.input_sidebar_order.setPlaceholderText("home,preset,settings,stats,achievements,projects,help")
        self.input_sidebar_order.setText(str(self._settings.get("sidebar_order", "home,preset,settings,stats,achievements,projects,help")))
        self.input_sidebar_order.editingFinished.connect(self._on_sidebar_config_changed)
        ij_lay.addWidget(self.input_sidebar_order)

        # Separator
        sep4 = QFrame()
        sep4.setObjectName("SettingsSeparator")
        sep4.setFixedHeight(1)
        ij_lay.addWidget(sep4)

        self.lbl_section_hotkeys = QLabel("Hotkeys")
        self.lbl_section_hotkeys.setObjectName("CardHeader")
        ij_lay.addWidget(self.lbl_section_hotkeys)

        # Scroll keybind
        self.lbl_scroll_key_title = QLabel(tr("scroll_keybind"))
        self.lbl_scroll_key_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_scroll_key_title)
        scroll_key_row = QHBoxLayout()
        scroll_key_row.setSpacing(10)
        self._scroll_key = self._settings.get("scroll_key", "")
        self.btn_scroll_key = QPushButton(
            self._format_keybind_label(self._scroll_key)
        )
        self.btn_scroll_key.setObjectName("ToggleButton")
        self.btn_scroll_key.setFlat(True)
        self.btn_scroll_key.setProperty("active", bool(self._scroll_key))
        self.btn_scroll_key.setCursor(Qt.PointingHandCursor)
        self.btn_scroll_key.setFixedHeight(40)
        self.btn_scroll_key.setMinimumWidth(80)
        self.btn_scroll_key.clicked.connect(self._on_scroll_key_click)
        self.btn_clear_scroll_key = QPushButton("Clear")
        self.btn_clear_scroll_key.setObjectName("ToggleButton")
        self.btn_clear_scroll_key.setFlat(True)
        self.btn_clear_scroll_key.setProperty("active", False)
        self.btn_clear_scroll_key.setCursor(Qt.PointingHandCursor)
        self.btn_clear_scroll_key.setFixedHeight(40)
        self.btn_clear_scroll_key.clicked.connect(self._clear_scroll_key)
        scroll_key_row.addWidget(self.btn_scroll_key, 1)
        scroll_key_row.addWidget(self.btn_clear_scroll_key)
        ij_lay.addLayout(scroll_key_row)
        self.lbl_scroll_key_desc = QLabel(tr("scroll_keybind_desc"))
        self.lbl_scroll_key_desc.setObjectName("WarnText")
        self.lbl_scroll_key_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_scroll_key_desc)
        self.chk_scroll_hotkey_enabled = QCheckBox("Enable scroll keybind")
        self.chk_scroll_hotkey_enabled.setChecked(self._settings.get("scroll_hotkey_enabled", True))
        self.chk_scroll_hotkey_enabled.setStyleSheet("")
        self.chk_scroll_hotkey_enabled.stateChanged.connect(self._on_scroll_hotkey_enabled_changed)
        ij_lay.addWidget(self.chk_scroll_hotkey_enabled)
        self._waiting_scroll_key = False

        # Separator
        self.sep_hotkey_1 = QFrame()
        self.sep_hotkey_1.setObjectName("SettingsSeparator")
        self.sep_hotkey_1.setFixedHeight(1)
        ij_lay.addWidget(self.sep_hotkey_1)

        # Scroll interpreted as key
        self.lbl_scroll_as_title = QLabel("Scroll as Key")
        self.lbl_scroll_as_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_scroll_as_title)

        scroll_as_row = QHBoxLayout()
        scroll_as_row.setSpacing(10)

        self.chk_scroll_as = QCheckBox("Interpret mouse scroll as key press")
        self.chk_scroll_as.setChecked(self._settings.get("scroll_as_enabled", False))
        self.chk_scroll_as.setStyleSheet("")
        self.chk_scroll_as.stateChanged.connect(self._on_scroll_as_changed)

        self._scroll_as_key = self._settings.get("scroll_as_key", "right click")
        self.btn_scroll_as_key = QPushButton(self._format_keybind_label(self._scroll_as_key, "Right Click"))
        self.btn_scroll_as_key.setObjectName("ToggleButton")
        self.btn_scroll_as_key.setFlat(True)
        self.btn_scroll_as_key.setProperty("active", bool(self._scroll_as_key))
        self.btn_scroll_as_key.setCursor(Qt.PointingHandCursor)
        self.btn_scroll_as_key.setFixedHeight(40)
        self.btn_scroll_as_key.setMinimumWidth(100)
        self.btn_scroll_as_key.clicked.connect(self._on_scroll_as_key_click)
        self._waiting_scroll_as_key = False

        scroll_as_row.addWidget(self.chk_scroll_as, 1)
        scroll_as_row.addWidget(self.btn_scroll_as_key)
        ij_lay.addLayout(scroll_as_row)

        self.lbl_scroll_as_desc = QLabel("When enabled, scrolling the mouse wheel triggers the chosen key instead.")
        self.lbl_scroll_as_desc.setObjectName("WarnText")
        self.lbl_scroll_as_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_scroll_as_desc)

        # Compact Overlay toggle
        self.sep_hotkey_2 = QFrame()
        self.sep_hotkey_2.setObjectName("SettingsSeparator")
        self.sep_hotkey_2.setFixedHeight(1)
        ij_lay.addWidget(self.sep_hotkey_2)

        self.lbl_overlay_title = QLabel("Compact Overlay")
        self.lbl_overlay_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_overlay_title)

        self.chk_overlay = QCheckBox("Show floating overlay with live CPS")
        self.chk_overlay.setChecked(self._settings.get("compact_overlay", False))
        self.chk_overlay.setStyleSheet("")
        self.chk_overlay.stateChanged.connect(
            lambda st: self.overlay_toggled.emit(st == Qt.Checked)
        )
        ij_lay.addWidget(self.chk_overlay)

        self.chk_tray_minimize = QCheckBox("Minimize to system tray (hide window when minimized)")
        self.chk_tray_minimize.setChecked(self._settings.get("tray_minimize", True))
        self.chk_tray_minimize.stateChanged.connect(self._on_tray_minimize_changed)
        ij_lay.addWidget(self.chk_tray_minimize)

        self.lbl_overlay_desc = QLabel("A tiny draggable window that stays on top showing CPS and start/stop.")
        self.lbl_overlay_desc.setObjectName("WarnText")
        self.lbl_overlay_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_overlay_desc)

        # Lock to focused window
        self.sep_safety_1 = QFrame()
        self.sep_safety_1.setObjectName("SettingsSeparator")
        self.sep_safety_1.setFixedHeight(1)
        ij_lay.addWidget(self.sep_safety_1)

        self.lbl_section_safety = QLabel("Safety")
        self.lbl_section_safety.setObjectName("CardHeader")
        ij_lay.addWidget(self.lbl_section_safety)

        self.lbl_lock_window_title = QLabel("Lock to Focused Window")
        self.lbl_lock_window_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_lock_window_title)

        self.chk_lock_window = QCheckBox("Only click when target window is focused")
        self.chk_lock_window.setChecked(self._settings.get("lock_to_window", True))
        self.chk_lock_window.setStyleSheet("")
        self.chk_lock_window.stateChanged.connect(self._on_lock_window_changed)
        ij_lay.addWidget(self.chk_lock_window)

        self.lbl_lock_window_desc = QLabel(
            "When enabled, the autoclicker captures the focused window at start "
            "and pauses clicking whenever you switch to a different window."
        )
        self.lbl_lock_window_desc.setObjectName("WarnText")
        self.lbl_lock_window_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_lock_window_desc)

        self.chk_blocked_programs = QCheckBox("Block when selected programs are focused")
        self.chk_blocked_programs.setChecked(self._settings.get("blocked_programs_enabled", False))
        self.chk_blocked_programs.setStyleSheet("")
        self.chk_blocked_programs.stateChanged.connect(self._on_blocked_programs_changed)
        ij_lay.addWidget(self.chk_blocked_programs)

        self.input_blocked_programs = QLineEdit()
        self.input_blocked_programs.setPlaceholderText("e.g. valorant.exe, cs2.exe, notepad.exe")
        self.input_blocked_programs.setText(self._settings.get("blocked_programs", ""))
        self.input_blocked_programs.editingFinished.connect(self._on_blocked_programs_changed)
        ij_lay.addWidget(self.input_blocked_programs)

        self.lbl_blocked_programs_desc = QLabel(
            "When enabled, start/toggle is blocked if the active foreground app matches this list."
        )
        self.lbl_blocked_programs_desc.setObjectName("WarnText")
        self.lbl_blocked_programs_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_blocked_programs_desc)

        self.sep_safety_edge = QFrame()
        self.sep_safety_edge.setObjectName("SettingsSeparator")
        self.sep_safety_edge.setFixedHeight(1)
        ij_lay.addWidget(self.sep_safety_edge)

        self.lbl_edge_stop_title = QLabel("Edge Stop Failsafe")
        self.lbl_edge_stop_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_edge_stop_title)

        self.chk_edge_stop = QCheckBox("Auto-stop when cursor reaches screen edge zone")
        self.chk_edge_stop.setChecked(self._settings.get("edge_stop_enabled", False))
        self.chk_edge_stop.setStyleSheet("")
        self.chk_edge_stop.stateChanged.connect(self._on_edge_corner_stop_changed)
        ij_lay.addWidget(self.chk_edge_stop)

        edge_row = QHBoxLayout()
        edge_row.setSpacing(10)
        self.lbl_edge_margin = QLabel("Edge zone (px)")
        self.spin_edge_margin = FocusClearSpinBox()
        self.spin_edge_margin.setObjectName("TimeSpin")
        self.spin_edge_margin.setRange(1, 80)
        self.spin_edge_margin.setValue(int(self._settings.get("edge_stop_margin_px", 6)))
        self.spin_edge_margin.setFixedHeight(36)
        self.spin_edge_margin.valueChanged.connect(self._on_edge_corner_stop_changed)
        edge_row.addWidget(self.lbl_edge_margin)
        edge_row.addWidget(self.spin_edge_margin)
        edge_row.addStretch(1)
        ij_lay.addLayout(edge_row)

        self.lbl_edge_stop_desc = QLabel("Stops clicking if the cursor touches any screen edge within this zone.")
        self.lbl_edge_stop_desc.setObjectName("WarnText")
        self.lbl_edge_stop_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_edge_stop_desc)

        self.sep_safety_corner = QFrame()
        self.sep_safety_corner.setObjectName("SettingsSeparator")
        self.sep_safety_corner.setFixedHeight(1)
        ij_lay.addWidget(self.sep_safety_corner)

        self.lbl_corner_stop_title = QLabel("Corner Stop Failsafe")
        self.lbl_corner_stop_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_corner_stop_title)

        self.chk_corner_stop = QCheckBox("Auto-stop when cursor enters a corner box")
        self.chk_corner_stop.setChecked(self._settings.get("corner_stop_enabled", True))
        self.chk_corner_stop.setStyleSheet("")
        self.chk_corner_stop.stateChanged.connect(self._on_edge_corner_stop_changed)
        ij_lay.addWidget(self.chk_corner_stop)

        corner_row = QHBoxLayout()
        corner_row.setSpacing(10)
        self.lbl_corner_size = QLabel("Corner box (px)")
        self.spin_corner_size = FocusClearSpinBox()
        self.spin_corner_size.setObjectName("TimeSpin")
        self.spin_corner_size.setRange(4, 140)
        self.spin_corner_size.setValue(int(self._settings.get("corner_stop_size_px", 20)))
        self.spin_corner_size.setFixedHeight(36)
        self.spin_corner_size.valueChanged.connect(self._on_edge_corner_stop_changed)
        corner_row.addWidget(self.lbl_corner_size)
        corner_row.addWidget(self.spin_corner_size)
        corner_row.addStretch(1)
        ij_lay.addLayout(corner_row)

        self.lbl_corner_stop_desc = QLabel("Stops clicking if the cursor enters any screen corner box.")
        self.lbl_corner_stop_desc.setObjectName("WarnText")
        self.lbl_corner_stop_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_corner_stop_desc)

        self.sep_color_trigger = QFrame()
        self.sep_color_trigger.setObjectName("SettingsSeparator")
        self.sep_color_trigger.setFixedHeight(1)
        ij_lay.addWidget(self.sep_color_trigger)

        self.lbl_color_trigger_title = QLabel("Color / Pixel Trigger")
        self.lbl_color_trigger_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_color_trigger_title)

        self.chk_color_trigger = QCheckBox("Auto-stop when pixel at X,Y matches RGB (± tolerance)")
        self.chk_color_trigger.setChecked(self._settings.get("color_trigger_enabled", False))
        self.chk_color_trigger.stateChanged.connect(self._on_color_trigger_changed)
        ij_lay.addWidget(self.chk_color_trigger)

        color_grid = QGridLayout()
        color_grid.setHorizontalSpacing(8)
        color_grid.setVerticalSpacing(6)
        self.spin_color_x = FocusClearSpinBox()
        self.spin_color_y = FocusClearSpinBox()
        self.spin_color_r = FocusClearSpinBox()
        self.spin_color_g = FocusClearSpinBox()
        self.spin_color_b = FocusClearSpinBox()
        self.spin_color_tol = FocusClearSpinBox()
        for spin, val, hi in (
            (self.spin_color_x, self._settings.get("color_trigger_x", 0), 9999),
            (self.spin_color_y, self._settings.get("color_trigger_y", 0), 9999),
            (self.spin_color_r, self._settings.get("color_trigger_r", 255), 255),
            (self.spin_color_g, self._settings.get("color_trigger_g", 0), 255),
            (self.spin_color_b, self._settings.get("color_trigger_b", 0), 255),
            (self.spin_color_tol, self._settings.get("color_trigger_tolerance", 12), 64),
        ):
            spin.setObjectName("TimeSpin")
            spin.setRange(0, hi)
            spin.setValue(int(val))
            spin.setFixedHeight(34)
            spin.valueChanged.connect(self._on_color_trigger_changed)
        labels = ("X", "Y", "R", "G", "B", "Tol")
        spins = (
            self.spin_color_x, self.spin_color_y, self.spin_color_r,
            self.spin_color_g, self.spin_color_b, self.spin_color_tol,
        )
        for col, (lbl, spin) in enumerate(zip(labels, spins)):
            color_grid.addWidget(QLabel(lbl), 0, col)
            color_grid.addWidget(spin, 1, col)
        ij_lay.addLayout(color_grid)

        self.lbl_color_trigger_desc = QLabel("Useful for stopping when a UI element changes color. Checked each click cycle.")
        self.lbl_color_trigger_desc.setObjectName("WarnText")
        self.lbl_color_trigger_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_color_trigger_desc)

        # Separator
        self.sep_hotkey_3 = QFrame()
        self.sep_hotkey_3.setObjectName("SettingsSeparator")
        self.sep_hotkey_3.setFixedHeight(1)
        ij_lay.addWidget(self.sep_hotkey_3)

        # Emergency stop key
        self.lbl_emergency_title = QLabel("Emergency Stop Key")
        self.lbl_emergency_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_emergency_title)

        emg_row = QHBoxLayout()
        emg_row.setSpacing(10)
        self._emergency_key = self._settings.get("emergency_key", "z")
        self.btn_emergency_key = QPushButton(self._format_keybind_label(self._emergency_key))
        self.btn_emergency_key.setObjectName("ToggleButton")
        self.btn_emergency_key.setFlat(True)
        self.btn_emergency_key.setProperty("active", bool(self._emergency_key))
        self.btn_emergency_key.setCursor(Qt.PointingHandCursor)
        self.btn_emergency_key.setFixedHeight(40)
        self.btn_emergency_key.clicked.connect(self._on_emergency_key_click)

        self.btn_clear_emergency = QPushButton("Clear")
        self.btn_clear_emergency.setObjectName("ToggleButton")
        self.btn_clear_emergency.setFlat(True)
        self.btn_clear_emergency.setProperty("active", False)
        self.btn_clear_emergency.setCursor(Qt.PointingHandCursor)
        self.btn_clear_emergency.setFixedHeight(40)
        self.btn_clear_emergency.clicked.connect(self._clear_emergency_key)
        emg_row.addWidget(self.btn_emergency_key, 1)
        emg_row.addWidget(self.btn_clear_emergency)
        ij_lay.addLayout(emg_row)

        self.lbl_emergency_desc = QLabel("Instantly stops all automation regardless of active page.")
        self.lbl_emergency_desc.setObjectName("WarnText")
        self.lbl_emergency_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_emergency_desc)
        self._waiting_emergency_key = False

        # Separator
        self.sep_hotkey_4 = QFrame()
        self.sep_hotkey_4.setObjectName("SettingsSeparator")
        self.sep_hotkey_4.setFixedHeight(1)
        ij_lay.addWidget(self.sep_hotkey_4)

        # Quick mouse swap key
        self.lbl_switch_mouse_title = QLabel("Switch Left/Right Key")
        self.lbl_switch_mouse_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_switch_mouse_title)

        switch_row = QHBoxLayout()
        switch_row.setSpacing(10)
        self._switch_mouse_button_key = self._settings.get("switch_mouse_button_key", "")
        self.btn_switch_mouse_key = QPushButton(self._format_keybind_label(self._switch_mouse_button_key))
        self.btn_switch_mouse_key.setObjectName("ToggleButton")
        self.btn_switch_mouse_key.setFlat(True)
        self.btn_switch_mouse_key.setProperty("active", bool(self._switch_mouse_button_key))
        self.btn_switch_mouse_key.setCursor(Qt.PointingHandCursor)
        self.btn_switch_mouse_key.setFixedHeight(40)
        self.btn_switch_mouse_key.clicked.connect(self._on_switch_mouse_key_click)

        self.btn_clear_switch_mouse_key = QPushButton("Clear")
        self.btn_clear_switch_mouse_key.setObjectName("ToggleButton")
        self.btn_clear_switch_mouse_key.setFlat(True)
        self.btn_clear_switch_mouse_key.setProperty("active", False)
        self.btn_clear_switch_mouse_key.setCursor(Qt.PointingHandCursor)
        self.btn_clear_switch_mouse_key.setFixedHeight(40)
        self.btn_clear_switch_mouse_key.clicked.connect(self._clear_switch_mouse_key)
        switch_row.addWidget(self.btn_switch_mouse_key, 1)
        switch_row.addWidget(self.btn_clear_switch_mouse_key)
        ij_lay.addLayout(switch_row)

        self.lbl_switch_mouse_desc = QLabel("Instantly flips active click button between left and right.")
        self.lbl_switch_mouse_desc.setObjectName("WarnText")
        self.lbl_switch_mouse_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_switch_mouse_desc)

        # Separator
        self.sep_hotkey_5 = QFrame()
        self.sep_hotkey_5.setObjectName("SettingsSeparator")
        self.sep_hotkey_5.setFixedHeight(1)
        ij_lay.addWidget(self.sep_hotkey_5)

        # Toggle both mouse buttons key
        self.lbl_toggle_both_mouse_title = QLabel("Toggle Both Buttons Key")
        self.lbl_toggle_both_mouse_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_toggle_both_mouse_title)

        both_row = QHBoxLayout()
        both_row.setSpacing(10)
        self._toggle_both_mouse_key = self._settings.get("toggle_both_mouse_key", "")
        self.btn_toggle_both_mouse_key = QPushButton(self._format_keybind_label(self._toggle_both_mouse_key))
        self.btn_toggle_both_mouse_key.setObjectName("ToggleButton")
        self.btn_toggle_both_mouse_key.setFlat(True)
        self.btn_toggle_both_mouse_key.setProperty("active", bool(self._toggle_both_mouse_key))
        self.btn_toggle_both_mouse_key.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_both_mouse_key.setFixedHeight(40)
        self.btn_toggle_both_mouse_key.clicked.connect(self._on_toggle_both_mouse_key_click)

        self.btn_clear_toggle_both_mouse_key = QPushButton("Clear")
        self.btn_clear_toggle_both_mouse_key.setObjectName("ToggleButton")
        self.btn_clear_toggle_both_mouse_key.setFlat(True)
        self.btn_clear_toggle_both_mouse_key.setProperty("active", False)
        self.btn_clear_toggle_both_mouse_key.setCursor(Qt.PointingHandCursor)
        self.btn_clear_toggle_both_mouse_key.setFixedHeight(40)
        self.btn_clear_toggle_both_mouse_key.clicked.connect(self._clear_toggle_both_mouse_key)
        both_row.addWidget(self.btn_toggle_both_mouse_key, 1)
        both_row.addWidget(self.btn_clear_toggle_both_mouse_key)
        ij_lay.addLayout(both_row)

        self.lbl_toggle_both_mouse_desc = QLabel("Toggles an all-at-once left+right click mode.")
        self.lbl_toggle_both_mouse_desc.setObjectName("WarnText")
        self.lbl_toggle_both_mouse_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_toggle_both_mouse_desc)

        # Separator
        self.sep_safety_2 = QFrame()
        self.sep_safety_2.setObjectName("SettingsSeparator")
        self.sep_safety_2.setFixedHeight(1)
        ij_lay.addWidget(self.sep_safety_2)

        self.lbl_perf_title = QLabel("Performance Mode")
        self.lbl_perf_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_perf_title)

        self.chk_perf_mode = QCheckBox("Reduce visual updates for slower PCs")
        self.chk_perf_mode.setChecked(self._settings.get("performance_mode", False))
        self.chk_perf_mode.setStyleSheet("")
        self.chk_perf_mode.stateChanged.connect(self._on_perf_mode_changed)
        ij_lay.addWidget(self.chk_perf_mode)

        # Separator
        self.sep_safety_3 = QFrame()
        self.sep_safety_3.setObjectName("SettingsSeparator")
        self.sep_safety_3.setFixedHeight(1)
        ij_lay.addWidget(self.sep_safety_3)

        self.lbl_lag_guard_title = QLabel("Lag Protection")
        self.lbl_lag_guard_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_lag_guard_title)

        self.chk_lag_guard = QCheckBox("Auto-stop if sustained lag is detected")
        self.chk_lag_guard.setChecked(self._settings.get("lag_guard_enabled", False))
        self.chk_lag_guard.setStyleSheet("")
        self.chk_lag_guard.stateChanged.connect(self._on_lag_guard_changed)
        ij_lay.addWidget(self.chk_lag_guard)

        lag_row = QHBoxLayout()
        lag_row.setSpacing(10)
        self.spin_lag_threshold = FocusClearSpinBox()
        self.spin_lag_threshold.setObjectName("TimeSpin")
        self.spin_lag_threshold.setRange(10, 99)
        self.spin_lag_threshold.setValue(int(self._settings.get("lag_guard_threshold", 65)))
        self.spin_lag_threshold.setFixedHeight(36)
        self.spin_lag_threshold.valueChanged.connect(self._on_lag_guard_changed)
        self.spin_lag_events = FocusClearSpinBox()
        self.spin_lag_events.setObjectName("TimeSpin")
        self.spin_lag_events.setRange(2, 20)
        self.spin_lag_events.setValue(int(self._settings.get("lag_guard_events", 6)))
        self.spin_lag_events.setFixedHeight(36)
        self.spin_lag_events.valueChanged.connect(self._on_lag_guard_changed)
        self.lbl_lag_min = QLabel("Min accuracy %")
        lag_row.addWidget(self.lbl_lag_min)
        lag_row.addWidget(self.spin_lag_threshold)
        self.lbl_lag_checks = QLabel("Consecutive checks")
        lag_row.addWidget(self.lbl_lag_checks)
        lag_row.addWidget(self.spin_lag_events)
        ij_lay.addLayout(lag_row)

        self.lbl_lag_guard_desc = QLabel(
            "Stops automatically when measured click accuracy stays below threshold for too long."
        )
        self.lbl_lag_guard_desc.setObjectName("WarnText")
        self.lbl_lag_guard_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_lag_guard_desc)

        # Separator
        self.sep_safety_4 = QFrame()
        self.sep_safety_4.setObjectName("SettingsSeparator")
        self.sep_safety_4.setFixedHeight(1)
        ij_lay.addWidget(self.sep_safety_4)

        self.lbl_start_warning_title = QLabel("Low Interval Warning Dialog")
        self.lbl_start_warning_title.setObjectName("InnerTitle")
        ij_lay.addWidget(self.lbl_start_warning_title)

        self.chk_low_interval_warning = QCheckBox("Show warning before starting below 5 ms interval")
        self.chk_low_interval_warning.setChecked(self._settings.get("low_interval_warning_enabled", True))
        self.chk_low_interval_warning.setStyleSheet("")
        self.chk_low_interval_warning.stateChanged.connect(self._on_low_interval_warning_changed)
        ij_lay.addWidget(self.chk_low_interval_warning)

        self.lbl_start_warning_desc = QLabel(
            "When enabled, the confirmation appears only once per app session."
        )
        self.lbl_start_warning_desc.setObjectName("WarnText")
        self.lbl_start_warning_desc.setWordWrap(True)
        ij_lay.addWidget(self.lbl_start_warning_desc)

        ij_lay.addStretch(1)

        jd_lay.addWidget(inner_jd)
        jd_lay.addStretch(1)

        row.addWidget(sound_card, 1)
        row.addWidget(jd_card, 1)

        # --- Theme selector card ---
        theme_card = Card()
        theme_card.setObjectName("ConfigCard")
        add_shadow(theme_card, blur=26, y=10, alpha=110)
        tc_lay = QVBoxLayout(theme_card)
        tc_lay.setContentsMargins(20, 18, 20, 18)
        tc_lay.setSpacing(14)

        th = QHBoxLayout()
        th.setSpacing(10)
        ti = QLabel("🎨")
        ti.setObjectName("HeaderIcon")
        ti.setFixedSize(34, 34)
        ti.setAlignment(Qt.AlignCenter)
        self.lbl_theme_header = QLabel("Themes")
        self.lbl_theme_header.setObjectName("CardHeader")
        th.addWidget(ti)
        th.addWidget(self.lbl_theme_header)
        th.addStretch(1)
        tc_lay.addLayout(th)

        inner_theme = Card(radius=16)
        inner_theme.setObjectName("InnerPanel")
        it_lay = QVBoxLayout(inner_theme)
        it_lay.setContentsMargins(14, 14, 14, 14)
        it_lay.setSpacing(8)

        self.lbl_theme_title = QLabel("Select Theme")
        self.lbl_theme_title.setObjectName("InnerTitle")
        it_lay.addWidget(self.lbl_theme_title)

        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)
        self.btn_theme_prev = QPushButton("<")
        self.btn_theme_prev.setObjectName("ToggleButton")
        self.btn_theme_prev.setFlat(True)
        self.btn_theme_prev.setProperty("active", True)
        self.btn_theme_prev.setFixedHeight(32)
        self.btn_theme_prev.setFixedWidth(40)
        self.lbl_theme_page = QLabel("Page 1")
        self.lbl_theme_page.setObjectName("WarnText")
        self.btn_theme_next = QPushButton(">")
        self.btn_theme_next.setObjectName("ToggleButton")
        self.btn_theme_next.setFlat(True)
        self.btn_theme_next.setProperty("active", True)
        self.btn_theme_next.setFixedHeight(32)
        self.btn_theme_next.setFixedWidth(40)
        nav_row.addWidget(self.btn_theme_prev)
        nav_row.addWidget(self.lbl_theme_page)
        nav_row.addWidget(self.btn_theme_next)
        nav_row.addStretch(1)
        it_lay.addLayout(nav_row)

        self.theme_grid = QGridLayout()
        self.theme_grid.setHorizontalSpacing(8)
        self.theme_grid.setVerticalSpacing(8)
        it_lay.addLayout(self.theme_grid)

        self._stats_ref = None  # will be set by MainWindow
        saved_theme = str(self._settings.get("selected_theme", "")).strip()
        if saved_theme:
            set_selected_theme_id(saved_theme)
        current_theme = get_selected_theme_id()
        self.theme_buttons: list[tuple[QPushButton, str]] = []
        self._theme_page = 0
        self._theme_page_size = 14  # 2x7
        for t in THEMES:
            tid = t["id"]
            locked = tid != "default" and tid not in get_unlocked_ids()
            icon = t["icon"]
            name = t["name"]
            active = tid == current_theme
            lock_icon = "🔒 " if locked else ""
            btn = QPushButton(f"{'●' if active else '○'}   {icon}  {lock_icon}{name}")
            btn.setObjectName("ToggleButton")
            btn.setFlat(True)
            btn.setProperty("active", active)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setEnabled(not locked)
            btn.clicked.connect(lambda checked, k=tid: self._select_theme(k))
            self.theme_buttons.append((btn, tid))

        self.btn_theme_prev.clicked.connect(self._theme_prev_page)
        self.btn_theme_next.clicked.connect(self._theme_next_page)
        self._refresh_theme_grid(current_theme)

        self.lbl_theme_desc = QLabel("Unlock more themes by earning achievements!")
        self.lbl_theme_desc.setObjectName("WarnText")
        self.lbl_theme_desc.setWordWrap(True)
        it_lay.addWidget(self.lbl_theme_desc)
        it_lay.addStretch(1)

        tc_lay.addWidget(inner_theme)
        tc_lay.addStretch(1)

        self._set_advanced_tab(self._adv_tab)

        lay.addWidget(hero)
        lay.addLayout(row)
        lay.addWidget(theme_card)
        lay.addStretch(1)

    def _select_sound(self, key: str):
        if key == "custom" and not self._custom_start_sound:
            self._choose_custom_sound()
            if not self._custom_start_sound:
                return
        for btn, k in self.sound_buttons:
            active = k == key
            name = [n for n, kk in self.SOUND_OPTIONS if kk == k][0]
            btn.setText(f"{'●' if active else '○'}   {name}")
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        self._settings["sound"] = key
        _save_settings(self._settings)
        self.sound_changed.emit(key)

    # ── Theme methods ──────────────────────────────────────────

    def set_stats_ref(self, stats):
        """Give the settings page a reference to StatsTracker for unlock checks."""
        self._stats_ref = stats
        self.refresh_themes()

    def _select_theme(self, theme_id: str):
        set_selected_theme_id(theme_id)
        self._settings["selected_theme"] = theme_id
        _save_settings(self._settings)
        for btn, tid in self.theme_buttons:
            t = THEME_MAP[tid]
            active = tid == theme_id
            locked = tid != "default" and not is_theme_unlocked(tid, self._stats_ref) if self._stats_ref else tid not in get_unlocked_ids()
            lock_icon = "🔒 " if locked else ""
            btn.setText(f"{'●' if active else '○'}   {t['icon']}  {lock_icon}{t['name']}")
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        self._refresh_theme_grid(theme_id)
        self.theme_changed.emit(theme_id)

    def refresh_themes(self):
        """Re-check which themes are unlocked and update button states."""
        current = get_selected_theme_id()
        for btn, tid in self.theme_buttons:
            t = THEME_MAP[tid]
            if self._stats_ref:
                locked = tid != "default" and not is_theme_unlocked(tid, self._stats_ref)
            else:
                locked = tid != "default" and tid not in get_unlocked_ids()
            active = tid == current
            lock_icon = "🔒 " if locked else ""
            btn.setText(f"{'●' if active else '○'}   {t['icon']}  {lock_icon}{t['name']}")
            btn.setProperty("active", active)
            btn.setEnabled(not locked)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        self._refresh_theme_grid(current)

    def _theme_prev_page(self):
        if self._theme_page > 0:
            self._theme_page -= 1
            self._refresh_theme_grid(get_selected_theme_id())

    def _theme_next_page(self):
        total = len(self.theme_buttons)
        max_page = max(0, (total - 1) // self._theme_page_size)
        if self._theme_page < max_page:
            self._theme_page += 1
            self._refresh_theme_grid(get_selected_theme_id())

    def _refresh_theme_grid(self, current_theme: str):
        while self.theme_grid.count():
            item = self.theme_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        total = len(self.theme_buttons)
        start = self._theme_page * self._theme_page_size
        end = min(total, start + self._theme_page_size)
        slot = 0
        for i in range(start, end):
            btn, tid = self.theme_buttons[i]
            t = THEME_MAP[tid]
            active = tid == current_theme
            locked = tid != "default" and (not is_theme_unlocked(tid, self._stats_ref) if self._stats_ref else tid not in get_unlocked_ids())
            lock_icon = "🔒 " if locked else ""
            btn.setText(f"{'●' if active else '○'}   {t['icon']}  {lock_icon}{t['name']}")
            btn.setProperty("active", active)
            btn.setEnabled(not locked)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            row = slot % 7
            col = slot // 7
            self.theme_grid.addWidget(btn, row, col)
            slot += 1

        max_page = max(0, (total - 1) // self._theme_page_size)
        self.lbl_theme_page.setText(f"Page {self._theme_page + 1}/{max_page + 1} (2x7)")
        self.btn_theme_prev.setEnabled(self._theme_page > 0)
        self.btn_theme_next.setEnabled(self._theme_page < max_page)

    def _preview_sound(self):
        key = self._settings.get("sound", "beep")
        play_sound(key, self.get_custom_start_sound())

    def _custom_sound_label(self) -> str:
        if self._custom_start_sound:
            return f"Custom start sound: {self._custom_start_sound}"
        return "Custom start sound: not set"

    def _choose_custom_sound(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Custom Start Sound", "", "WAV Files (*.wav)")
        if not path:
            return
        self._custom_start_sound = path
        self._settings["custom_start_sound"] = path
        _save_settings(self._settings)
        self.lbl_custom_sound.setText(self._custom_sound_label())
        if self.get_sound() == "custom":
            self.sound_changed.emit("custom")

    def _clear_custom_sound(self):
        self._custom_start_sound = ""
        self._settings["custom_start_sound"] = ""
        _save_settings(self._settings)
        self.lbl_custom_sound.setText(self._custom_sound_label())

    def get_custom_start_sound(self) -> str:
        return self._custom_start_sound

    def _set_advanced_tab(self, tab: str):
        tab = (tab or "function").strip().lower()
        if tab not in ("function", "keybinds", "cosmetics"):
            tab = "function"
        self._adv_tab = tab
        self._settings["advanced_tab"] = tab
        _save_settings(self._settings)

        btns = {
            "function": self.btn_adv_function,
            "keybinds": self.btn_adv_keybinds,
            "cosmetics": self.btn_adv_cosmetics,
        }
        for key, btn in btns.items():
            btn.setProperty("active", key == tab)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

        sections = {
            "function": [
                self.lbl_section_general, self.lbl_jitter_title, self.jitter_slider, self.lbl_jitter_val,
                self.lbl_jitter_desc, self.sep_general_1, self.lbl_delay_title, self.spin_delay,
                self.delay_unit, self.lbl_delay_desc,
            ],
            "keybinds": [
                self.lbl_section_hotkeys, self.lbl_scroll_key_title, self.btn_scroll_key,
                self.btn_clear_scroll_key, self.lbl_scroll_key_desc, self.chk_scroll_hotkey_enabled,
                self.sep_hotkey_1, self.lbl_scroll_as_title, self.chk_scroll_as, self.btn_scroll_as_key,
                self.lbl_scroll_as_desc, self.sep_hotkey_2, self.lbl_overlay_title, self.chk_overlay,
                self.lbl_overlay_desc, self.sep_hotkey_3, self.lbl_emergency_title, self.btn_emergency_key,
                self.btn_clear_emergency, self.lbl_emergency_desc, self.sep_hotkey_4,
                self.lbl_switch_mouse_title, self.btn_switch_mouse_key, self.btn_clear_switch_mouse_key,
                self.lbl_switch_mouse_desc, self.sep_hotkey_5, self.lbl_toggle_both_mouse_title,
                self.btn_toggle_both_mouse_key, self.btn_clear_toggle_both_mouse_key,
                self.lbl_toggle_both_mouse_desc,
            ],
            "function_extra": [
                self.lbl_section_safety, self.sep_safety_1, self.lbl_lock_window_title, self.chk_lock_window,
                self.lbl_lock_window_desc, self.chk_blocked_programs, self.input_blocked_programs,
                self.lbl_blocked_programs_desc, self.sep_safety_edge, self.lbl_edge_stop_title,
                self.chk_edge_stop, self.lbl_edge_margin, self.spin_edge_margin, self.lbl_edge_stop_desc,
                self.sep_safety_corner, self.lbl_corner_stop_title, self.chk_corner_stop,
                self.lbl_corner_size, self.spin_corner_size, self.lbl_corner_stop_desc,
                self.sep_safety_2, self.lbl_perf_title,
                self.chk_perf_mode, self.sep_safety_3, self.lbl_lag_guard_title, self.chk_lag_guard,
                self.lbl_lag_min, self.spin_lag_threshold, self.lbl_lag_checks, self.spin_lag_events,
                self.lbl_lag_guard_desc, self.sep_safety_4, self.lbl_start_warning_title,
                self.chk_low_interval_warning, self.lbl_start_warning_desc,
            ],
            "cosmetics": [
                self.sep_general_2, self.lbl_startup_title, self.chk_startup,
                self.sep_general_3, self.lbl_lang_title, self.combo_lang,
                self.sep_top_action, self.lbl_topbar_action_title, self.combo_topbar_action,
                self.sep_sidebar, self.lbl_sidebar_title, self.chk_sidebar_basic,
                self.chk_sidebar_stats, self.chk_sidebar_achievements, self.chk_sidebar_projects,
                self.chk_sidebar_help, self.lbl_sidebar_order, self.input_sidebar_order,
            ],
        }
        show_function = tab == "function"
        show_keybinds = tab == "keybinds"
        show_cosmetics = tab == "cosmetics"
        for w in sections["function"]:
            w.setVisible(show_function)
        for w in sections["function_extra"]:
            w.setVisible(show_function)
        for w in sections["keybinds"]:
            w.setVisible(show_keybinds)
        for w in sections["cosmetics"]:
            w.setVisible(show_cosmetics)

    def _on_advanced_section_changed(self, idx: int):
        # Backward compatibility for older signal wiring.
        tab_map = {0: "function", 1: "keybinds", 2: "cosmetics", 3: "function"}
        self._set_advanced_tab(tab_map.get(int(idx), "function"))

    def _on_jitter_changed(self, v: int):
        self.lbl_jitter_val.setText(f"{v} ms")
        self._settings["jitter_ms"] = v
        _save_settings(self._settings)
        self.jitter_changed.emit(v)

    def _on_delay_changed(self, v: int):
        self._settings["delay_ms"] = v
        _save_settings(self._settings)

    def _on_delay_unit_changed(self, idx: int):
        self._settings["delay_unit"] = "seconds" if int(idx) == 1 else "milliseconds"
        _save_settings(self._settings)

    def get_delay_ms(self) -> int:
        val = self.spin_delay.value()
        if self.delay_unit.currentIndex() == 1:
            return val * 1000
        return val

    def get_jitter_ms(self) -> int:
        return self.jitter_slider.value()

    def get_sound(self) -> str:
        return self._settings.get("sound", "beep")

    def get_per_click_sound(self) -> bool:
        return self.chk_per_click.isChecked()

    def _on_per_click_changed(self, state):
        self._settings["per_click_sound"] = bool(state)
        _save_settings(self._settings)

    def _on_disable_toasts_changed(self, state):
        self._settings["disable_toasts"] = bool(state)
        _save_settings(self._settings)

    def get_lock_to_window(self) -> bool:
        return self.chk_lock_window.isChecked()

    def _on_lock_window_changed(self, state):
        self._settings["lock_to_window"] = bool(state)
        _save_settings(self._settings)

    def _apply_startup_enabled(self, state: bool):
        if winreg is None:
            return
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            if state:
                exe = sys.executable
                winreg.SetValueEx(key, "MTAutoClicker", 0, winreg.REG_SZ, f'"{exe}"')
            else:
                try:
                    winreg.DeleteValue(key, "MTAutoClicker")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as exc:
            print(f"[Settings] Failed to apply startup setting: {exc}", file=sys.stderr)

    @staticmethod
    def _is_startup_enabled() -> bool:
        if winreg is None:
            return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run",
                                0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "MTAutoClicker")
            winreg.CloseKey(key)
            return True
        except (FileNotFoundError, OSError):
            return False

    def _on_startup_changed(self, state):
        self._settings["startup_enabled"] = bool(state)
        _save_settings(self._settings)
        if winreg is None:
            _show_save_error_toast("Startup setting is only available on Windows.")
            return
        try:
            self._apply_startup_enabled(bool(state))
        except Exception as exc:
            print(f"[Settings] Failed to update startup setting: {exc}", file=sys.stderr)
            _show_save_error_toast("Couldn't update startup setting.")

    def _on_language_changed(self, idx):
        lang_map = {0: "en", 1: "de", 2: "fr", 3: "es"}
        code = lang_map.get(idx, "en")
        self._settings["language"] = code
        _save_settings(self._settings)
        self.language_changed.emit(code)

    def _on_topbar_action_changed(self, idx: int):
        idx_map = {
            0: "search",
            1: "helldivers",
            2: "support",
            3: "projects",
            4: "marketplace",
            5: "about",
            6: "toggle",
            7: "workflow",
        }
        action = idx_map.get(idx, "search")
        self._settings["topbar_action"] = action
        _save_settings(self._settings)
        self.topbar_action_changed.emit(action)

    def get_topbar_action(self) -> str:
        return self._settings.get("topbar_action", "search")

    def _on_sidebar_config_changed(self, _state=None):
        prefs = self.get_sidebar_preferences()
        self._settings["sidebar_basic_mode"] = bool(prefs.get("basic_mode", False))
        self._settings["sidebar_order"] = ",".join(prefs.get("order", []))
        visible = prefs.get("visible", {})
        self._settings["sidebar_show_stats"] = bool(visible.get("stats", True))
        self._settings["sidebar_show_achievements"] = bool(visible.get("achievements", True))
        self._settings["sidebar_show_projects"] = bool(visible.get("projects", True))
        self._settings["sidebar_show_help"] = bool(visible.get("help", True))
        _save_settings(self._settings)
        self.sidebar_config_changed.emit(prefs)

    def get_sidebar_preferences(self) -> dict:
        allowed = ["home", "preset", "settings", "stats", "achievements", "projects", "help"]
        raw = self.input_sidebar_order.text().strip().lower()
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        parts = ["projects" if p == "marketplace" else p for p in parts]
        order = [p for p in parts if p in allowed]
        for key in allowed:
            if key not in order:
                order.append(key)

        visible = {
            "stats": self.chk_sidebar_stats.isChecked(),
            "achievements": self.chk_sidebar_achievements.isChecked(),
            "projects": self.chk_sidebar_projects.isChecked(),
            "help": self.chk_sidebar_help.isChecked(),
        }
        basic_mode = self.chk_sidebar_basic.isChecked()
        if basic_mode:
            # Keep only core pages in simplified mode.
            order = ["home", "preset", "settings", "projects", "help"]
            visible = {
                "stats": False,
                "achievements": False,
                "projects": False,
                "help": True,
            }

        return {
            "basic_mode": basic_mode,
            "order": order,
            "visible": visible,
        }

    def _on_scroll_key_click(self):
        self._start_capture("scroll_key", self.btn_scroll_key)

    def _on_scroll_hotkey_enabled_changed(self, state):
        enabled = bool(state)
        self._settings["scroll_hotkey_enabled"] = enabled
        _save_settings(self._settings)
        self.scroll_hotkey_enabled_changed.emit(enabled)

    def keyPressEvent(self, event):
        if self._capture_target:
            token = self._qt_event_to_token(event)
            if token:
                self.capture_keybind_input(token)
            else:
                self._cancel_capture()
            return
        super().keyPressEvent(event)

    def _clear_scroll_key(self):
        self._scroll_key = ""
        self._settings["scroll_key"] = ""
        _save_settings(self._settings)
        self.btn_scroll_key.setText("None")
        self.btn_scroll_key.setProperty("active", False)
        self.btn_scroll_key.style().unpolish(self.btn_scroll_key)
        self.btn_scroll_key.style().polish(self.btn_scroll_key)
        self._waiting_scroll_key = False
        self.scroll_key_changed.emit("")

    def get_scroll_key(self) -> str:
        return self._scroll_key

    def get_scroll_hotkey_enabled(self) -> bool:
        return self.chk_scroll_hotkey_enabled.isChecked()

    def _on_emergency_key_click(self):
        self._start_capture("emergency_key", self.btn_emergency_key)

    def _clear_emergency_key(self):
        self._emergency_key = ""
        self._settings["emergency_key"] = ""
        _save_settings(self._settings)
        self.btn_emergency_key.setText("None")
        self.btn_emergency_key.setProperty("active", False)
        self.btn_emergency_key.style().unpolish(self.btn_emergency_key)
        self.btn_emergency_key.style().polish(self.btn_emergency_key)
        self._waiting_emergency_key = False
        self.emergency_key_changed.emit("")

    def get_emergency_key(self) -> str:
        return self._emergency_key

    def _on_perf_mode_changed(self, state):
        enabled = state == Qt.Checked
        self._settings["performance_mode"] = enabled
        _save_settings(self._settings)
        self.performance_mode_changed.emit(enabled)

    def _on_lag_guard_changed(self, _state=None):
        self._settings["lag_guard_enabled"] = self.chk_lag_guard.isChecked()
        self._settings["lag_guard_threshold"] = int(self.spin_lag_threshold.value())
        self._settings["lag_guard_events"] = int(self.spin_lag_events.value())
        _save_settings(self._settings)

    def _on_low_interval_warning_changed(self, _state=None):
        self._settings["low_interval_warning_enabled"] = self.chk_low_interval_warning.isChecked()
        _save_settings(self._settings)

    def get_lag_guard_settings(self) -> tuple[bool, int, int]:
        return (
            self.chk_lag_guard.isChecked(),
            int(self.spin_lag_threshold.value()),
            int(self.spin_lag_events.value()),
        )

    def get_low_interval_warning_enabled(self) -> bool:
        return self.chk_low_interval_warning.isChecked()

    def _on_blocked_programs_changed(self, _state=None):
        self._settings["blocked_programs_enabled"] = self.chk_blocked_programs.isChecked()
        self._settings["blocked_programs"] = self.input_blocked_programs.text().strip()
        _save_settings(self._settings)

    def _on_edge_corner_stop_changed(self, _state=None):
        self._settings["edge_stop_enabled"] = self.chk_edge_stop.isChecked()
        self._settings["edge_stop_margin_px"] = int(self.spin_edge_margin.value())
        self._settings["corner_stop_enabled"] = self.chk_corner_stop.isChecked()
        self._settings["corner_stop_size_px"] = int(self.spin_corner_size.value())
        _save_settings(self._settings)

    def get_blocked_programs_settings(self) -> tuple[bool, list[str]]:
        raw = self.input_blocked_programs.text().strip().lower()
        items = []
        for part in raw.replace(";", ",").split(","):
            name = part.strip()
            if not name:
                continue
            if not name.endswith(".exe"):
                name += ".exe"
            items.append(name)
        return self.chk_blocked_programs.isChecked(), items

    def get_edge_corner_stop_settings(self) -> tuple[bool, int, bool, int]:
        return (
            self.chk_edge_stop.isChecked(),
            int(self.spin_edge_margin.value()),
            self.chk_corner_stop.isChecked(),
            int(self.spin_corner_size.value()),
        )

    def get_performance_mode(self) -> bool:
        return self.chk_perf_mode.isChecked()

    # ── Scroll-as-key handlers ─────────────────────────
    def _on_scroll_as_changed(self, state):
        enabled = bool(state)
        self._settings["scroll_as_enabled"] = enabled
        _save_settings(self._settings)
        self.scroll_as_changed.emit(enabled, self._scroll_as_key)

    def _on_scroll_as_key_click(self):
        self._start_capture("scroll_as_key", self.btn_scroll_as_key)

    def _finish_scroll_as_key(self, ch: str):
        self._scroll_as_key = ch
        self._settings["scroll_as_key"] = ch
        _save_settings(self._settings)
        self.btn_scroll_as_key.setText(self._format_keybind_label(ch, "Right Click"))
        self.btn_scroll_as_key.setProperty("active", bool(ch))
        self.btn_scroll_as_key.style().unpolish(self.btn_scroll_as_key)
        self.btn_scroll_as_key.style().polish(self.btn_scroll_as_key)
        self._waiting_scroll_as_key = False
        self.scroll_as_changed.emit(self.chk_scroll_as.isChecked(), ch)

    def get_scroll_as_setting(self) -> tuple[bool, str]:
        return self.chk_scroll_as.isChecked(), self._scroll_as_key

    def _on_switch_mouse_key_click(self):
        self._start_capture("switch_mouse_button_key", self.btn_switch_mouse_key)

    def _clear_switch_mouse_key(self):
        self._switch_mouse_button_key = ""
        self._settings["switch_mouse_button_key"] = ""
        _save_settings(self._settings)
        self.btn_switch_mouse_key.setText("None")
        self.btn_switch_mouse_key.setProperty("active", False)
        self.btn_switch_mouse_key.style().unpolish(self.btn_switch_mouse_key)
        self.btn_switch_mouse_key.style().polish(self.btn_switch_mouse_key)
        self.switch_mouse_button_key_changed.emit("")

    def _on_toggle_both_mouse_key_click(self):
        self._start_capture("toggle_both_mouse_key", self.btn_toggle_both_mouse_key)

    def _clear_toggle_both_mouse_key(self):
        self._toggle_both_mouse_key = ""
        self._settings["toggle_both_mouse_key"] = ""
        _save_settings(self._settings)
        self.btn_toggle_both_mouse_key.setText("None")
        self.btn_toggle_both_mouse_key.setProperty("active", False)
        self.btn_toggle_both_mouse_key.style().unpolish(self.btn_toggle_both_mouse_key)
        self.btn_toggle_both_mouse_key.style().polish(self.btn_toggle_both_mouse_key)
        self.toggle_both_mouse_key_changed.emit("")

    def get_switch_mouse_button_key(self) -> str:
        return self._switch_mouse_button_key

    def get_toggle_both_mouse_key(self) -> str:
        return self._toggle_both_mouse_key

    def is_waiting_for_keybind_capture(self) -> bool:
        return bool(self._capture_target)

    def capture_keybind_input(self, token: str):
        token = (token or "").strip().lower()
        if not token or not self._capture_target:
            return

        conflict = self._find_keybind_conflict(token, self._capture_target)
        if conflict:
            self._cancel_capture()
            return

        if self._capture_target == "scroll_key":
            self._scroll_key = token
            self._settings["scroll_key"] = token
            _save_settings(self._settings)
            self.btn_scroll_key.setText(self._format_keybind_label(token))
            self.btn_scroll_key.setProperty("active", True)
            self.btn_scroll_key.style().unpolish(self.btn_scroll_key)
            self.btn_scroll_key.style().polish(self.btn_scroll_key)
            self.scroll_key_changed.emit(token)

        elif self._capture_target == "emergency_key":
            self._emergency_key = token
            self._settings["emergency_key"] = token
            _save_settings(self._settings)
            self.btn_emergency_key.setText(self._format_keybind_label(token))
            self.btn_emergency_key.setProperty("active", True)
            self.btn_emergency_key.style().unpolish(self.btn_emergency_key)
            self.btn_emergency_key.style().polish(self.btn_emergency_key)
            self.emergency_key_changed.emit(token)

        elif self._capture_target == "scroll_as_key":
            self._finish_scroll_as_key(token)

        elif self._capture_target == "switch_mouse_button_key":
            self._switch_mouse_button_key = token
            self._settings["switch_mouse_button_key"] = token
            _save_settings(self._settings)
            self.btn_switch_mouse_key.setText(self._format_keybind_label(token))
            self.btn_switch_mouse_key.setProperty("active", True)
            self.btn_switch_mouse_key.style().unpolish(self.btn_switch_mouse_key)
            self.btn_switch_mouse_key.style().polish(self.btn_switch_mouse_key)
            self.switch_mouse_button_key_changed.emit(token)

        elif self._capture_target == "toggle_both_mouse_key":
            self._toggle_both_mouse_key = token
            self._settings["toggle_both_mouse_key"] = token
            _save_settings(self._settings)
            self.btn_toggle_both_mouse_key.setText(self._format_keybind_label(token))
            self.btn_toggle_both_mouse_key.setProperty("active", True)
            self.btn_toggle_both_mouse_key.style().unpolish(self.btn_toggle_both_mouse_key)
            self.btn_toggle_both_mouse_key.style().polish(self.btn_toggle_both_mouse_key)
            self.toggle_both_mouse_key_changed.emit(token)

        self._capture_target = ""
        self._waiting_scroll_key = False
        self._waiting_emergency_key = False
        self._waiting_scroll_as_key = False

    def _find_keybind_conflict(self, token: str, target: str) -> bool:
        token = (token or "").strip().lower()
        if not token:
            return False
        current = {
            "scroll_key": self._scroll_key,
            "emergency_key": self._emergency_key,
            "scroll_as_key": self._scroll_as_key,
            "switch_mouse_button_key": self._switch_mouse_button_key,
            "toggle_both_mouse_key": self._toggle_both_mouse_key,
        }
        for key, value in current.items():
            if key != target and value and value.lower() == token:
                self._show_keybind_conflict(target, key, token)
                return True
        return False

    def _show_keybind_conflict(self, wanted_target: str, existing_target: str, token: str):
        wanted = self._friendly_keybind_name(wanted_target)
        existing = self._friendly_keybind_name(existing_target)
        self.lbl_scroll_key_desc.setText(
            f"Conflict: {self._format_keybind_label(token)} is already used for {existing}. "
            f"Choose another key for {wanted}."
        )

    @staticmethod
    def _friendly_keybind_name(target: str) -> str:
        names = {
            "scroll_key": "Scroll keybind",
            "emergency_key": "Emergency stop",
            "scroll_as_key": "Scroll-as-key",
            "switch_mouse_button_key": "Switch left/right",
            "toggle_both_mouse_key": "Toggle both buttons",
        }
        return names.get(target, target)

    def _start_capture(self, target: str, button: QPushButton):
        if self._capture_target:
            return
        self._capture_target = target
        self._waiting_scroll_key = target == "scroll_key"
        self._waiting_emergency_key = target == "emergency_key"
        self._waiting_scroll_as_key = target == "scroll_as_key"
        button.setText("Press any key or mouse button...")
        button.setFocus()

    def _cancel_capture(self):
        self._capture_target = ""
        self._waiting_scroll_key = False
        self._waiting_emergency_key = False
        self._waiting_scroll_as_key = False
        self.btn_scroll_key.setText(self._format_keybind_label(self._scroll_key))
        self.btn_emergency_key.setText(self._format_keybind_label(self._emergency_key))
        self.btn_scroll_as_key.setText(self._format_keybind_label(self._scroll_as_key, "Right Click"))
        self.btn_switch_mouse_key.setText(self._format_keybind_label(self._switch_mouse_button_key))
        self.btn_toggle_both_mouse_key.setText(self._format_keybind_label(self._toggle_both_mouse_key))

    @staticmethod
    def _format_keybind_label(token: str, empty_label: str = "None") -> str:
        tok = (token or "").strip().lower()
        if not tok:
            return empty_label
        if tok.startswith("mouse_"):
            return tok.replace("_", " ").title()
        if len(tok) == 1:
            return tok.upper()
        return tok.replace("_", " ").title()

    @staticmethod
    def _qt_event_to_token(event) -> str:
        text = (event.text() or "").strip().lower()
        if text:
            return text

        key_map = {
            Qt.Key_Space: "space",
            Qt.Key_Tab: "tab",
            Qt.Key_Return: "enter",
            Qt.Key_Enter: "enter",
            Qt.Key_Escape: "esc",
            Qt.Key_Backspace: "backspace",
            Qt.Key_Delete: "delete",
            Qt.Key_Insert: "insert",
            Qt.Key_Home: "home",
            Qt.Key_End: "end",
            Qt.Key_PageUp: "page_up",
            Qt.Key_PageDown: "page_down",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Shift: "shift",
            Qt.Key_Control: "ctrl",
            Qt.Key_Alt: "alt",
            Qt.Key_CapsLock: "caps_lock",
        }
        key_val = event.key()
        if key_val in key_map:
            return key_map[key_val]
        if Qt.Key_F1 <= key_val <= Qt.Key_F24:
            return f"f{key_val - Qt.Key_F1 + 1}"
        return ""

    def retranslateUi(self):
        """Update all translatable text."""
        self.hero_title.setText(tr("settings_title"))
        self.hero_sub.setText(tr("settings_sub"))
        self.lbl_sound_header.setText(tr("sound_effects"))
        self.lbl_start_stop_sound.setText(tr("start_stop_sound"))
        # Sound option buttons
        sound_keys = {
            "": "none_sound", "beep": "default_beep",
            "ding": "ding", "chirp": "chirp", "alert": "alert",
        }
        for btn, key in self.sound_buttons:
            active = btn.property("active")
            label_key = sound_keys.get(key, key)
            btn.setText(f"{'●' if active else '○'}   {tr(label_key)}")
        self.btn_preview.setText(tr("preview_sound"))
        self.chk_per_click.setText(tr("per_click_desc"))
        self.lbl_advanced_header.setText(tr("advanced"))
        self.lbl_jitter_title.setText(tr("random_jitter"))
        self.lbl_jitter_desc.setText(tr("jitter_desc"))
        self.lbl_delay_title.setText(tr("delayed_start"))
        self.lbl_delay_desc.setText(tr("delay_desc"))
        self.lbl_startup_title.setText(tr("startup_windows"))
        self.chk_startup.setText(tr("startup_desc"))
        self.lbl_lang_title.setText(tr("language"))
        self.lbl_scroll_key_title.setText(tr("scroll_keybind"))
        self.lbl_scroll_key_desc.setText(tr("scroll_keybind_desc"))
        # Delay unit combo
        self.delay_unit.setItemText(0, tr("milliseconds"))
        self.delay_unit.setItemText(1, tr("seconds"))

    def _on_color_trigger_changed(self, *_args) -> None:
        self._settings["color_trigger_enabled"] = self.chk_color_trigger.isChecked()
        self._settings["color_trigger_x"] = int(self.spin_color_x.value())
        self._settings["color_trigger_y"] = int(self.spin_color_y.value())
        self._settings["color_trigger_r"] = int(self.spin_color_r.value())
        self._settings["color_trigger_g"] = int(self.spin_color_g.value())
        self._settings["color_trigger_b"] = int(self.spin_color_b.value())
        self._settings["color_trigger_tolerance"] = int(self.spin_color_tol.value())
        _save_settings(self._settings)

    def _on_tray_minimize_changed(self, *_args) -> None:
        self._settings["tray_minimize"] = self.chk_tray_minimize.isChecked()
        _save_settings(self._settings)

    def get_color_trigger_settings(self) -> dict:
        return {
            "enabled": bool(self._settings.get("color_trigger_enabled", False)),
            "x": int(self._settings.get("color_trigger_x", 0)),
            "y": int(self._settings.get("color_trigger_y", 0)),
            "r": int(self._settings.get("color_trigger_r", 255)),
            "g": int(self._settings.get("color_trigger_g", 0)),
            "b": int(self._settings.get("color_trigger_b", 0)),
            "tolerance": int(self._settings.get("color_trigger_tolerance", 12)),
        }

    def get_tray_minimize_enabled(self) -> bool:
        return bool(self._settings.get("tray_minimize", True))


def play_sound(key: str, custom_path: str = ""):
    """Play a system sound by key, optionally from custom WAV file."""
    if winsound is None:
        return
    try:
        if key == "custom" and custom_path:
            winsound.PlaySound(custom_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        if key == "beep":
            winsound.Beep(800, 150)
        elif key == "ding":
            winsound.Beep(1200, 100)
        elif key == "chirp":
            winsound.Beep(600, 80)
            winsound.Beep(900, 80)
        elif key == "alert":
            winsound.Beep(1000, 200)
        elif key == "soft_click":
            winsound.Beep(700, 60)
        elif key == "pulse":
            winsound.Beep(760, 70)
            winsound.Beep(860, 70)
        elif key == "arcade":
            winsound.Beep(1000, 60)
            winsound.Beep(1300, 60)
            winsound.Beep(1600, 80)
    except Exception:
        pass


def play_tick():
    """Play a tiny tick sound for per-click feedback."""
    if winsound is None:
        return
    try:
        winsound.Beep(2000, 15)
    except Exception:
        pass
