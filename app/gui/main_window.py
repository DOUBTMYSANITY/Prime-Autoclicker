from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QEvent, QStringListModel
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QDialog, QSizeGrip, QSpinBox, QLineEdit, QTextEdit,
    QFormLayout, QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout,
    QApplication, QCompleter,
)
from PyQt5.QtGui import QMouseEvent, QRegion
from pynput import keyboard
from pynput import mouse as _mouse
from pynput.mouse import Controller as MouseController
from pathlib import Path
import sys as _sys


from app import PROJECT_ROOT, setup_paths

setup_paths()

from app.core.function_auto import ClickConfig, AutoRunner
from app.styling.localization import tr, set_language
from app.gui.widgets import (
    GradientBackground, Card, PillButton, add_shadow,
    make_placeholder_page, make_projects_page, ToastNotification,
    AdaptiveStack, CompactOverlay,
)
from app.services.stats_tracker import StatsTracker
from app.pages.stats_page import StatsPage
from app.pages.settings_page import SettingsPage, play_sound, play_tick
from app.pages.presets_page import PresetDialog, PresetPage
from app.pages.home_page import HomePage
from app.pages.achievements_page import AchievementsPage
from app.pages.admin_panel import AdminPanel
from app.styling.themes import get_theme, get_theme_font, check_and_unlock_all, get_selected_theme_id, get_dialog_stylesheet
from app.pages.about_page import AboutPage
from app.windows.phasmophobia_window import PhasmophobiaWindow
from app.pages.macro_builder_page import MacroBuilderPage
from app.pages.marketplace_page import MarketplacePage
from app.services.plugin_system import PluginManager
from app.pages.support_hub_page import SupportHubPage
from app.services.app_services import AppServices
import ctypes as _ctypes
import sys as _sys
import json as _json
import time as _time_module
import collections as _collections
import threading as _th
import queue as _queue
import textwrap as _textwrap
import difflib as _difflib
from pathlib import Path
from datetime import datetime

# Konami Code sequence
_KONAMI_KEYS = ["up", "up", "down", "down", "left", "right", "left", "right", "b", "a"]


class _EnterDefocusFilter(QWidget):
    """App-wide event filter: pressing Enter/Return in any QSpinBox or QLineEdit
    forces focus to the main window so the field is deselected."""

    def __init__(self, main_window: QMainWindow):
        super().__init__(main_window)
        self._mw = main_window

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if isinstance(obj, QLineEdit) and getattr(self._mw, "input_search", None) is obj:
                    self._mw._on_topbar_action()
                    return True
                if isinstance(obj, (QSpinBox, QLineEdit)):
                    # Commit the current text
                    if isinstance(obj, QSpinBox):
                        obj.interpretText()
                    # Move focus to the main window
                    self._mw.setFocus(Qt.OtherFocusReason)
                    return True  # eat the event
            return False
        except KeyboardInterrupt:
            app = QApplication.instance()
            if app is not None:
                app.quit()
            return True


class MainWindow(QMainWindow):
    PAGE_HOME = 0
    PAGE_PRESET = 1
    PAGE_SETTINGS = 2
    PAGE_TOKENS = 3
    PAGE_PROJECTS = 4
    PAGE_LOGIN = 5
    PAGE_ACHIEVEMENTS = 6
    PAGE_BUILDER = 7
    PAGE_SUPPORT = 8
    PAGE_MARKETPLACE = 9
    PAGE_PLUGIN_OPTIONS = 10
    _toggle_signal = pyqtSignal()  # Bridge pynput thread -> Qt main thread
    _hotkey_signal = pyqtSignal(str)  # Bridge pynput thread -> Qt for hotkey capture
    _capture_signal = pyqtSignal(str)  # Bridge pynput thread -> settings capture
    _input_token_signal = pyqtSignal(str, bool)  # Bridge pynput thread -> Qt input handler

    _WCA_ACCENT_POLICY = 19
    _ACCENT_DISABLED = 0
    _ACCENT_ENABLE_BLURBEHIND = 3
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(tr("app_title"))
        self.resize(1200, 720)
        self._is_windows = _sys.platform.startswith("win")
        self._drag_pos = None
        self.stats = StatsTracker()
        self.config = ClickConfig()
        self.runner = AutoRunner(self.config)
        self._is_toggling = False
        self._hotkey_char = "x"
        self._pressed_keyboard_tokens: set[str] = set()
        # Load persisted hotkey
        _saved_hk = self._load_persisted_hotkey()
        if _saved_hk:
            self._hotkey_char = _saved_hk
        self._waiting_for_hotkey = False
        self._session_start = None
        self._scroll_hotkey_enabled = True
        self._lag_guard_enabled = False
        self._lag_guard_threshold = 65
        self._lag_guard_events = 6
        self._lag_guard_streak = 0
        self._low_interval_warning_shown = False
        self._blocked_programs_enabled = False
        self._blocked_programs: set[str] = set()
        self._search_terms: list[str] = []
        self._search_routes: list[dict] = []
        # Secrets tracking state
        self._konami_buf: list[str] = []  # last N key names
        self._visited_pages: set[int] = set()
        self._toggle_times: _collections.deque = _collections.deque(maxlen=10)
        self._achievement_snapshot: set[str] = set()  # names of earned achievements
        self._last_gui_tick: float = 0.0  # throttle GUI updates from click_performed
        self._pending_stat_clicks: int = 0
        self._last_hotkey_switch_toggle: float = 0.0
        self._last_hotkey_both_toggle: float = 0.0
        self._rr_recording = False
        self._rr_playing = False
        self._rr_events: list[dict] = []
        self._rr_record_start: float = 0.0
        self._rr_last_move_ts: float = 0.0
        self._rr_last_pos: tuple[int, int] | None = None
        self._rr_status_text: str = "Idle"
        self._rr_cfg_cache: dict | None = None
        self._session_events: list[str] = []
        self._smart_stabilize_key: str = ""
        self._smart_stabilize_best_accuracy: float = 0.0
        self._smart_stabilize_best_correction_ms: float = 0.0
        self._hotkey_listener_booting = False
        self._plugin_manager = PluginManager(PROJECT_ROOT)
        self._services = AppServices()
        # Single persistent thread for tick sounds (avoids spawning thousands of threads)
        self._tick_q: _queue.SimpleQueue = _queue.SimpleQueue()
        _th.Thread(target=self._tick_sound_worker, daemon=True).start()
        self._build_ui()
        self._apply_styles()
        self._wire()
        self._toggle_signal.connect(self._toggle_autoclicker)
        self._hotkey_signal.connect(self._set_hotkey)
        self._capture_signal.connect(self.page_settings.capture_keybind_input)
        self._input_token_signal.connect(self._handle_input_token)
        self._snapshot_achievements()  # baseline after init
        self._switch_page(self.PAGE_HOME)
        QTimer.singleShot(0, self._run_deferred_startup_tasks)

        # Global event filter: Enter/Return on any input field loses focus
        app = QApplication.instance()
        if app:
            self._enter_filter = _EnterDefocusFilter(self)
            app.installEventFilter(self._enter_filter)

    def _run_deferred_startup_tasks(self):
        """Stagger heavy startup work to keep first paint responsive."""
        QTimer.singleShot(120, self._start_hotkey_listener_async)
        QTimer.singleShot(650, self._deferred_refresh_plugins)
        QTimer.singleShot(1100, self._deferred_theme_unlock_refresh)

    def _start_hotkey_listener_async(self):
        if self._hotkey_listener_booting:
            return
        if hasattr(self, "keyboard_listener") or hasattr(self, "mouse_listener"):
            return
        self._hotkey_listener_booting = True

        def _bootstrap_listeners():
            try:
                self._setup_hotkey()
            finally:
                self._hotkey_listener_booting = False

        _th.Thread(target=_bootstrap_listeners, daemon=True).start()

    def _deferred_refresh_plugins(self):
        try:
            self._plugin_manager.load_all()
        except Exception:
            pass
        self._refresh_plugin_page_state()

    def _deferred_theme_unlock_refresh(self):
        try:
            newly = check_and_unlock_all(self.stats)
            if newly:
                self.page_settings.refresh_themes()
        except Exception:
            pass

    def _build_ui(self):
        self._bg = GradientBackground()
        theme = get_theme()
        self._bg.set_gradient(theme["gradient"])
        self._bg.setStyleSheet("GradientBackground { border-radius: 16px; }")
        self.setCentralWidget(self._bg)
        outer = QVBoxLayout(self._bg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Custom title bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(38)
        tb_lay = QHBoxLayout(self.title_bar)
        tb_lay.setContentsMargins(14, 0, 8, 0)
        tb_lay.setSpacing(8)

        self.title_label = QLabel(tr("app_title"))
        self.title_label.setObjectName("TitleBarLabel")

        self.btn_minimize = QPushButton("\u2500")
        self.btn_maximize = QPushButton("\u25a1")
        self.btn_close = QPushButton("\u2715")
        for btn in (self.btn_minimize, self.btn_maximize, self.btn_close):
            btn.setObjectName("TitleBarBtn")
            btn.setFixedSize(32, 26)
            btn.setCursor(Qt.PointingHandCursor)
        self.btn_close.setObjectName("TitleBarCloseBtn")
        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self.close)

        tb_lay.addWidget(self.title_label)
        tb_lay.addStretch(1)
        tb_lay.addWidget(self.btn_minimize)
        tb_lay.addWidget(self.btn_maximize)
        tb_lay.addWidget(self.btn_close)
        outer.addWidget(self.title_bar)

        # Main body
        body = QWidget()
        root = QHBoxLayout(body)
        root.setContentsMargins(18, 10, 18, 18)
        root.setSpacing(16)
        outer.addWidget(body, 1)

        # Size grip for resizing
        self._size_grip = QSizeGrip(self)
        self._size_grip.setFixedSize(16, 16)
        self._size_grip.setStyleSheet("background: transparent;")

        # Sidebar
        self.sidebar = Card()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(235)
        add_shadow(self.sidebar, blur=24, y=10, alpha=110)
        sb = QVBoxLayout(self.sidebar)
        sb.setContentsMargins(18, 18, 18, 18)
        sb.setSpacing(16)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        logo_mark = QLabel("PA")
        logo_mark.setObjectName("LogoMark")
        logo_mark.setFixedSize(58, 58)
        logo_mark.setAlignment(Qt.AlignCenter)
        logo_text = QLabel("PRIME\nAUTOCLICKER")
        logo_text.setObjectName("LogoText")
        logo_row.addWidget(logo_mark)
        logo_row.addWidget(logo_text)
        logo_row.addStretch(1)
        sb.addLayout(logo_row)

        self.btn_home = PillButton(tr("home"), "\u2302")
        self.btn_preset = PillButton("Workflow Studio", "\u25a6")
        self.btn_settings = PillButton(tr("settings"), "\u2699")
        self.btn_tokens = PillButton(tr("stats"), "\U0001F4CA")
        self.btn_achievements = PillButton(tr("achievements"), "\U0001F3C5")
        self.btn_support = PillButton("Support Hub", "\u2695")
        self.btn_projects = PillButton("Plugins", "\U0001F517")
        self.btn_login = PillButton("Help Center", "?")

        self._sidebar_nav_host = QWidget()
        self._sidebar_nav_layout = QVBoxLayout(self._sidebar_nav_host)
        self._sidebar_nav_layout.setContentsMargins(0, 6, 0, 0)
        self._sidebar_nav_layout.setSpacing(8)
        sb.addWidget(self._sidebar_nav_host, 1)

        # Main content
        self.main = QWidget()
        main = QVBoxLayout(self.main)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(16)

        # Top bar
        top = Card()
        top.setObjectName("TopBar")
        top.setFixedHeight(58)
        self._top_bar_card = top
        add_shadow(top, blur=22, y=8, alpha=90)
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(18, 10, 18, 10)
        top_l.setSpacing(12)

        self.btn_back = QPushButton("\u2190")
        self.btn_back.setObjectName("IconBtn")
        self.btn_back.setFixedSize(38, 38)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.lbl_top_title = QLabel(tr("home"))
        self.lbl_top_title.setObjectName("TopTitle")

        top_l.addWidget(self.btn_back)
        top_l.addWidget(self.lbl_top_title)
        top_l.addStretch(1)

        self.btn_hotkey = QPushButton(f"Hotkey: {self._hotkey_char.upper()}")
        self.btn_hotkey.setObjectName("HotkeyBtn")
        self.btn_hotkey.setCursor(Qt.PointingHandCursor)
        self.btn_hotkey.setFixedHeight(32)
        self.btn_hotkey.setMinimumWidth(100)
        top_l.addWidget(self.btn_hotkey)

        self.input_search = QLineEdit()
        self.input_search.setObjectName("HotkeyBtn")
        self.input_search.setPlaceholderText("Smart search everything...")
        self.input_search.setFixedHeight(32)
        self.input_search.setMinimumWidth(220)
        self.btn_search = QPushButton("Smart Search")
        self.btn_search.setObjectName("HotkeyBtn")
        self.btn_search.setFixedHeight(32)
        self.btn_search.setMinimumWidth(120)

        self.lbl_avg_cps = QLabel("Avg CPS: 0.0")
        self.lbl_avg_cps.setObjectName("Badge")
        self.lbl_avg_cps.setFixedHeight(28)
        self.lbl_avg_cps.setAlignment(Qt.AlignCenter)
        self.lbl_avg_cps.setMinimumWidth(98)

        top_l.addWidget(self.input_search)
        top_l.addWidget(self.btn_search)
        top_l.addWidget(self.lbl_avg_cps)

        # Pages
        self.pages = AdaptiveStack()
        self.pages.setObjectName("Pages")
        self.page_home = HomePage()
        self.page_preset = PresetPage()
        self.page_builder = MacroBuilderPage()
        self.page_preset_builder = self._make_fused_page(
            "Presets", self.page_preset,
            "Macro Builder", self.page_builder,
        )
        self.page_settings = SettingsPage()
        self.page_stats = StatsPage(self.stats)
        self.page_projects = make_projects_page()
        self.page_marketplace = MarketplacePage()
        self.page_plugins_market = self._make_fused_page(
            "Plugins", self.page_projects,
            "Marketplace", self.page_marketplace,
        )
        self.page_about = AboutPage()
        self.page_achievements = AchievementsPage(self.stats)
        self.page_support = SupportHubPage(self._services)
        self.page_plugin_options = self._make_plugin_options_page()
        self.page_login = self._make_fused_page(
            "About", self.page_about,
            "Support", self.page_support,
        )

        self.pages.addWidget(self.page_home)
        self.pages.addWidget(self.page_preset_builder)
        self.pages.addWidget(self.page_settings)
        self.pages.addWidget(self.page_stats)
        self.pages.addWidget(self.page_plugins_market)
        self.pages.addWidget(self.page_login)
        self.pages.addWidget(self.page_achievements)
        self.pages.addWidget(make_placeholder_page("Builder", "Merged into Preset + Builder"))
        self.pages.addWidget(make_placeholder_page("Support", "Merged into Help Center"))
        self.pages.addWidget(make_placeholder_page("Marketplace", "Merged into Plugins + Marketplace"))
        self.pages.addWidget(self.page_plugin_options)

        # Wrap in scroll area for full-content scrolling
        scroll = QScrollArea()
        scroll.setObjectName("MainScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_content = QWidget()
        scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setContentsMargins(0, 0, 0, 0)
        scroll_lay.setSpacing(16)
        scroll_lay.addWidget(top)
        scroll_lay.addWidget(self.pages)
        scroll.setWidget(scroll_content)
        self.scroll = scroll
        # Fail-safe: prevent scrolling into empty whitespace below content
        scroll.verticalScrollBar().rangeChanged.connect(self._clamp_scroll_range)

        main.addWidget(scroll, 1)
        root.addWidget(self.sidebar)
        root.addWidget(self.main, 1)

    def _apply_styles(self, theme_id: str | None = None):
        theme = get_theme(theme_id)
        p = theme["palette"]
        theme_font = get_theme_font(theme.get("id"))
        # Update gradient background
        self._bg.set_gradient(theme["gradient"])
        self.setStyleSheet(
            f"QWidget {{ color: {p['text_primary']}; font-family: {theme_font}; }}"
            f"QFrame#Card {{ background: {p['base']}; border-radius: 20px; }}"
                        f"QWidget#TitleBar {{ background: {p['topbar']}; border-top-left-radius: 20px; border-top-right-radius: 20px; }}"
                        f"QLabel#TitleBarLabel {{ color: {p['text_secondary']}; font-size: 12px; font-weight: 600; background: transparent; }}"
                        f"QPushButton#TitleBarBtn {{"
                        f"  background: {p['pill_bg']}; border: 1px solid {p['pill_border']};"
                        f"  border-radius: 8px; color: {p['text_secondary']}; font-size: 13px;"
                        f"}}"
                        f"QPushButton#TitleBarBtn:hover {{ background: {p['pill_active_bg']}; color: {p['text_primary']}; }}"
                        f"QPushButton#TitleBarBtn:pressed {{ background: {p['accent'].format(a='0.20')}; border: 1px solid {p['pill_active_border']}; color: {p['text_primary']}; }}"
                        f"QPushButton#TitleBarCloseBtn {{"
                        f"  background: {p['pill_bg']}; border: 1px solid {p['pill_border']};"
                        f"  border-radius: 8px; color: {p['text_secondary']}; font-size: 13px;"
                        f"}}"
                        f"QPushButton#TitleBarCloseBtn:hover {{ background: {p['stop_btn_bg']}; color: #FFFFFF; border: 1px solid {p['stop_btn_border']}; }}"
                        f"QPushButton#TitleBarCloseBtn:pressed {{ background: {p['stop_btn_border']}; color: #FFFFFF; border: 1px solid {p['stop_btn_border']}; }}"
            f"QFrame#Sidebar {{ background: {p['sidebar']}; border-radius: 20px; }}"
            f"QFrame#TopBar {{ background: {p['topbar']}; border-radius: 20px; }}"
            f"QFrame#Hero {{ background: {p['hero']}; border-radius: 20px; }}"
            f"QFrame#ConfigCard {{ background: {p['config_card']}; border-radius: 20px; }}"
            f"QFrame#InnerPanel {{ background: {p['inner_panel']}; border-radius: 14px; }}"
            f"QFrame#MarketplaceCard {{ background: rgba(10,12,18,0.50); border: 1px solid {p['pill_border']}; border-radius: 20px; }}"
            f"QFrame#MarketplaceInnerPanel {{ background: rgba(18,20,28,0.50); border: 1px solid rgba(255,255,255,0.10); border-radius: 14px; }}"
            f"QFrame#TimeBox, QFrame#CycleBox {{ background: {p['input_bg']}; border-radius: 12px; }}"
            f"QLabel#LogoMark {{"
            f"  background: {p['logo_bg']};"
            f"  border: 1px solid {p['logo_border']};"
            f"  border-radius: 16px; font-size: 20px; font-weight: 700; letter-spacing: 1px;"
            f"}}"
            f"QLabel#LogoText {{ font-size: 16px; font-weight: 700; line-height: 1.1; color: {p['text_primary']}; }}"
            f"QPushButton#PillButton {{"
            f"  text-align: left; padding-left: 50px; border-radius: 14px;"
            f"  background: {p['pill_bg']}; border: 1px solid {p['pill_border']};"
            f"  font-size: 14px; height: 44px;"
            f"}}"
            f"QPushButton#PillButton:hover {{"
            f"  background: {p['pill_active_bg']}; border: 1px solid {p['pill_active_border']};"
            f"}}"
            f"QPushButton#PillButton:pressed {{"
            f"  background: {p['accent'].format(a='0.12')}; border: 1px solid {p['accent'].format(a='0.18')};"
            f"}}"
            f"QPushButton#PillButton[active=\"true\"] {{"
            f"  background: {p['pill_active_bg']}; border: 1px solid {p['pill_active_border']};"
            f"}}"
            f"QLabel#PillIcon {{"
            f"  color: {p['text_secondary']}; background: rgba(0,0,0,0.18); border-radius: 14px;"
            f"  font-size: 14px; padding: 0px;"
            f"}}"
            f"QPushButton#IconBtn {{"
            f"  background: {p['pill_bg']}; border: 1px solid {p['pill_border']};"
            f"  border-radius: 12px; font-size: 16px; text-align: center; padding: 0px;"
            f"}}"
            f"QPushButton#IconBtn:hover {{ background: {p['pill_active_bg']}; border: 1px solid {p['pill_active_border']}; }}"
            f"QPushButton#IconBtn:pressed {{ background: {p['accent'].format(a='0.15')}; }}"
            f"QLabel#TopTitle {{ font-size: 14px; font-weight: 600; color: {p['text_primary']}; }}"
            f"QLabel#Badge {{"
            f"  background: {p['badge_bg']}; border: 1px solid {p['badge_border']};"
            f"  border-radius: 12px; font-weight: 700; padding: 0px 8px;"
            f"}}"
            f"QLabel#HeroTitle {{ font-size: 22px; font-weight: 700; color: {p['text_primary']}; }}"
            f"QLabel#HeroSub {{ font-size: 12.5px; color: {p['text_secondary']}; }}"
            f"QLabel#Illustration {{"
            f"  background: {p['pill_bg']}; border: 1px solid {p['pill_border']};"
            f"  border-radius: 18px;"
            f"}}"
            f"QLabel#HeaderIcon {{"
            f"  background: {p['pill_bg']}; border: 1px solid {p['pill_border']};"
            f"  border-radius: 12px; color: {p['text_secondary']}; font-size: 16px; padding: 0px;"
            f"}}"
            f"QLabel#CardHeader {{ font-size: 15px; font-weight: 700; color: {p['text_primary']}; }}"
            f"QLabel#AboutValueStrong, QLabel#AboutKeyStrong {{"
            f"  font-size: 12.5px; font-weight: 700; color: {p['text_primary']};"
            f"}}"
            f"QComboBox#DropDown {{"
            f"  background: {p['combo_bg']}; border: 1px solid {p['combo_border']};"
            f"  border-radius: 10px; padding: 6px; color: {p['text_secondary']};"
            f"}}"
            f"QComboBox#DropDown::drop-down {{ border: none; }}"
            f"QComboBox#DropDown::down-arrow {{ image: none; }}"
            f"QComboBox#DropDown QAbstractItemView {{"
            f"  background: {p['combo_list_bg']}; border: 1px solid {p['combo_border']}; border-radius: 8px;"
            f"  color: {p['text_secondary']}; selection-background-color: {p['combo_sel_bg']}; selection-color: {p['text_primary']};"
            f"  outline: none;"
            f"}}"
            f"QAbstractItemView#SearchSuggestList {{"
            f"  background: {p['combo_list_bg']};"
            f"  border: 1px solid {p['combo_border']};"
            f"  border-radius: 10px;"
            f"  color: {p['text_secondary']};"
            f"  outline: none;"
            f"  padding: 4px;"
            f"}}"
            f"QAbstractItemView#SearchSuggestList::item {{"
            f"  padding: 6px 8px;"
            f"  border-radius: 6px;"
            f"}}"
            f"QAbstractItemView#SearchSuggestList::item:selected {{"
            f"  background: {p['combo_sel_bg']};"
            f"  color: {p['text_primary']};"
            f"}}"
            f"QPushButton#ToggleButton {{"
            f"  color: {p['text_secondary']}; font-size: 12.5px; padding: 8px 14px;"
            f"  background: {p['toggle_bg']}; border: 1px solid {p['toggle_border']};"
            f"  border-radius: 12px; text-align: left; outline: none;"
            f"}}"
            f"QPushButton#ToggleButton:hover {{"
            f"  background: {p['toggle_active_bg']}; border: 1px solid {p['toggle_border']};"
            f"}}"
            f"QPushButton#ToggleButton:pressed {{"
            f"  background: {p['toggle_active_bg']}; border: 1px solid {p['toggle_active_border']};"
            f"  color: {p['text_primary']};"
            f"}}"
            f"QPushButton#ToggleButton[active=\"true\"] {{"
            f"  background: {p['toggle_active_bg']}; border: 1px solid {p['toggle_active_border']};"
            f"  color: {p['text_primary']};"
            f"}}"
            f"QPushButton#ToggleButton[active=\"false\"] {{"
            f"  background: {p['toggle_bg']}; border: 1px solid {p['toggle_border']};"
            f"  color: rgba(150,150,180,0.55);"
            f"}}"
            f"QLabel#TimeUnit {{ font-size: 12px; color: {p['text_secondary']}; }}"
            f"QSpinBox#TimeSpin {{"
            f"  background: {p['input_bg']}; border: 1px solid {p['input_border']};"
            f"  border-radius: 8px; padding: 4px 6px; font-weight: 700; font-size: 13px; color: {p['text_primary']};"
            f"}}"
            f"QSpinBox#TimeSpin::up-button, QSpinBox#TimeSpin::down-button {{ width: 0px; height: 0px; }}"
            f"QSpinBox#TimeSpin:disabled {{ color: rgba(233,237,255,0.30); background: rgba(0,0,0,0.10); }}"
            f"QLabel#InnerTitle {{ font-size: 12.5px; font-weight: 700; color: {p['text_secondary']}; }}"
            f"QSpinBox#Spin {{"
            f"  background: {p['input_bg']}; border: 1px solid {p['input_border']};"
            f"  border-radius: 12px; padding: 6px 10px; font-weight: 700;"
            f"}}"
            f"QDoubleSpinBox#Spin {{"
            f"  background: {p['input_bg']}; border: 1px solid {p['input_border']};"
            f"  border-radius: 12px; padding: 6px 10px; font-weight: 700;"
            f"}}"
            f"QSpinBox#Spin::up-button, QSpinBox#Spin::down-button {{ width: 0px; height: 0px; }}"
            f"QDoubleSpinBox#Spin::up-button, QDoubleSpinBox#Spin::down-button {{ width: 0px; height: 0px; }}"
            f"QComboBox#UnitDrop {{"
            f"  background: {p['combo_bg']}; border: 1px solid {p['combo_border']};"
            f"  border-radius: 12px; padding: 6px 10px; color: {p['text_secondary']};"
            f"}}"
            f"QComboBox#UnitDrop::drop-down {{ border: none; }}"
            f"QComboBox#UnitDrop::down-arrow {{ image: none; }}"
            f"QComboBox#UnitDrop QAbstractItemView {{"
            f"  background: {p['combo_list_bg']}; border: 1px solid {p['combo_border']}; border-radius: 8px;"
            f"  color: {p['text_secondary']}; selection-background-color: {p['combo_sel_bg']}; selection-color: {p['text_primary']};"
            f"  outline: none;"
            f"}}"
            f"QLabel#MsLabel {{ font-size: 13px; font-weight: 700; color: {p['text_secondary']}; padding: 0px 8px; }}"
            f"QLabel#WarnText {{ color: rgba(233,237,255,0.55); font-size: 11.5px; }}"
            f"QLabel#SparkHeader {{ font-size: 13px; font-weight: 600; color: {p['text_secondary']}; background: transparent; }}"
            f"QLabel#FunFact {{"
            f"  color: {p['text_secondary']}; font-size: 13px; font-style: italic;"
            f"  padding: 8px 10px; background: {p['pill_bg']}; border: 1px solid {p['pill_border']}; border-radius: 10px;"
            f"}}"
            f"QLabel#StatusLabel {{ font-size: 12.5px; font-weight: 700; color: {p['text_secondary']}; }}"
            f"QLabel#StatusLabel[running=\"true\"] {{ color: {p['running_color']}; }}"
            f"QLabel#StatusLabel[running=\"false\"] {{ color: {p['stopped_color']}; }}"
            f"QPushButton#StartStopBtn {{"
            f"  background: {p['start_btn_bg']}; border: 1px solid {p['start_btn_border']};"
            f"  border-radius: 12px; font-weight: 700; font-size: 14px; color: {p['text_primary']};"
            f"}}"
            f"QPushButton#StartStopBtn:hover {{ background: {p['accent'].format(a='0.28')}; }}"
            f"QPushButton#StartStopBtn:pressed {{ background: {p['accent'].format(a='0.35')}; }}"
            f"QPushButton#StartStopBtn[running=\"true\"] {{"
            f"  background: {p['stop_btn_bg']}; border: 1px solid {p['stop_btn_border']};"
            f"}}"
            f"QPushButton#HotkeyBtn {{"
            f"  background: {p['pill_bg']}; border: 1px solid {p['pill_border']};"
            f"  border-radius: 10px; padding: 4px 10px; font-size: 12px; color: {p['text_primary']};"
            f"}}"
            f"QPushButton#HotkeyBtn:hover {{ background: {p['pill_active_bg']}; border: 1px solid {p['pill_active_border']}; }}"
            f"QPushButton#HotkeyBtn:pressed {{ background: {p['accent'].format(a='0.12')}; }}"
            f"QLineEdit {{"
            f"  background: {p['input_bg']}; border: 1px solid {p['input_border']};"
            f"  border-radius: 10px; padding: 4px 10px; font-size: 12px; color: {p['text_primary']};"
            f"  selection-background-color: {p['combo_sel_bg']};"
            f"}}"
            f"QLineEdit:focus {{ border: 1px solid {p['pill_active_border']}; }}"
            f"QLineEdit#HotkeyBtn {{"
            f"  background: {p['pill_bg']}; border: 1px solid {p['pill_border']};"
            f"  border-radius: 10px; padding: 4px 10px; font-size: 12px; color: {p['text_primary']};"
            f"}}"
            f"QLineEdit#HotkeyBtn:focus {{ border: 1px solid {p['pill_active_border']}; }}"
            f"QTextEdit, QPlainTextEdit {{"
            f"  background: {p['input_bg']}; border: 1px solid {p['input_border']};"
            f"  border-radius: 10px; padding: 6px 10px; color: {p['text_primary']};"
            f"  selection-background-color: {p['combo_sel_bg']};"
            f"}}"
            f"QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {p['pill_active_border']}; }}"
            f"QScrollArea#MainScroll {{ background: transparent; border: none; }}"
            f"QScrollArea#MainScroll > QWidget > QWidget {{ background: transparent; }}"
            f"QScrollBar:vertical {{"
            f"  background: transparent; width: 0px; margin: 0;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"  background: transparent; min-height: 0px;"
            f"}}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
            f"QLabel#StatValue {{ font-size: 26px; font-weight: 800; color: {p['text_primary']}; }}"
            f"QLabel#StatLine {{"
            f"  font-size: 13px; color: {p['text_secondary']};"
            f"  padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.06);"
            f"}}"
            f"QSlider#Slider::groove:horizontal {{"
            f"  height: 6px; background: {p['slider_groove']}; border-radius: 3px;"
            f"}}"
            f"QSlider#Slider::handle:horizontal {{"
            f"  width: 18px; height: 18px; margin: -6px 0;"
            f"  background: {p['slider_handle']}; border-radius: 9px;"
            f"}}"
            f"QSlider#Slider::handle:horizontal:hover {{ background: {p['slider_handle']}; }}"
            f"QSlider#Slider::sub-page:horizontal {{"
            f"  background: {p['slider_sub']}; border-radius: 3px;"
            f"}}"
            f"QListWidget#PresetList {{"
            f"  background: {p['input_bg']}; border: 1px solid {p['input_border']};"
            f"  border-radius: 12px; padding: 6px; font-size: 13px; outline: none;"
            f"}}"
            f"QListWidget#PresetList::item {{"
            f"  padding: 10px 14px; border-radius: 8px; margin: 2px 0;"
            f"  color: {p['text_secondary']};"
            f"}}"
            f"QListWidget#PresetList::item:selected {{"
            f"  background: {p['accent'].format(a='0.20')}; color: {p['text_primary']};"
            f"}}"
            f"QListWidget#PresetList::item:hover {{"
            f"  background: {p['pill_bg']};"
            f"}}"
            f"QCheckBox {{ color: {p['text_secondary']}; font-size: 12.5px; spacing: 8px; }}"
            f"QCheckBox::indicator {{"
            f"  width: 18px; height: 18px; border-radius: 5px;"
            f"  border: 1px solid {p['checkbox_border']}; background: {p['checkbox_bg']};"
            f"}}"
            f"QCheckBox::indicator:hover {{"
            f"  border: 1px solid {p['checkbox_border']}; background: {p['checkbox_bg']};"
            f"}}"
            f"QCheckBox::indicator:checked {{"
            f"  background: {p['checkbox_checked']}; border: 1px solid {p['checkbox_checked_border']};"
            f"}}"
            f"QFrame#SettingsSeparator {{"
            f"  background: {p['card_border']}; border: none; min-height: 1px; max-height: 1px;"
            f"}}"
        )
        if hasattr(self, "page_home") and hasattr(self.page_home, "xp_bar"):
            self.page_home.xp_bar.set_theme(p)
        if hasattr(self, "page_stats") and hasattr(self.page_stats, "apply_theme"):
            self.page_stats.apply_theme(p)
        if hasattr(self, "page_achievements") and hasattr(self.page_achievements, "apply_theme"):
            self.page_achievements.apply_theme(p)
        self._apply_window_theme_effects(theme)
        self._update_window_mask()

    def _wire(self):
        self.btn_home.clicked.connect(lambda: self._switch_page(self.PAGE_HOME))
        self.btn_preset.clicked.connect(lambda: self._switch_page(self.PAGE_PRESET))
        self.btn_settings.clicked.connect(lambda: self._switch_page(self.PAGE_SETTINGS))
        self.btn_tokens.clicked.connect(lambda: self._switch_page(self.PAGE_TOKENS))
        self.btn_projects.clicked.connect(self._open_plugins_tab)
        self.btn_login.clicked.connect(lambda: self._switch_page(self.PAGE_LOGIN))
        self.btn_achievements.clicked.connect(lambda: self._switch_page(self.PAGE_ACHIEVEMENTS))
        self.btn_back.clicked.connect(lambda: self._switch_page(self.PAGE_HOME))

        if hasattr(self.page_home, "spin_interval"):
            self.page_home.spin_interval.valueChanged.connect(self._on_interval_changed)
            # Restore last saved click interval from settings JSON.
            try:
                data = self._load_persisted_settings()
                saved_interval = int(data.get("interval_ms", self.page_home.spin_interval.value()))
                saved_interval = max(1, min(86400000, saved_interval))
                self.page_home.spin_interval.blockSignals(True)
                self.page_home.spin_interval.setValue(saved_interval)
                self.page_home.spin_interval.blockSignals(False)
                self.config.interval_ms = saved_interval
            except Exception:
                pass

        self.btn_hotkey.clicked.connect(self._on_hotkey_btn_clicked)
        self.page_home.btn_start_stop.clicked.connect(self._toggle_autoclicker)
        self.runner.started.connect(lambda: self.page_home.set_running_state(True))
        self.runner.stopped.connect(lambda: self.page_home.set_running_state(False))
        self.runner.click_performed.connect(self._on_click_performed)
        self.runner.click_at_position.connect(self._on_click_at_position)
        self.runner.cps_adjusted.connect(self._on_cps_adjusted)
        self.runner.started.connect(self._on_session_start)
        self.runner.stopped.connect(self._on_session_stop)

        # Sound on start/stop
        self.runner.started.connect(self._play_start_sound)
        self.runner.stopped.connect(self._play_stop_sound)

        # Preset page
        self.page_preset.btn_new.clicked.disconnect()  # disconnect the stub
        self.page_preset.btn_new.clicked.connect(self._on_new_preset)
        self.page_preset.preset_loaded.connect(self._on_load_preset)

        # Language change
        self.page_settings.language_changed.connect(self._on_language_changed)

        # Scroll keybind
        self.page_settings.scroll_key_changed.connect(self._on_scroll_key_changed)
        self._scroll_key = self.page_settings.get_scroll_key()
        self._scroll_hotkey_enabled = self.page_settings.get_scroll_hotkey_enabled()
        self._emergency_key = self.page_settings.get_emergency_key()
        self._switch_mouse_button_key = self.page_settings.get_switch_mouse_button_key()
        self._toggle_both_mouse_key = self.page_settings.get_toggle_both_mouse_key()
        self.page_settings.scroll_hotkey_enabled_changed.connect(self._on_scroll_hotkey_enabled_changed)
        self.page_settings.emergency_key_changed.connect(self._on_emergency_key_changed)
        self.page_settings.switch_mouse_button_key_changed.connect(self._on_switch_mouse_button_key_changed)
        self.page_settings.toggle_both_mouse_key_changed.connect(self._on_toggle_both_mouse_key_changed)
        self._lag_guard_enabled, self._lag_guard_threshold, self._lag_guard_events = self.page_settings.get_lag_guard_settings()
        self._blocked_programs_enabled, blocked = self.page_settings.get_blocked_programs_settings()
        self._blocked_programs = set(blocked)
        self._performance_mode = self.page_settings.get_performance_mode()
        self.page_settings.performance_mode_changed.connect(self._on_performance_mode_changed)

        # Secret admin panel
        self.page_home.admin_activated.connect(self._activate_admin_panel)

        # Theme support
        self.page_settings.set_stats_ref(self.stats)
        self.page_settings.theme_changed.connect(self._on_theme_changed)

        # Phasmophobia reference window
        self._phasmophobia_window = None
        self._phasmophobia_active = False

        # Plugin install/delete controls follow marketplace flow.
        for key, btn in getattr(self.page_projects, "_install_buttons", {}).items():
            btn.clicked.connect(lambda _=False, k=key: self._install_marketplace_plugin(self._plugin_id_for_project(k)))
        for key, btn in getattr(self.page_projects, "_delete_buttons", {}).items():
            btn.clicked.connect(lambda _=False, k=key: self._remove_marketplace_plugin(self._plugin_id_for_project(k)))
        self.page_marketplace.install_requested.connect(self._install_marketplace_plugin)
        self.page_marketplace.refresh_requested.connect(self._refresh_plugin_page_state)

        # Compact overlay
        self._overlay = CompactOverlay()
        self._overlay.btn_toggle.clicked.connect(self._toggle_autoclicker)
        self.page_settings.overlay_toggled.connect(self._on_overlay_toggled)
        self._overlay.set_hotkey(self._hotkey_char)
        if self.page_settings.chk_overlay.isChecked():
            self._overlay.show()

        self._init_search_index()
        self.input_search.textEdited.connect(self._update_search_suggestions)
        self.input_search.returnPressed.connect(self._on_topbar_action)
        self.btn_search.clicked.connect(self._on_topbar_action)

        self._overlay_time = QTimer(self)
        self._overlay_time.setInterval(1000)
        self._overlay_time.timeout.connect(self._tick_overlay_time)

        self._topbar_action = self.page_settings.get_topbar_action()
        self.page_settings.topbar_action_changed.connect(self._on_topbar_action_changed)
        self.page_settings.sidebar_config_changed.connect(self._on_sidebar_config_changed)
        self._on_topbar_action_changed(self._topbar_action)
        self._update_top_avg_cps()
        self._apply_sidebar_preferences(self.page_settings.get_sidebar_preferences())

        # Initial XP bar sync
        self._refresh_xp_bar()

    # ── Achievement toast helpers ──────────────────────
    def _snapshot_achievements(self):
        """Record the set of currently-earned achievement names."""
        earned = set()
        for cat in self.stats.get_categorized_achievements():
            for _icon, name, _desc, is_earned in cat["achievements"]:
                if is_earned:
                    earned.add(name)
        self._achievement_snapshot = earned

    def _check_new_achievements(self):
        """Compare current achievements against snapshot and toast any new ones."""
        earned_now = set()
        for cat in self.stats.get_categorized_achievements():
            for _icon, name, _desc, is_earned in cat["achievements"]:
                if is_earned:
                    earned_now.add(name)
        new = earned_now - self._achievement_snapshot
        if new:
            self._achievement_snapshot = earned_now
            theme = get_theme()
            p = theme["palette"]
            for name in sorted(new):
                toast = ToastNotification(
                    f"GG! You unlocked {name}",
                    bg_color=p["config_card"],
                    border_color=p.get("pill_active_border", "rgba(78,141,255,0.28)"),
                    text_color=p["text_primary"],
                    icon="\U0001F3C6",
                )
                toast.show_toast()

    def _on_theme_changed(self, theme_id: str):
        """Apply a new theme when the user selects one."""
        self._apply_styles(theme_id)
        if self._phasmophobia_window is not None:
            self._phasmophobia_window.apply_theme(theme_id)

    def _open_phasmophobia(self):
        """Open the Phasmophobia cheat-sheet window and hide the autoclicker."""
        try:
            if self._phasmophobia_window is None:
                self._phasmophobia_window = PhasmophobiaWindow()
                self._phasmophobia_window.go_back_to_autoclicker.connect(self._return_from_phasmophobia)
            self._phasmophobia_window.apply_theme(get_selected_theme_id())
            self._phasmophobia_active = True
            if not self._phasmophobia_window.isVisible():
                self._phasmophobia_window.resize(1900, 1080)
            self._phasmophobia_window.move(self.pos())
            self._phasmophobia_window.show()
            self.hide()
        except Exception as exc:
            self._phasmophobia_active = False
            self._show_status_toast(f"Phasmophobia failed to open: {exc}", icon="\u26A0")

    def _return_from_phasmophobia(self):
        """Return to the autoclicker from the Phasmophobia window."""
        self._phasmophobia_active = False
        if self._phasmophobia_window:
            self._phasmophobia_window.hide()
        self.show()

    def _plugin_path_for_project(self, project_key: str) -> Path | None:
        fname = getattr(self.page_projects, "_plugin_files", {}).get(project_key)
        if not fname:
            return None
        return self._plugin_manager.registry_dir / fname

    def _plugin_id_for_project(self, project_key: str) -> str:
        fname = getattr(self.page_projects, "_plugin_files", {}).get(project_key, "")
        return Path(fname).stem if fname else ""

    def _project_plugin_template(self, project_key: str) -> str:
        return _textwrap.dedent(
            """\
            def register(context: dict) -> dict:
                return {
                    \"id\": \"removed_plugin\",
                    \"name\": \"Removed Plugin\",
                    \"version\": \"0.0.0\",
                    \"description\": \"This plugin was removed from the release build.\",
                }
            """
        )

    def _refresh_plugin_page_state(self):
        for key, status_lbl in getattr(self.page_projects, "_status_labels", {}).items():
            p = self._plugin_path_for_project(key)
            installed = bool(p and p.exists())
            status_lbl.setText("Status: Installed" if installed else "Status: Not installed")

            open_btn = getattr(self.page_projects, "_project_buttons", {}).get(key)
            if open_btn:
                open_btn.setEnabled(installed)

            install_btn = getattr(self.page_projects, "_install_buttons", {}).get(key)
            if install_btn:
                install_btn.setEnabled(not installed)

            delete_btn = getattr(self.page_projects, "_delete_buttons", {}).get(key)
            if delete_btn:
                delete_btn.setEnabled(installed)
        if hasattr(self, "page_marketplace"):
            self.page_marketplace.refresh_plugins(
                self._plugin_manager.records(),
                catalog=self._marketplace_catalog(),
            )
        self._refresh_projects_manage_list()

    def _refresh_projects_manage_list(self):
        lay = getattr(self.page_projects, "_managed_plugins_layout", None)
        if lay is None:
            return
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        records = sorted(self._plugin_manager.records(), key=lambda r: str(getattr(r, "name", "")).lower())
        if not records:
            empty = QLabel("No plugins installed yet.")
            empty.setObjectName("WarnText")
            lay.addWidget(empty, 0, 0, 1, 2)
            return

        emoji_map = {
            "route_recorder_plugin": "\U0001F6E3",
            "input_humanization_plugin": "\u23F1",
            "preset_benchmark_plugin": "\U0001F3C1",
            "phasmopobia_plugin": "\U0001F47B",
            "example_plugin": "\U0001F9EA",
        }

        for idx, rec in enumerate(records):
            card = Card()
            card.setObjectName("ConfigCard")
            add_shadow(card, blur=18, y=6, alpha=90)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 14, 16, 14)
            cl.setSpacing(8)

            icon_btn = QPushButton(emoji_map.get(rec.plugin_id, "\U0001F9E9"))
            icon_btn.setObjectName("IconBtn")
            icon_btn.setFixedSize(44, 44)
            icon_btn.setCursor(Qt.PointingHandCursor)
            icon_btn.clicked.connect(lambda _=False, pid=rec.plugin_id: self._open_plugin_options(pid))

            title = QLabel(rec.name)
            title.setObjectName("CardHeader")
            desc = QLabel(rec.description)
            desc.setObjectName("HeroSub")
            desc.setWordWrap(True)
            status = QLabel(f"Status: {'Loaded' if rec.loaded else 'Failed'}")
            status.setObjectName("WarnText")

            row = QHBoxLayout()
            row.setSpacing(8)
            btn_options = QPushButton("Options")
            btn_options.setObjectName("HotkeyBtn")
            btn_options.setCursor(Qt.PointingHandCursor)
            btn_options.clicked.connect(lambda _=False, pid=rec.plugin_id: self._open_plugin_options(pid))
            btn_remove = QPushButton("Remove")
            btn_remove.setObjectName("HotkeyBtn")
            btn_remove.setCursor(Qt.PointingHandCursor)
            btn_remove.clicked.connect(lambda _=False, pid=rec.plugin_id: self._remove_marketplace_plugin(pid))
            row.addWidget(btn_options)
            row.addWidget(btn_remove)
            row.addStretch(1)

            cl.addWidget(icon_btn)
            cl.addWidget(title)
            cl.addWidget(desc)
            cl.addWidget(status)
            cl.addLayout(row)

            row_idx = idx // 2
            col_idx = idx % 2
            lay.addWidget(card, row_idx, col_idx)

    def _open_plugin_options(self, plugin_id: str):
        plugin_id = (plugin_id or "").strip()
        if not plugin_id:
            return
        if plugin_id == "phasmopobia_plugin":
            self._open_phasmophobia()
            return
        if plugin_id == "route_recorder_plugin":
            self._open_route_recorder_plugin_page()
            return
        self._open_plugin_json_gui(plugin_id)

    def _ensure_plugin_config(self, plugin_id: str) -> Path:
        cfg_path = self._plugin_manager.registry_dir / f"{plugin_id}.json"
        if not cfg_path.exists():
            cfg_path.write_text(_json.dumps(self._default_plugin_options(plugin_id), indent=2), encoding="utf-8")
        return cfg_path

    def _is_plugin_loaded(self, plugin_id: str) -> bool:
        pid = (plugin_id or "").strip()
        if not pid:
            return False
        for rec in self._plugin_manager.records():
            if str(getattr(rec, "plugin_id", "")).strip() == pid and bool(getattr(rec, "loaded", False)):
                return True
        return False

    def _open_plugin_json_gui(self, plugin_id: str):
        cfg_path = self._ensure_plugin_config(plugin_id)

        try:
            data = _json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            data = self._default_plugin_options(plugin_id)
        self._render_plugin_options_page(plugin_id, cfg_path, data)
        self._switch_page(self.PAGE_PLUGIN_OPTIONS)

    def _route_recordings_path(self) -> Path:
        return Path.home() / ".mtautoclicker_route_recorder_routes.json"

    def _load_route_recordings(self) -> list[dict]:
        p = self._route_recordings_path()
        if not p.exists():
            legacy = self._plugin_manager.registry_dir / "route_recorder_routes.json"
            if not legacy.exists():
                return []
            p = legacy
        try:
            raw = _json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [r for r in raw if isinstance(r, dict)]
        except Exception:
            pass
        return []

    def _save_route_recordings(self, records: list[dict]):
        p = self._route_recordings_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_json.dumps(records, indent=2), encoding="utf-8")

    def _open_route_recorder_plugin_page(self):
        plugin_id = "route_recorder_plugin"
        cfg_path = self._ensure_plugin_config(plugin_id)
        try:
            data = _json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            data = self._default_plugin_options(plugin_id)
        self._rr_cfg_cache = dict(data)

        page = self.page_plugin_options
        form = page._po_form
        self._clear_form_rows(form)

        page._po_plugin_id = plugin_id
        page._po_cfg_path = cfg_path
        page._po_editors = {}
        page._po_custom_save = lambda: self._save_route_recorder_plugin_options(page)
        page._po_title.setText("Route Recorder")
        page._po_subtitle.setText("Record full keyboard + mouse routes globally, then execute them on demand.")

        panel = Card(radius=12)
        panel.setObjectName("InnerPanel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(12, 12, 12, 12)
        pl.setSpacing(10)

        row0 = QHBoxLayout()
        chk_enabled = QCheckBox("Enabled")
        chk_enabled.setChecked(bool(data.get("enabled", True)))
        lbl_status = QLabel(self._rr_status_text)
        lbl_status.setObjectName("WarnText")
        row0.addWidget(chk_enabled)
        row0.addStretch(1)
        row0.addWidget(lbl_status)
        pl.addLayout(row0)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        lbl_rec_hk = QLabel("Record Hotkey")
        lbl_rec_hk.setObjectName("WarnText")
        input_rec_hk = QLineEdit(str(data.get("record_hotkey", "f8")))
        input_rec_hk.setPlaceholderText("f8")
        input_rec_hk.setFixedWidth(90)
        lbl_exec_hk = QLabel("Execute Hotkey")
        lbl_exec_hk.setObjectName("WarnText")
        input_exec_hk = QLineEdit(str(data.get("execute_hotkey", "f9")))
        input_exec_hk.setPlaceholderText("f9")
        input_exec_hk.setFixedWidth(90)
        row1.addWidget(lbl_rec_hk)
        row1.addWidget(input_rec_hk)
        row1.addSpacing(12)
        row1.addWidget(lbl_exec_hk)
        row1.addWidget(input_exec_hk)
        row1.addStretch(1)
        pl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        lbl_name = QLabel("Recording Name")
        lbl_name.setObjectName("WarnText")
        input_name = QLineEdit(str(data.get("record_name", "")))
        input_name.setPlaceholderText("My route")
        combo_recordings = QComboBox()
        combo_recordings.setObjectName("DropDown")
        row2.addWidget(lbl_name)
        row2.addWidget(input_name, 2)
        row2.addWidget(combo_recordings, 2)
        pl.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(8)
        chk_keyboard = QCheckBox("Record Keyboard")
        chk_keyboard.setChecked(bool(data.get("record_keyboard", True)))
        chk_move = QCheckBox("Record Mouse Move")
        chk_move.setChecked(bool(data.get("record_mouse_move", True)))
        chk_clicks = QCheckBox("Record Clicks")
        chk_clicks.setChecked(bool(data.get("record_clicks", True)))
        chk_scroll = QCheckBox("Record Scroll")
        chk_scroll.setChecked(bool(data.get("record_scroll", True)))
        row3.addWidget(chk_keyboard)
        row3.addWidget(chk_move)
        row3.addWidget(chk_clicks)
        row3.addWidget(chk_scroll)
        row3.addStretch(1)
        pl.addLayout(row3)

        row4 = QHBoxLayout()
        row4.setSpacing(8)
        lbl_sampling = QLabel("Sampling (ms)")
        lbl_sampling.setObjectName("WarnText")
        spin_sampling = QSpinBox()
        spin_sampling.setObjectName("Spin")
        spin_sampling.setRange(1, 100)
        spin_sampling.setValue(int(data.get("sampling_ms", 8)))
        lbl_speed = QLabel("Playback Speed")
        lbl_speed.setObjectName("WarnText")
        spin_speed = QDoubleSpinBox()
        spin_speed.setObjectName("Spin")
        spin_speed.setRange(0.10, 10.0)
        spin_speed.setDecimals(2)
        spin_speed.setSingleStep(0.05)
        spin_speed.setValue(float(data.get("playback_speed", 1.0)))
        lbl_jitter = QLabel("Jitter (px)")
        lbl_jitter.setObjectName("WarnText")
        spin_jitter = QSpinBox()
        spin_jitter.setObjectName("Spin")
        spin_jitter.setRange(0, 20)
        spin_jitter.setValue(int(data.get("jitter_px", 1)))
        row4.addWidget(lbl_sampling)
        row4.addWidget(spin_sampling)
        row4.addWidget(lbl_speed)
        row4.addWidget(spin_speed)
        row4.addWidget(lbl_jitter)
        row4.addWidget(spin_jitter)
        row4.addStretch(1)
        pl.addLayout(row4)

        row5 = QHBoxLayout()
        row5.setSpacing(8)
        lbl_max_points = QLabel("Max Points")
        lbl_max_points.setObjectName("WarnText")
        spin_max_points = QSpinBox()
        spin_max_points.setObjectName("Spin")
        spin_max_points.setRange(100, 100_000)
        spin_max_points.setValue(int(data.get("max_points", 5000)))
        lbl_max_saved = QLabel("Max Saved Routes")
        lbl_max_saved.setObjectName("WarnText")
        spin_max_saved = QSpinBox()
        spin_max_saved.setObjectName("Spin")
        spin_max_saved.setRange(1, 200)
        spin_max_saved.setValue(int(data.get("max_saved_routes", 40)))
        chk_game_mode = QCheckBox("Game Mode (Relative Mouse Playback)")
        chk_game_mode.setChecked(bool(data.get("game_mode_relative_mouse", True)))
        row5.addWidget(lbl_max_points)
        row5.addWidget(spin_max_points)
        row5.addWidget(lbl_max_saved)
        row5.addWidget(spin_max_saved)
        row5.addWidget(chk_game_mode)
        row5.addStretch(1)
        pl.addLayout(row5)

        row6 = QHBoxLayout()
        row6.setSpacing(8)
        btn_toggle_record = QPushButton("Start Recording")
        btn_toggle_record.setObjectName("StartStopBtn")
        btn_execute = QPushButton("Execute Selected")
        btn_execute.setObjectName("ToggleButton")
        btn_refresh = QPushButton("Refresh List")
        btn_refresh.setObjectName("HotkeyBtn")
        row6.addWidget(btn_toggle_record)
        row6.addWidget(btn_execute)
        row6.addWidget(btn_refresh)
        row6.addStretch(1)
        pl.addLayout(row6)

        form.addRow(panel)

        page._po_route_widgets = {
            "enabled": chk_enabled,
            "record_hotkey": input_rec_hk,
            "execute_hotkey": input_exec_hk,
            "record_name": input_name,
            "selected": combo_recordings,
            "record_keyboard": chk_keyboard,
            "record_mouse_move": chk_move,
            "record_clicks": chk_clicks,
            "record_scroll": chk_scroll,
            "sampling_ms": spin_sampling,
            "playback_speed": spin_speed,
            "jitter_px": spin_jitter,
            "max_points": spin_max_points,
            "max_saved_routes": spin_max_saved,
            "game_mode_relative_mouse": chk_game_mode,
            "status": lbl_status,
            "btn_toggle_record": btn_toggle_record,
        }

        btn_toggle_record.clicked.connect(self._toggle_route_recording_from_ui)
        btn_execute.clicked.connect(lambda: self._execute_route_recording(from_hotkey=False))
        btn_refresh.clicked.connect(self._refresh_route_recordings_combo)
        combo_recordings.currentTextChanged.connect(lambda _v: self._save_route_recorder_plugin_options(page, show_toast=False))
        self._refresh_route_recordings_combo()
        selected = str(data.get("selected_recording", "")).strip()
        if selected:
            combo_recordings.setCurrentText(selected)
        self._update_route_recording_ui_state()
        self._switch_page(self.PAGE_PLUGIN_OPTIONS)

    def _refresh_route_recordings_combo(self):
        page = getattr(self, "page_plugin_options", None)
        widgets = getattr(page, "_po_route_widgets", {}) or {}
        combo = widgets.get("selected")
        if combo is None:
            return
        current = str(combo.currentText()).strip()
        records = self._load_route_recordings()
        names = [str(r.get("name", "")).strip() for r in records if str(r.get("name", "")).strip()]
        if not current:
            cfg = self._route_cfg()
            current = str(cfg.get("selected_recording", "")).strip()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(names)
        if current and current in names:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _save_route_recorder_plugin_options(self, page, show_toast: bool = True):
        cfg_path = page._po_cfg_path
        if cfg_path is None:
            return
        w = getattr(page, "_po_route_widgets", {}) or {}
        if not w:
            return
        data = {
            "enabled": bool(w["enabled"].isChecked()),
            "record_hotkey": str(w["record_hotkey"].text()).strip().lower() or "f8",
            "execute_hotkey": str(w["execute_hotkey"].text()).strip().lower() or "f9",
            "record_name": str(w["record_name"].text()).strip(),
            "selected_recording": str(w["selected"].currentText()).strip(),
            "record_keyboard": bool(w["record_keyboard"].isChecked()),
            "record_mouse_move": bool(w["record_mouse_move"].isChecked()),
            "record_clicks": bool(w["record_clicks"].isChecked()),
            "record_scroll": bool(w["record_scroll"].isChecked()),
            "max_points": int(w["max_points"].value()),
            "sampling_ms": int(w["sampling_ms"].value()),
            "playback_speed": float(w["playback_speed"].value()),
            "jitter_px": int(w["jitter_px"].value()),
            "game_mode_relative_mouse": bool(w["game_mode_relative_mouse"].isChecked()),
            "max_saved_routes": int(w["max_saved_routes"].value()),
        }
        self._rr_cfg_cache = dict(data)
        cfg_path.write_text(_json.dumps(data, indent=2), encoding="utf-8")
        if show_toast:
            self._show_status_toast("Saved options: route_recorder_plugin", icon="\u2705")

    def _route_cfg(self) -> dict:
        if self._rr_cfg_cache is not None:
            return self._rr_cfg_cache
        cfg_path = self._ensure_plugin_config("route_recorder_plugin")
        try:
            self._rr_cfg_cache = _json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            self._rr_cfg_cache = self._default_plugin_options("route_recorder_plugin")
        return self._rr_cfg_cache

    def _route_capture_event(self, event: dict):
        if not self._rr_recording:
            return
        cfg = self._route_cfg()
        max_points = max(100, int(cfg.get("max_points", 5000)))
        if len(self._rr_events) >= max_points:
            return
        self._rr_events.append(event)

    def _route_timestamp_ms(self) -> int:
        if self._rr_record_start <= 0:
            return 0
        return int(max(0.0, (_time_module.perf_counter() - self._rr_record_start) * 1000.0))

    def _on_route_keyboard_event(self, token: str, is_down: bool):
        if not self._rr_recording:
            return
        cfg = self._route_cfg()
        if not bool(cfg.get("record_keyboard", True)):
            return
        rec_hk = str(cfg.get("record_hotkey", "f8")).strip().lower() or "f8"
        exe_hk = str(cfg.get("execute_hotkey", "f9")).strip().lower() or "f9"
        if token in {rec_hk, exe_hk}:
            return
        self._route_capture_event({
            "t": self._route_timestamp_ms(),
            "type": "key",
            "token": str(token),
            "down": bool(is_down),
        })

    def _on_route_mouse_button_event(self, token: str, is_down: bool, x: int, y: int):
        if not self._rr_recording:
            return
        cfg = self._route_cfg()
        if not bool(cfg.get("record_clicks", True)):
            return
        self._route_capture_event({
            "t": self._route_timestamp_ms(),
            "type": "mouse_button",
            "token": str(token),
            "down": bool(is_down),
            "x": int(x),
            "y": int(y),
        })

    def _on_route_mouse_move_event(self, x: int, y: int):
        if not self._rr_recording:
            return
        cfg = self._route_cfg()
        if not bool(cfg.get("record_mouse_move", True)):
            return
        now = _time_module.perf_counter()
        sampling_ms = max(1, int(cfg.get("sampling_ms", 8)))
        if self._rr_last_move_ts > 0 and (now - self._rr_last_move_ts) * 1000.0 < sampling_ms:
            return
        last = self._rr_last_pos
        if last is None:
            dx, dy = 0, 0
        else:
            dx, dy = int(x - last[0]), int(y - last[1])
        self._rr_last_move_ts = now
        self._rr_last_pos = (int(x), int(y))
        self._route_capture_event({
            "t": self._route_timestamp_ms(),
            "type": "mouse_move",
            "x": int(x),
            "y": int(y),
            "dx": int(dx),
            "dy": int(dy),
        })

    def _on_route_mouse_scroll_event(self, x: int, y: int, dx: int, dy: int):
        if not self._rr_recording:
            return
        cfg = self._route_cfg()
        if not bool(cfg.get("record_scroll", True)):
            return
        self._route_capture_event({
            "t": self._route_timestamp_ms(),
            "type": "mouse_scroll",
            "x": int(x),
            "y": int(y),
            "dx": int(dx),
            "dy": int(dy),
        })

    def _toggle_route_recording_from_ui(self):
        if self._rr_recording:
            self._stop_route_recording()
        else:
            self._start_route_recording()

    def _start_route_recording(self):
        if self._rr_playing:
            self._show_status_toast("Stop playback before recording", icon="\u26A0")
            return
        cfg = self._route_cfg()
        if not bool(cfg.get("enabled", True)):
            self._show_status_toast("Route Recorder is disabled", icon="\u26A0")
            return
        self._rr_events = []
        self._rr_recording = True
        self._rr_record_start = _time_module.perf_counter()
        self._rr_last_move_ts = 0.0
        try:
            self._rr_last_pos = MouseController().position
        except Exception:
            self._rr_last_pos = None
        self._rr_status_text = "Recording..."
        self._update_route_recording_ui_state()
        self._show_status_toast("Route recording started", icon="\u25CF")

    def _stop_route_recording(self):
        if not self._rr_recording:
            return
        self._rr_recording = False
        dur_ms = int(max(0.0, (_time_module.perf_counter() - self._rr_record_start) * 1000.0))
        cfg = self._route_cfg()
        page = getattr(self, "page_plugin_options", None)
        w = getattr(page, "_po_route_widgets", {}) or {}
        base_name = ""
        if w:
            base_name = str(w.get("record_name").text()).strip()
        if not base_name:
            base_name = str(cfg.get("record_name", "")).strip()
        if not base_name:
            base_name = datetime.now().strftime("Route %Y-%m-%d %H:%M:%S")

        rec = {
            "name": base_name,
            "created_at": datetime.now().isoformat(),
            "duration_ms": dur_ms,
            "events": self._rr_events,
        }
        records = self._load_route_recordings()
        records = [r for r in records if str(r.get("name", "")).strip() != base_name]
        records.append(rec)
        max_saved = max(1, int(cfg.get("max_saved_routes", 40)))
        if len(records) > max_saved:
            records = records[-max_saved:]
        self._save_route_recordings(records)
        self._rr_status_text = f"Saved '{base_name}' ({len(self._rr_events)} events)"
        self._update_route_recording_ui_state()
        self._refresh_route_recordings_combo()
        self._show_status_toast(f"Route saved: {base_name}", icon="\u2705")

    def _update_route_recording_ui_state(self):
        page = getattr(self, "page_plugin_options", None)
        if page is None or getattr(page, "_po_plugin_id", "") != "route_recorder_plugin":
            return
        w = getattr(page, "_po_route_widgets", {}) or {}
        if not w:
            return
        status = w.get("status")
        btn = w.get("btn_toggle_record")
        if status is not None:
            status.setText(self._rr_status_text)
        if btn is not None:
            btn.setText("Stop Recording" if self._rr_recording else "Start Recording")

    def _try_route_recorder_hotkey(self, token: str) -> bool:
        if not self._is_plugin_loaded("route_recorder_plugin"):
            return False
        cfg = self._route_cfg()
        if not bool(cfg.get("enabled", True)):
            return False
        rec_hotkey = str(cfg.get("record_hotkey", "f8")).strip().lower() or "f8"
        exe_hotkey = str(cfg.get("execute_hotkey", "f9")).strip().lower() or "f9"
        if token == rec_hotkey:
            if self._rr_recording:
                self._stop_route_recording()
            else:
                self._start_route_recording()
            return True
        if token == exe_hotkey:
            self._execute_route_recording(from_hotkey=True)
            return True
        return False

    def _keyboard_key_from_token(self, token: str):
        t = (token or "").strip().lower()
        if not t:
            return None
        key_map = {
            "space": keyboard.Key.space,
            "enter": keyboard.Key.enter,
            "tab": keyboard.Key.tab,
            "backspace": keyboard.Key.backspace,
            "esc": keyboard.Key.esc,
            "shift": keyboard.Key.shift,
            "shift_l": keyboard.Key.shift_l,
            "shift_r": keyboard.Key.shift_r,
            "ctrl": keyboard.Key.ctrl,
            "ctrl_l": keyboard.Key.ctrl_l,
            "ctrl_r": keyboard.Key.ctrl_r,
            "alt": keyboard.Key.alt,
            "alt_l": keyboard.Key.alt_l,
            "alt_r": keyboard.Key.alt_r,
            "up": keyboard.Key.up,
            "down": keyboard.Key.down,
            "left": keyboard.Key.left,
            "right": keyboard.Key.right,
        }
        if t in key_map:
            return key_map[t]
        fn = getattr(keyboard.Key, t, None)
        if fn is not None:
            return fn
        if len(t) == 1:
            return keyboard.KeyCode.from_char(t)
        return None

    def _mouse_button_from_token(self, token: str):
        t = (token or "").strip().lower()
        if t == "mouse_left":
            return _mouse.Button.left
        if t == "mouse_right":
            return _mouse.Button.right
        if t == "mouse_middle":
            return _mouse.Button.middle
        return None

    def _emit_relative_mouse(self, dx: int, dy: int):
        if not self._is_windows or not getattr(_ctypes, "windll", None):
            return
        try:
            _ctypes.windll.user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)
        except Exception:
            pass

    def _execute_route_recording(self, from_hotkey: bool):
        if self._rr_recording:
            if not from_hotkey:
                self._show_status_toast("Stop recording before playback", icon="\u26A0")
            return
        if self._rr_playing:
            if not from_hotkey:
                self._show_status_toast("Route playback already running", icon="\u26A0")
            return
        cfg = self._route_cfg()
        if not bool(cfg.get("enabled", True)):
            if not from_hotkey:
                self._show_status_toast("Route Recorder is disabled", icon="\u26A0")
            return
        selected = str(cfg.get("selected_recording", "")).strip()
        page = getattr(self, "page_plugin_options", None)
        w = getattr(page, "_po_route_widgets", {}) or {}
        if w and w.get("selected") is not None:
            selected = str(w["selected"].currentText()).strip() or selected
        records = self._load_route_recordings()
        rec = None
        if selected:
            for r in reversed(records):
                if str(r.get("name", "")).strip() == selected:
                    rec = r
                    break
        if rec is None and records:
            rec = records[-1]
        if rec is None:
            if not from_hotkey:
                self._show_status_toast("No route recordings found", icon="\u26A0")
            return

        speed = max(0.10, float(cfg.get("playback_speed", 1.0)))
        jitter_px = max(0, int(cfg.get("jitter_px", 0)))
        rel_mode = bool(cfg.get("game_mode_relative_mouse", True))
        events = list(rec.get("events", []))
        if not events:
            if not from_hotkey:
                self._show_status_toast("Selected route is empty", icon="\u26A0")
            return

        self._rr_playing = True
        self._rr_status_text = f"Playing '{str(rec.get('name', 'route'))}'..."
        self._update_route_recording_ui_state()

        def _worker():
            kb = keyboard.Controller()
            ms = MouseController()
            last_t = 0
            try:
                for ev in events:
                    t = int(ev.get("t", 0))
                    dt = max(0, t - last_t)
                    last_t = t
                    _time_module.sleep((dt / 1000.0) / speed)
                    et = str(ev.get("type", ""))

                    if et == "key":
                        kk = self._keyboard_key_from_token(str(ev.get("token", "")))
                        if kk is None:
                            continue
                        if bool(ev.get("down", True)):
                            kb.press(kk)
                        else:
                            kb.release(kk)
                    elif et == "mouse_button":
                        mb = self._mouse_button_from_token(str(ev.get("token", "")))
                        if mb is None:
                            continue
                        if bool(ev.get("down", True)):
                            ms.press(mb)
                        else:
                            ms.release(mb)
                    elif et == "mouse_move":
                        dx = int(ev.get("dx", 0))
                        dy = int(ev.get("dy", 0))
                        if jitter_px > 0:
                            dx += int((_time_module.time() * 1000) % (2 * jitter_px + 1)) - jitter_px
                            dy += int((_time_module.time() * 1337) % (2 * jitter_px + 1)) - jitter_px
                        if rel_mode:
                            self._emit_relative_mouse(dx, dy)
                        else:
                            x = int(ev.get("x", 0))
                            y = int(ev.get("y", 0))
                            ms.position = (max(0, x + dx), max(0, y + dy))
                    elif et == "mouse_scroll":
                        ms.scroll(int(ev.get("dx", 0)), int(ev.get("dy", 0)))
            except Exception:
                pass
            finally:
                self._rr_playing = False
                self._rr_status_text = "Idle"
                QTimer.singleShot(0, self._update_route_recording_ui_state)

        _th.Thread(target=_worker, daemon=True).start()
        if not from_hotkey:
            self._show_status_toast(f"Executing route: {str(rec.get('name', 'route'))}", icon="\u25B6")

    def _make_plugin_options_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=24, y=8, alpha=95)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24, 18, 24, 18)
        hl.setSpacing(8)

        title = QLabel("Plugin Options")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("Configure installed plugin settings in-app.")
        subtitle.setObjectName("HeroSub")
        subtitle.setWordWrap(True)
        hl.addWidget(title)
        hl.addWidget(subtitle)

        panel = Card()
        panel.setObjectName("ConfigCard")
        add_shadow(panel, blur=20, y=6, alpha=90)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        pl.addLayout(form)

        row = QHBoxLayout()
        row.addStretch(1)
        btn_back = QPushButton("Back")
        btn_back.setObjectName("HotkeyBtn")
        btn_save = QPushButton("Save")
        btn_save.setObjectName("StartStopBtn")
        row.addWidget(btn_back)
        row.addWidget(btn_save)
        pl.addLayout(row)

        lay.addWidget(hero)
        lay.addWidget(panel)
        lay.addStretch(1)

        page._po_title = title
        page._po_subtitle = subtitle
        page._po_form = form
        page._po_back_btn = btn_back
        page._po_save_btn = btn_save
        page._po_editors = {}
        page._po_cfg_path = None
        page._po_plugin_id = ""
        page._po_custom_save = None
        page._po_instant_up_widgets = {}
        page._po_route_widgets = {}

        btn_back.clicked.connect(lambda: self._switch_page(self.PAGE_PROJECTS))
        btn_save.clicked.connect(self._save_current_plugin_options_page)
        return page

    def _clear_form_rows(self, form: QFormLayout):
        while form.rowCount() > 0:
            form.removeRow(0)

    def _render_plugin_options_page(self, plugin_id: str, cfg_path: Path, data: dict):
        page = self.page_plugin_options
        form = page._po_form
        self._clear_form_rows(form)

        page._po_plugin_id = plugin_id
        page._po_cfg_path = cfg_path
        page._po_editors = {}
        page._po_custom_save = None
        page._po_kahoot_widgets = {}
        page._po_instant_up_widgets = {}
        page._po_route_widgets = {}
        page._po_title.setText(f"Plugin Options - {plugin_id}")
        page._po_subtitle.setText("Adjust values, then press Save. Changes apply to this plugin config file.")

        key_order = sorted(data.keys(), key=lambda k: (k != "enabled", str(k).lower()))
        editors = {}
        for key in key_order:
            value = data.get(key)
            label = QLabel(str(key).replace("_", " ").title())
            label.setObjectName("WarnText")

            if isinstance(value, bool):
                w = QCheckBox("Enabled" if key == "enabled" else "On")
                w.setChecked(bool(value))
                editors[key] = ("bool", w)
                form.addRow(label, w)
                continue

            if isinstance(value, int) and not isinstance(value, bool):
                w = QSpinBox()
                w.setRange(-1_000_000, 1_000_000)
                w.setValue(int(value))
                w.setObjectName("Spin")
                editors[key] = ("int", w)
                form.addRow(label, w)
                continue

            if isinstance(value, float):
                w = QDoubleSpinBox()
                w.setRange(-1_000_000.0, 1_000_000.0)
                w.setDecimals(4)
                w.setSingleStep(0.1)
                w.setValue(float(value))
                w.setObjectName("Spin")
                editors[key] = ("float", w)
                form.addRow(label, w)
                continue

            if isinstance(value, str):
                choices = self._plugin_option_choices(plugin_id, key)
                if choices:
                    w = QComboBox()
                    w.setObjectName("DropDown")
                    w.addItems(choices)
                    if value not in choices:
                        w.addItem(value)
                    w.setCurrentText(value)
                    editors[key] = ("str_combo", w)
                    form.addRow(label, w)
                else:
                    w = QLineEdit(value)
                    editors[key] = ("str", w)
                    form.addRow(label, w)
                continue

            w = QTextEdit()
            w.setMinimumHeight(92)
            w.setPlainText(_json.dumps(value, indent=2))
            editors[key] = ("json", w)
            form.addRow(label, w)

        page._po_editors = editors

    def _save_current_plugin_options_page(self):
        page = self.page_plugin_options
        custom_save = getattr(page, "_po_custom_save", None)
        if callable(custom_save):
            custom_save()
            return
        cfg_path = page._po_cfg_path
        plugin_id = page._po_plugin_id
        editors = page._po_editors or {}
        if cfg_path is None or not plugin_id:
            return

        try:
            parsed = {}
            for key, (kind, widget) in editors.items():
                if kind == "bool":
                    parsed[key] = bool(widget.isChecked())
                elif kind == "int":
                    parsed[key] = int(widget.value())
                elif kind == "float":
                    parsed[key] = float(widget.value())
                elif kind == "str_combo":
                    parsed[key] = str(widget.currentText()).strip()
                elif kind == "str":
                    parsed[key] = str(widget.text()).strip()
                else:
                    raw = widget.toPlainText().strip() or "null"
                    parsed[key] = _json.loads(raw)

            cfg_path.write_text(_json.dumps(parsed, indent=2), encoding="utf-8")
            self._show_status_toast(f"Saved options: {plugin_id}", icon="\u2705")
        except Exception as exc:
            self._show_status_toast(f"Invalid JSON: {exc}", icon="\u26A0")

    def _default_plugin_options(self, plugin_id: str) -> dict:
        defaults = {
            "input_humanization_plugin": {
                "enabled": True,
                "jitter_min_ms": 2,
                "jitter_max_ms": 12,
                "micro_pause_every": 35,
                "micro_pause_ms": 45,
                "fatigue_curve": "soft",
            },
            "preset_benchmark_plugin": {
                "enabled": True,
                "duration_seconds": 60,
                "warmup_seconds": 5,
                "score_weights": {
                    "stability": 0.5,
                    "consistency": 0.3,
                    "drift": 0.2,
                },
            },
            "route_recorder_plugin": {
                "enabled": True,
                "record_hotkey": "f8",
                "execute_hotkey": "f9",
                "record_name": "",
                "selected_recording": "",
                "record_keyboard": False,
                "record_mouse_move": True,
                "record_clicks": True,
                "record_scroll": True,
                "max_points": 5000,
                "sampling_ms": 8,
                "playback_speed": 1.0,
                "jitter_px": 1,
                "game_mode_relative_mouse": True,
                "max_saved_routes": 40,
            },
        }
        return _json.loads(_json.dumps(defaults.get(plugin_id, {"enabled": True, "notes": "Plugin options"})))

    def _plugin_option_choices(self, plugin_id: str, key: str) -> list[str]:
        choice_map = {
            ("input_humanization_plugin", "fatigue_curve"): ["soft", "linear", "aggressive"],
        }
        return list(choice_map.get((plugin_id, key), []))

    def _marketplace_catalog(self) -> list[dict]:
        return [
            {"id": "route_recorder_plugin", "name": "Route Recorder", "version": "2.0.0", "description": "Record full keyboard/mouse routes with hotkeys and replay them with game-mode relative mouse movement.", "author": "Prime Team", "file_name": "route_recorder_plugin.py"},
            {"id": "input_humanization_plugin", "name": "Input Humanization", "version": "1.2.0", "description": "Adds natural timing variation, micro-pauses, and fatigue curves to click patterns.", "author": "Prime Team", "file_name": "input_humanization_plugin.py"},
            {"id": "preset_benchmark_plugin", "name": "Preset Benchmark", "version": "1.1.0", "description": "Performance telemetry for CPU load, missed inputs, lag score, and runtime stability.", "author": "Prime Team", "file_name": "preset_benchmark_plugin.py"},
            {"id": "phasmopobia_plugin", "name": "Phasmophobia", "version": "1.2.0", "description": "Ghost filters, field guide, timer overlays, BPM finder, and Ctrl+K search.", "author": "Prime Team", "file_name": "phasmopobia_plugin.py"},
            {"id": "example_plugin", "name": "Example Plugin", "version": "1.0.0", "description": "Example plugin for template/testing.", "author": "Prime Team", "file_name": "example_plugin.py"},
        ]

    def _marketplace_file_for_plugin(self, plugin_id: str) -> Path:
        for item in self._marketplace_catalog():
            if item.get("id") == plugin_id:
                return self._plugin_manager.registry_dir / str(item.get("file_name"))
        return self._plugin_manager.registry_dir / f"{plugin_id}.py"

    def _marketplace_template_for_plugin(self, plugin_id: str) -> str:
        for item in self._marketplace_catalog():
            if item.get("id") == plugin_id:
                name = str(item.get("name", plugin_id))
                version = str(item.get("version", "1.0.0"))
                desc = str(item.get("description", "Marketplace plugin."))
                return _textwrap.dedent(
                    f'''\
                    def register(context: dict) -> dict:
                        return {{
                            "id": "{plugin_id}",
                            "name": "{name}",
                            "version": "{version}",
                            "description": "{desc}",
                        }}
                    '''
                )
        return _textwrap.dedent(
            f'''\
            def register(context: dict) -> dict:
                return {{
                    "id": "{plugin_id}",
                    "name": "{plugin_id}",
                    "version": "1.0.0",
                    "description": "Marketplace installed plugin.",
                }}
            '''
        )

    def _install_marketplace_plugin(self, plugin_id: str):
        plugin_id = (plugin_id or "").strip()
        if not plugin_id:
            return
        valid_ids = {str(item.get("id", "")).strip() for item in self._marketplace_catalog()}
        if plugin_id not in valid_ids:
            self._show_status_toast("Plugin not available in this release.", icon="\u26A0")
            return
        p = self._marketplace_file_for_plugin(plugin_id)
        if not self._show_themed_confirm(
            "Plugin Install Warning",
            "Plugins can run custom Python code with your user permissions.\n"
            "Only install plugins from trusted sources.\n\n"
            f"Do you want to install '{plugin_id}'?",
            warning=True,
        ):
            self._show_status_toast("Install cancelled", icon="\u26A0")
            return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text(self._marketplace_template_for_plugin(plugin_id), encoding="utf-8")
            self._plugin_manager.load_all()
            self._refresh_plugin_page_state()
            self._switch_page(self.PAGE_PROJECTS)
            if hasattr(self, "page_plugins_market") and hasattr(self.page_plugins_market, "set_fused_index"):
                self.page_plugins_market.set_fused_index(0)
            self._show_status_toast(f"Installed: {plugin_id}", icon="\u2705")
        except Exception as exc:
            self._show_status_toast(f"Install failed: {exc}", icon="\u26A0")

    def _remove_marketplace_plugin(self, plugin_id: str):
        plugin_id = (plugin_id or "").strip()
        if not plugin_id:
            return
        p = self._marketplace_file_for_plugin(plugin_id)
        try:
            if p.exists():
                p.unlink()
            self._plugin_manager.load_all()
            self._refresh_plugin_page_state()
            self._show_status_toast(f"Removed: {plugin_id}", icon="\U0001F5D1")
        except Exception as exc:
            self._show_status_toast(f"Remove failed: {exc}", icon="\u26A0")

    def _install_project_plugin(self, project_key: str):
        p = self._plugin_path_for_project(project_key)
        if p is None:
            return
        if not self._show_themed_confirm(
            "Plugin Install Warning",
            "Plugins can run custom Python code with your user permissions.\n"
            "Only install plugins from trusted sources.\n\n"
            f"Do you want to install '{project_key}'?",
            warning=True,
        ):
            self._show_status_toast("Install cancelled", icon="\u26A0")
            return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text(self._project_plugin_template(project_key), encoding="utf-8")
            self._plugin_manager.load_all()
            self._refresh_plugin_page_state()
            self._show_status_toast(f"Installed: {project_key}", icon="\u2705")
        except Exception as exc:
            self._show_status_toast(f"Install failed: {exc}", icon="\u26A0")

    def _delete_project_plugin(self, project_key: str):
        p = self._plugin_path_for_project(project_key)
        if p is None:
            return
        try:
            if p.exists():
                p.unlink()
            self._plugin_manager.load_all()
            self._refresh_plugin_page_state()
            self._show_status_toast(f"Deleted: {project_key}", icon="\U0001F5D1")
        except Exception as exc:
            self._show_status_toast(f"Delete failed: {exc}", icon="\u26A0")

    def _on_admin_reset(self):
        """Called when the admin panel resets everything — revert to default theme."""
        self._apply_styles("default")
        self.page_settings.refresh_themes()

    def _on_admin_theme_applied(self):
        """Called when the admin panel changes theme unlocks or selection."""
        from app.styling.themes import get_selected_theme_id
        tid = get_selected_theme_id()
        self._apply_styles(tid)
        self.page_settings.refresh_themes()

    def _activate_admin_panel(self):
        """Replace the login page with the admin panel (secret easter egg)."""
        if hasattr(self, "_admin_active") and self._admin_active:
            self._switch_page(self.PAGE_LOGIN)
            return
        self._admin_active = True
        admin = AdminPanel(self.stats, plugin_manager=self._plugin_manager)
        self.pages.removeWidget(self.page_login)
        self.page_login.deleteLater()
        self.page_login = admin
        self.pages.insertWidget(self.PAGE_LOGIN, admin)
        admin.refresh()
        admin.stats_reset.connect(self._on_admin_reset)
        admin.theme_applied.connect(self._on_admin_theme_applied)
        self._switch_page(self.PAGE_LOGIN)

    def _set_active_sidebar(self, active_btn: QPushButton):
        btns = [
            self.btn_home,
            self.btn_preset,
            self.btn_settings,
            self.btn_tokens,
            self.btn_achievements,
            self.btn_projects,
            self.btn_login,
        ]
        for b in btns:
            b.setProperty("active", b is active_btn)
            b.style().unpolish(b)
            b.style().polish(b)
            b.update()

    def _switch_page(self, page_index: int):
        self.pages.setCurrentIndex(page_index)
        self.scroll.verticalScrollBar().setValue(0)
        QTimer.singleShot(0, self._do_clamp_scroll)
        # Secret: Page Turner – track visited pages
        self._visited_pages.add(page_index)
        all_pages = {
            self.PAGE_HOME,
            self.PAGE_PRESET,
            self.PAGE_SETTINGS,
            self.PAGE_TOKENS,
            self.PAGE_PROJECTS,
            self.PAGE_LOGIN,
            self.PAGE_ACHIEVEMENTS,
            self.PAGE_PLUGIN_OPTIONS,
        }
        if self._visited_pages >= all_pages and not self.stats.is_secret_unlocked("page_turner"):
            self.stats.unlock_secret("page_turner")
            self._check_new_achievements()
        titles = {
            self.PAGE_HOME: ("home", self.btn_home),
            self.PAGE_PRESET: ("workflow_studio", self.btn_preset),
            self.PAGE_SETTINGS: ("settings", self.btn_settings),
            self.PAGE_TOKENS: ("stats", self.btn_tokens),
            self.PAGE_PROJECTS: ("plugins", self.btn_projects),
            self.PAGE_MARKETPLACE: ("marketplace", self.btn_projects),
            self.PAGE_PLUGIN_OPTIONS: ("plugin_options", self.btn_projects),
            self.PAGE_LOGIN: ("help_center", self.btn_login),
            self.PAGE_ACHIEVEMENTS: ("achievements", self.btn_achievements),
            self.PAGE_BUILDER: ("workflow_studio", self.btn_preset),
        }
        title_key, btn = titles.get(page_index, ("home", self.btn_home))
        if page_index == self.PAGE_LOGIN and hasattr(self, "_admin_active") and self._admin_active:
            self.lbl_top_title.setText("Admin Panel")
        else:
            if title_key == "help_center":
                self.lbl_top_title.setText("Help Center")
            elif title_key == "plugin_options":
                self.lbl_top_title.setText("Plugin Options")
            elif title_key == "plugins":
                self.lbl_top_title.setText("Plugins")
            else:
                self.lbl_top_title.setText(tr(title_key) if title_key != "about" else "About")
        self._set_active_sidebar(btn)
        if page_index == self.PAGE_TOKENS:
            self.page_stats.refresh()
        if page_index == self.PAGE_ACHIEVEMENTS:
            self.page_achievements.refresh()
        if page_index == self.PAGE_SETTINGS:
            check_and_unlock_all(self.stats)
            self.page_settings.refresh_themes()
        if page_index == self.PAGE_LOGIN:
            self.page_support.set_session_events(self._session_events)
            self.page_support.refresh_all()
        if page_index == self.PAGE_LOGIN and hasattr(self, "_admin_active") and self._admin_active:
            self.page_login.refresh()
        self._log_event(f"Switched page -> {self.lbl_top_title.text()}")

    # ── Scroll clamp fail-safe ───────────────────────────
    def _clamp_scroll_range(self, _lo: int, _hi: int):
        """Scheduled whenever the scrollbar range changes."""
        QTimer.singleShot(0, self._do_clamp_scroll)

    def _effective_visible_height(self, widget: QWidget | None) -> int:
        if widget is None or not widget.isVisible():
            return 0

        # Fused pages (for example Plugins/Marketplace) should clamp based on
        # the active tab only, not the combined size of both tabs.
        fused_stack = getattr(widget, "_fused_stack", None)
        if isinstance(fused_stack, AdaptiveStack):
            active_page = fused_stack.currentWidget()
            tab_top_h = int(getattr(widget, "_fused_top_height", 0) or 0)
            content_h = self._effective_visible_height(active_page)
            return max(0, tab_top_h) + max(0, content_h)

        if isinstance(widget, AdaptiveStack):
            current = widget.currentWidget()
            if current is None:
                return 0
            return max(
                current.minimumSizeHint().height(),
                current.sizeHint().height(),
                current.height(),
            )

        lay = widget.layout()
        if lay is None:
            return max(
                widget.minimumSizeHint().height(),
                widget.sizeHint().height(),
                widget.height(),
            )

        margins = lay.contentsMargins()
        spacing = max(0, lay.spacing())
        child_heights: list[int] = []
        for i in range(lay.count()):
            item = lay.itemAt(i)
            cw = item.widget()
            if cw is not None:
                h = self._effective_visible_height(cw)
                if h > 0:
                    child_heights.append(h)
                continue
            cl = item.layout()
            if cl is not None:
                h = max(cl.minimumSize().height(), cl.sizeHint().height())
                if h > 0:
                    child_heights.append(h)

        if isinstance(lay, QHBoxLayout):
            body = max(child_heights) if child_heights else 0
        else:
            body = sum(child_heights) + max(0, len(child_heights) - 1) * spacing
        return margins.top() + body + margins.bottom()

    def _do_clamp_scroll(self):
        """Prevent the user from scrolling into empty whitespace below the page content."""
        sc = self.scroll
        bar = sc.verticalScrollBar()
        vp_h = sc.viewport().height()
        inner = sc.widget()
        if not inner:
            return

        lay = inner.layout()
        real_h = 0
        if lay and hasattr(self, "pages") and hasattr(self, "_top_bar_card"):
            margins = lay.contentsMargins()
            spacing = max(0, lay.spacing())
            top_h = max(self._top_bar_card.sizeHint().height(), self._top_bar_card.height())
            current_page = self.pages.currentWidget()
            page_h = self._effective_visible_height(current_page)
            real_h = margins.top() + top_h + spacing + page_h + margins.bottom()

        if real_h <= 0:
            candidates = [inner.minimumSizeHint().height(), inner.childrenRect().height(), inner.height()]
            if lay:
                candidates.append(lay.minimumSize().height())
            real_h = max(candidates)

        real_max = max(0, real_h - vp_h)
        bar.setMaximum(real_max)
        if bar.value() > real_max:
            bar.setValue(real_max)

    def _on_interval_changed(self, v: int):
        self.config.interval_ms = int(v)
        self.config.use_cps = False
        self.runner.set_config(self.config)
        try:
            data = self._load_persisted_settings()
            data["interval_ms"] = int(v)
            self._save_persisted_settings(data)
        except Exception:
            pass
        self._update_top_avg_cps()
        # Secret: Speedrunner (1ms) / Patience (max 86400000ms)
        if v == 1 and not self.stats.is_secret_unlocked("speedrunner"):
            self.stats.unlock_secret("speedrunner")
            self._check_new_achievements()
        if v == 86400000 and not self.stats.is_secret_unlocked("patience"):
            self.stats.unlock_secret("patience")
            self._check_new_achievements()

    def _on_scroll_key_changed(self, key: str):
        self._scroll_key = key

    def _on_switch_mouse_button_key_changed(self, key: str):
        self._switch_mouse_button_key = key

    def _on_toggle_both_mouse_key_changed(self, key: str):
        self._toggle_both_mouse_key = key

    def _on_scroll_hotkey_enabled_changed(self, enabled: bool):
        self._scroll_hotkey_enabled = enabled

    def _toggle_scroll_from_hotkey(self):
        """Toggle independent continuous scrolling via keybind."""
        hp = self.page_home
        if not hp.chk_scroll.isChecked():
            self._show_status_toast("Scroll mode is blocked: enable it first", icon="\u26A0")
            return

        if not hasattr(self, "_scroll_timer"):
            self._scroll_timer = QTimer(self)
            self._scroll_mouse = MouseController()
            self._scroll_timer.timeout.connect(self._do_scroll_tick)

        if self._scroll_timer.isActive():
            self._scroll_timer.stop()
            self._show_status_toast("Auto-scroll: Off")
        else:
            scroll_on, scroll_dir, scroll_amt = hp.get_scroll_config()
            if not scroll_on:
                # checkbox was just unchecked, nothing to do
                return
            self._scroll_dir = scroll_dir
            self._scroll_amt = scroll_amt
            self._scroll_timer.start(50)  # ~20 scrolls per second
            self._show_status_toast("Auto-scroll: On")

    def _do_scroll_tick(self):
        """Perform one scroll tick."""
        amt = self._scroll_amt
        if self._scroll_dir == "up":
            amt = -amt
        try:
            self._scroll_mouse.scroll(0, amt)
        except Exception:
            pass

    def _setup_hotkey(self):
        if hasattr(self, "keyboard_listener") or hasattr(self, "mouse_listener"):
            return

        def on_press(key):
            try:
                # ── Konami code tracking (works with both special and char keys) ──
                key_name = self._normalize_keyboard_key(key)
                if key_name:
                    self._konami_buf.append(key_name)
                    if len(self._konami_buf) > len(_KONAMI_KEYS):
                        self._konami_buf = self._konami_buf[-len(_KONAMI_KEYS):]
                    if self._konami_buf == _KONAMI_KEYS:
                        self._konami_buf.clear()
                        if not self.stats.is_secret_unlocked("konami_code"):
                            self.stats.unlock_secret("konami_code")
                            QTimer.singleShot(0, self._check_new_achievements)

                token = self._normalize_keyboard_key(key)
                if token:
                    if token in self._pressed_keyboard_tokens:
                        return
                    self._pressed_keyboard_tokens.add(token)
                    self._on_route_keyboard_event(token, True)
                    self._input_token_signal.emit(token, True)
            except AttributeError:
                pass

        def on_release(key):
            try:
                token = self._normalize_keyboard_key(key)
                if token:
                    self._pressed_keyboard_tokens.discard(token)
                    self._on_route_keyboard_event(token, False)
            except AttributeError:
                pass

        def on_mouse_click(x, y, button, pressed):
            token = self._normalize_mouse_button(button)
            if token:
                self._on_route_mouse_button_event(token, bool(pressed), int(x), int(y))
            if pressed and token:
                self._input_token_signal.emit(token, False)

        def on_mouse_move(x, y):
            self._on_route_mouse_move_event(int(x), int(y))

        def on_mouse_scroll(x, y, dx, dy):
            self._on_route_mouse_scroll_event(int(x), int(y), int(dx), int(dy))

        self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keyboard_listener.start()
        self.mouse_listener = _mouse.Listener(on_click=on_mouse_click, on_move=on_mouse_move, on_scroll=on_mouse_scroll)
        self.mouse_listener.start()

    @staticmethod
    def _normalize_keyboard_key(key) -> str:
        if hasattr(key, "char") and key.char:
            return str(key.char).lower()
        if hasattr(key, "name") and key.name:
            return str(key.name).lower()
        return ""

    @staticmethod
    def _normalize_mouse_button(button) -> str:
        name = getattr(button, "name", "")
        if name:
            return f"mouse_{str(name).lower()}"
        return ""

    def _handle_input_token(self, token: str, allow_presets: bool):
        token = (token or "").strip().lower()
        if not token:
            return

        if self._waiting_for_hotkey:
            self._hotkey_signal.emit(token)
            return

        if self.page_settings.is_waiting_for_keybind_capture():
            self._capture_signal.emit(token)
            return

        if self._emergency_key and token == self._emergency_key:
            if self.runner.is_running():
                self.runner.stop()
                self._log_event("Emergency stop triggered")
            return

        if token == self._hotkey_char:
            if self.isVisible() and self.pages.currentIndex() == self.PAGE_HOME:
                self._toggle_signal.emit()
            return

        if self._scroll_hotkey_enabled and self._scroll_key and token == self._scroll_key:
            QTimer.singleShot(0, self._toggle_scroll_from_hotkey)
            return

        if self._switch_mouse_button_key and token == self._switch_mouse_button_key:
            now = _time_module.monotonic()
            if now - self._last_hotkey_switch_toggle < 0.08:
                return
            self._last_hotkey_switch_toggle = now
            self._toggle_mouse_button_mode()
            return

        if self._toggle_both_mouse_key and token == self._toggle_both_mouse_key:
            now = _time_module.monotonic()
            if now - self._last_hotkey_both_toggle < 0.08:
                return
            self._last_hotkey_both_toggle = now
            self._toggle_both_mouse_mode()
            return

        if self._try_route_recorder_hotkey(token):
            return

        if allow_presets:
            preset_hks = self.page_preset.get_preset_hotkeys()
            if token in preset_hks and self.isVisible():
                self._hotkey_signal.emit(f"preset:{token}")

    def changeEvent(self, event):
        super().changeEvent(event)

    def _toggle_mouse_button_mode(self):
        button = self.page_home.toggle_left_right_button()
        self._show_status_toast(f"Mouse button: {button.title()}")
        self._log_event("Mouse button switched (left/right)")

    def _toggle_both_mouse_mode(self):
        mode = self.page_home.toggle_both_buttons_mode()
        self._show_status_toast(f"Mouse mode: {mode}")
        self._log_event("Both-buttons mode toggled")

    def _show_status_toast(self, text: str, icon: str = "\u2139"):
        theme = get_theme()
        p = theme["palette"]
        toast = ToastNotification(
            text,
            bg_color=p["config_card"],
            border_color=p.get("pill_active_border", "rgba(78,141,255,0.28)"),
            text_color=p["text_primary"],
            icon=icon,
        )
        toast.show_toast(position="top-right")

    def _update_top_avg_cps(self):
        try:
            interval = max(1, int(self.page_home.get_interval_ms()))
            cps = 1000.0 / float(interval)
        except Exception:
            cps = 0.0
        self.lbl_avg_cps.setText(f"Avg CPS: {cps:.1f}")

    def _on_topbar_action_changed(self, action: str):
        self._topbar_action = (action or "search").strip().lower()
        label_map = {
            "search": "Smart Search",
            "support": "Help Center",
            "projects": "Projects",
            "marketplace": "Marketplace",
            "about": "Help Center",
            "toggle": "Toggle",
            "workflow": "Workflow",
        }
        self.btn_search.setText(label_map.get(self._topbar_action, "Smart Search"))

    def _perform_top_action(self, act: str):
        action = (act or "search").strip().lower()
        if action == "search":
            self._on_global_search()
            return
        if action == "support":
            self._open_help_tab("support")
            return
        if action == "projects":
            self._open_plugins_tab()
            return
        if action == "marketplace":
            self._open_marketplace_tab()
            return
        if action == "about":
            self._open_help_tab("about")
            return
        if action == "toggle":
            self._toggle_autoclicker()
            return
        if action == "workflow":
            self._switch_page(self.PAGE_PRESET)
            return
        self._on_global_search()

    def _on_topbar_action(self):
        self._perform_top_action(self._topbar_action)

    def _get_foreground_window_handle(self) -> int:
        if not self._is_windows or not getattr(_ctypes, "windll", None):
            return 0
        try:
            return int(_ctypes.windll.user32.GetForegroundWindow())
        except Exception:
            return 0

    def _get_foreground_exe_name(self) -> str:
        if not self._is_windows or not getattr(_ctypes, "windll", None):
            return ""
        try:
            hwnd = _ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return ""
            pid = _ctypes.c_ulong(0)
            _ctypes.windll.user32.GetWindowThreadProcessId(hwnd, _ctypes.byref(pid))
            if not pid.value:
                return ""
            process_handle = _ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)
            if not process_handle:
                return ""
            try:
                buff = _ctypes.create_unicode_buffer(512)
                size = _ctypes.c_ulong(len(buff))
                ok = _ctypes.windll.kernel32.QueryFullProcessImageNameW(
                    process_handle, 0, buff, _ctypes.byref(size)
                )
                if not ok:
                    return ""
                return buff.value.replace("/", "\\").split("\\")[-1].strip().lower()
            finally:
                _ctypes.windll.kernel32.CloseHandle(process_handle)
        except Exception:
            return ""

    def _get_foreground_window_title(self) -> str:
        if not self._is_windows or not getattr(_ctypes, "windll", None):
            return ""
        try:
            hwnd = _ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return ""
            length = int(_ctypes.windll.user32.GetWindowTextLengthW(hwnd))
            buff = _ctypes.create_unicode_buffer(max(1, length + 1))
            _ctypes.windll.user32.GetWindowTextW(hwnd, buff, len(buff))
            return buff.value.strip().lower()
        except Exception:
            return ""

    def _is_blocked_foreground_program(self) -> bool:
        self._blocked_programs_enabled, blocked = self.page_settings.get_blocked_programs_settings()
        self._blocked_programs = set(blocked)
        if not self._blocked_programs_enabled or not self._blocked_programs:
            return False
        active = self._get_foreground_exe_name()
        if not active:
            return False
        return active in self._blocked_programs

    # ── Hotkey persistence ─────────────────────────────────────
    def _load_persisted_hotkey(self) -> str:
        try:
            import json, os
            f = os.path.join(os.path.expanduser("~"), ".mtautoclicker_settings.json")
            with open(f, "r", encoding="utf-8") as fp:
                return json.load(fp).get("hotkey_char", "")
        except Exception:
            return ""

    def _load_persisted_settings(self) -> dict:
        try:
            f = Path.home() / ".mtautoclicker_settings.json"
            with open(f, "r", encoding="utf-8") as fp:
                data = _json.load(fp)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_persisted_settings(self, data: dict):
        try:
            f = Path.home() / ".mtautoclicker_settings.json"
            with open(f, "w", encoding="utf-8") as fp:
                _json.dump(data, fp, indent=2)
        except Exception:
            pass

    def _build_smart_stabilize_key(self) -> str:
        pos_mode = "fixed" if bool(self.config.use_fixed_position) else "follow"
        btn = str(self.config.button).strip().lower() or "left"
        interval = max(1, int(self.config.interval_ms))
        active_exe = self._get_foreground_exe_name() or "any"
        return f"{active_exe}|{btn}|{pos_mode}|{interval}"

    def _load_smart_stabilize_bootstrap(self, key: str) -> float:
        if not key:
            return 0.0
        data = self._load_persisted_settings()
        profiles = data.get("smart_stabilize_profiles", {})
        profile = profiles.get(key, {}) if isinstance(profiles, dict) else {}
        try:
            value = float(profile.get("correction_ms", 0.0))
        except Exception:
            value = 0.0
        if value > 2000.0:
            value = 2000.0
        if value < -2000.0:
            value = -2000.0
        return value

    def _save_smart_stabilize_profile(self):
        if not self._smart_stabilize_key:
            return
        if self._smart_stabilize_best_accuracy < 75.0:
            return

        data = self._load_persisted_settings()
        profiles = data.get("smart_stabilize_profiles")
        if not isinstance(profiles, dict):
            profiles = {}

        prev = profiles.get(self._smart_stabilize_key, {}) if isinstance(profiles.get(self._smart_stabilize_key), dict) else {}
        prev_acc = float(prev.get("accuracy", 0.0) or 0.0)
        correction = float(self._smart_stabilize_best_correction_ms)

        # Blend with prior value to avoid overfitting to one noisy run.
        if prev:
            correction = (float(prev.get("correction_ms", correction)) * 0.65) + (correction * 0.35)

        profiles[self._smart_stabilize_key] = {
            "correction_ms": round(correction, 4),
            "accuracy": round(max(prev_acc, self._smart_stabilize_best_accuracy), 3),
            "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        data["smart_stabilize_profiles"] = profiles
        self._save_persisted_settings(data)

    def _save_persisted_hotkey(self, ch: str):
        try:
            import json, os
            f = os.path.join(os.path.expanduser("~"), ".mtautoclicker_settings.json")
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except Exception:
                data = {}
            data["hotkey_char"] = ch
            with open(f, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2)
        except Exception:
            pass

    def _on_hotkey_btn_clicked(self):
        if self._waiting_for_hotkey:
            return
        self._waiting_for_hotkey = True
        self.btn_hotkey.setText("Hotkey: (press key or mouse button)")

    def _set_hotkey(self, ch: str):
        # Handle preset hotkey signals
        if ch.startswith("preset:"):
            preset_key = ch.split(":", 1)[1]
            preset_hks = self.page_preset.get_preset_hotkeys()
            if preset_key in preset_hks:
                self._on_load_preset(preset_hks[preset_key])
                QTimer.singleShot(100, self._toggle_autoclicker)
            return
        self._hotkey_char = ch.lower()
        self._waiting_for_hotkey = False
        self.btn_hotkey.setText(f"Hotkey: {self._format_keybind_display(self._hotkey_char)}")
        self._overlay.set_hotkey(self._hotkey_char)
        self._save_persisted_hotkey(self._hotkey_char)

    @staticmethod
    def _format_keybind_display(token: str) -> str:
        tok = (token or "").strip().lower()
        if not tok:
            return "-"
        if tok.startswith("mouse_"):
            return tok.replace("_", " ").title()
        if len(tok) == 1:
            return tok.upper()
        return tok.replace("_", " ").title()

    def _on_emergency_key_changed(self, ch: str):
        self._emergency_key = ch

    def _on_performance_mode_changed(self, enabled: bool):
        self._performance_mode = enabled
        self._overlay_time.setInterval(1500 if enabled else 1000)

    def _toggle_autoclicker(self):
        if self._is_toggling:
            return
        self._is_toggling = True
        # Secret: Click Frenzy – 5 toggles in 10 seconds
        now = _time_module.time()
        self._toggle_times.append(now)
        if len(self._toggle_times) >= 5:
            if now - self._toggle_times[-5] <= 10.0:
                if not self.stats.is_secret_unlocked("click_frenzy"):
                    self.stats.unlock_secret("click_frenzy")
                    self._check_new_achievements()
        try:
            if self.runner.is_running():
                self.runner.stop()
                self._log_event("Manual stop via UI/hotkey")
            else:
                if self._is_blocked_foreground_program():
                    self._show_status_toast("Start blocked for active program", icon="\u26A0")
                    self._log_event("Start blocked by foreground program rule")
                    return

                self.config.interval_ms = self.page_home.get_interval_ms()

                # Warn if interval is dangerously low (once per session when enabled)
                if self.config.interval_ms < 5 and self.page_settings.get_low_interval_warning_enabled():
                    if not self._low_interval_warning_shown:
                        self._low_interval_warning_shown = True
                        if not self._show_themed_confirm(
                            "\u26a0  Low Interval Warning",
                            "You are about to click with an interval under 5 ms.\n\n"
                            "This can freeze your system or cause instability.\n"
                            "Are you sure you want to continue?",
                            warning=True,
                        ):
                            return

                self.config.click_count = self.page_home.get_click_count()
                self.config.button = self.page_home.get_mouse_button()
                self.config.time_limit_ms = self.page_home.get_time_limit_ms()
                self.config.use_cps = False

                # Position
                fixed, px, py = self.page_home.get_position_config()
                self.config.use_fixed_position = fixed
                self.config.fixed_x = px
                self.config.fixed_y = py

                # Jitter & delay from settings
                self.config.random_jitter_ms = self.page_settings.get_jitter_ms()
                self.config.delay_ms = self.page_settings.get_delay_ms()

                # Scroll mode
                scroll_on, scroll_dir, scroll_amt = self.page_home.get_scroll_config()
                self.config.scroll_mode = scroll_on
                self.config.scroll_direction = scroll_dir
                self.config.scroll_amount = scroll_amt

                # Combo mode
                combo_mode, combo_btns = self.page_home.get_combo_config()
                self.config.combo_mode = combo_mode
                self.config.combo_buttons = combo_btns

                # Position offset
                self.config.position_offset_px = self.page_home.get_offset_px()

                # CPS stabilization
                self.config.cps_stabilize = True
                self._smart_stabilize_key = self._build_smart_stabilize_key()
                bootstrap_ms = self._load_smart_stabilize_bootstrap(self._smart_stabilize_key)
                self.config.stabilize_bootstrap_ms = float(bootstrap_ms)
                self.config.stabilize_warmup_clicks = 1 if bootstrap_ms else 3
                self._smart_stabilize_best_accuracy = 0.0
                self._smart_stabilize_best_correction_ms = float(bootstrap_ms)

                # Lag protection settings
                self._lag_guard_enabled, self._lag_guard_threshold, self._lag_guard_events = self.page_settings.get_lag_guard_settings()
                self.config.lag_guard_enabled = self._lag_guard_enabled
                self.config.lag_guard_min_accuracy = float(self._lag_guard_threshold)
                self.config.lag_guard_consecutive = int(self._lag_guard_events)
                self._lag_guard_streak = 0

                # Window targeting: capture the currently-focused window
                if self.page_settings.get_lock_to_window():
                    self.config.target_hwnd = self._get_foreground_window_handle()
                else:
                    self.config.target_hwnd = 0

                # Cursor fail-safe stop zones
                edge_enabled, edge_margin, corner_enabled, corner_size = self.page_settings.get_edge_corner_stop_settings()
                self.config.edge_stop_enabled = bool(edge_enabled)
                self.config.edge_stop_margin_px = max(1, int(edge_margin))
                self.config.corner_stop_enabled = bool(corner_enabled)
                self.config.corner_stop_size_px = max(1, int(corner_size))

                self.runner.set_config(self.config)
                self.runner.start()
                self._log_event("Manual start via UI/hotkey")
        finally:
            QTimer.singleShot(200, lambda: setattr(self, "_is_toggling", False))

    def closeEvent(self, event):
        if hasattr(self, '_scroll_timer') and self._scroll_timer.isActive():
            self._scroll_timer.stop()
        if self._rr_recording:
            self._stop_route_recording()
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        if self.runner.is_running():
            self.runner.stop()
        self._overlay.close()
        self._flush_pending_click_stats()
        self.stats.save()
        event.accept()

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_maximize_icon()
        self._update_window_mask()
        self._update_size_grip()

    def _sync_maximize_icon(self):
        if hasattr(self, "btn_maximize"):
            self.btn_maximize.setText("\u2752" if self.isMaximized() else "\u25a1")

    def _update_size_grip(self):
        if not hasattr(self, "_size_grip"):
            return
        if self.isMaximized():
            self._size_grip.hide()
            return
        self._size_grip.show()
        margin = 10
        self._size_grip.move(
            self.width() - self._size_grip.width() - margin,
            self.height() - self._size_grip.height() - margin,
        )
        self._size_grip.raise_()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and event.y() <= self.title_bar.height():
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            if self.isMaximized():
                self.showNormal()
                self._sync_maximize_icon()
                self._update_size_grip()
                self._drag_pos = QPoint(self.width() // 2, 18)
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.y() <= self.title_bar.height():
            self._toggle_maximize()
        else:
            super().mouseDoubleClickEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            self._sync_maximize_icon()
            self._update_window_mask()
            self._update_size_grip()
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_window_mask()
        self._update_size_grip()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_window_theme_effects(get_theme())
        self._update_window_mask()
        self._sync_maximize_icon()
        self._update_size_grip()

    def _update_window_mask(self):
        if self.isMaximized():
            self.clearMask()
            return
        r = 20
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        region = QRegion(r, 0, max(1, w - 2 * r), h)
        region = region.united(QRegion(0, r, w, max(1, h - 2 * r)))
        region = region.united(QRegion(0, 0, 2 * r, 2 * r, QRegion.Ellipse))
        region = region.united(QRegion(w - 2 * r, 0, 2 * r, 2 * r, QRegion.Ellipse))
        region = region.united(QRegion(0, h - 2 * r, 2 * r, 2 * r, QRegion.Ellipse))
        region = region.united(QRegion(w - 2 * r, h - 2 * r, 2 * r, 2 * r, QRegion.Ellipse))
        self.setMask(region)

    def _apply_window_theme_effects(self, theme: dict):
        # Enable blur-behind for the glass theme on Windows and keep normal
        # compositing for all other themes.
        if not self._is_windows or not getattr(_ctypes, "windll", None):
            return
        is_glass = (theme.get("id") == "liquid_glass")
        try:
            hwnd = int(self.winId())
            class ACCENTPOLICY(_ctypes.Structure):
                _fields_ = [
                    ("AccentState", _ctypes.c_int),
                    ("AccentFlags", _ctypes.c_int),
                    ("GradientColor", _ctypes.c_uint),
                    ("AnimationId", _ctypes.c_int),
                ]

            class WINDOWCOMPOSITIONATTRIBDATA(_ctypes.Structure):
                _fields_ = [
                    ("Attrib", _ctypes.c_int),
                    ("pvData", _ctypes.c_void_p),
                    ("cbData", _ctypes.c_size_t),
                ]

            accent = ACCENTPOLICY()
            accent.AccentState = self._ACCENT_ENABLE_BLURBEHIND if is_glass else self._ACCENT_DISABLED
            accent.AccentFlags = 0
            accent.GradientColor = 0
            accent.AnimationId = 0

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attrib = self._WCA_ACCENT_POLICY
            data.pvData = _ctypes.cast(_ctypes.pointer(accent), _ctypes.c_void_p)
            data.cbData = _ctypes.sizeof(accent)

            fn = getattr(_ctypes.windll.user32, "SetWindowCompositionAttribute", None)
            if fn:
                fn(hwnd, _ctypes.byref(data))
        except Exception:
            pass

    def _on_click_performed(self, count: int = 1):
        self._pending_stat_clicks += max(1, int(count))

        # ── Throttle expensive GUI work to ~30 Hz ──
        now = _time_module.monotonic()
        if now - self._last_gui_tick < 0.033:
            # Keep batching stats clicks, but skip visual updates
            return
        self._last_gui_tick = now

        old_total, new_total = self._flush_pending_click_stats()

        if hasattr(self, 'page_stats'):
            self.page_stats.record_click_time()
        # Feed CPS sparkline
        self.page_home.cps_spark.record_click()
        # Update overlay CPS
        self._overlay.set_cps(self.page_home.cps_spark.current_cps)
        # XP bar
        self._refresh_xp_bar()
        if self.page_settings.get_per_click_sound():
            self._tick_q.put_nowait(True)
        # Secret: Lucky Seven – exactly 777,777 total clicks
        if old_total < 777_777 <= new_total and not self.stats.is_secret_unlocked("lucky_seven"):
            self.stats.unlock_secret("lucky_seven")
            self._check_new_achievements()
        # Check theme unlocks every 500 clicks to avoid overhead
        if new_total // 500 > old_total // 500:
            newly = check_and_unlock_all(self.stats)
            if newly:
                self.page_settings.refresh_themes()
            self._check_new_achievements()

    def _flush_pending_click_stats(self) -> tuple[int, int]:
        pending = self._pending_stat_clicks
        if pending <= 0:
            current = self.stats.total_clicks
            return current, current
        self._pending_stat_clicks = 0
        return self.stats.record_click_batch(pending)

    def _on_click_at_position(self, x: int, y: int):
        self.stats.record_click_position(x, y)

    def _on_cps_adjusted(self, target_cps: float, actual_cps: float,
                         accuracy: float, correction_ms: float):
        self.page_home.show_cps_drift(target_cps, actual_cps, accuracy, correction_ms)
        if self.runner.is_running() and accuracy >= self._smart_stabilize_best_accuracy:
            self._smart_stabilize_best_accuracy = float(accuracy)
            self._smart_stabilize_best_correction_ms = float(correction_ms)
        if not self._lag_guard_enabled or not self.runner.is_running():
            return
        if accuracy < float(self._lag_guard_threshold):
            self._lag_guard_streak += 1
        else:
            self._lag_guard_streak = 0
        if self._lag_guard_streak >= int(self._lag_guard_events):
            self._lag_guard_streak = 0
            self.runner.stop()
            self._show_status_toast("Auto-stopped due to sustained lag", icon="\u26A0")
            self._log_event("Lag protection auto-stopped the runner")

    # ── Themed confirm / warning dialogs ──────────────────────
    def _show_themed_confirm(self, title: str, msg: str, *, warning: bool = False) -> bool:
        """Show a themed Yes / No confirmation dialog. Returns True for Yes."""
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setFixedSize(420, 180)
        dlg.setStyleSheet(get_dialog_stylesheet(warning=warning))

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        lbl = QLabel(msg)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 13px;")
        lay.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_no = QPushButton("Cancel")
        btn_no.setObjectName("CancelBtn")
        btn_no.setCursor(Qt.PointingHandCursor)
        btn_no.clicked.connect(dlg.reject)
        btn_yes = QPushButton("\u2714  Continue")
        btn_yes.setCursor(Qt.PointingHandCursor)
        btn_yes.clicked.connect(dlg.accept)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_no)
        btn_row.addWidget(btn_yes)
        lay.addLayout(btn_row)

        return dlg.exec_() == QDialog.Accepted

    def _play_toggle_sound(self):
        sound = self.page_settings.get_sound()
        if sound:
            custom = self.page_settings.get_custom_start_sound()
            _th.Thread(target=play_sound, args=(sound, custom), daemon=True).start()

    _play_start_sound = _play_toggle_sound
    _play_stop_sound  = _play_toggle_sound

    def _tick_sound_worker(self):
        """Persistent daemon thread that plays tick sounds from a queue."""
        while True:
            self._tick_q.get()  # block until a tick is requested
            # Drain any queued ticks to avoid stacking up during high CPS
            while not self._tick_q.empty():
                try:
                    self._tick_q.get_nowait()
                except Exception:
                    break
            try:
                play_tick()
            except Exception:
                pass

    def _on_new_preset(self):
        dlg = PresetDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            name, desc = dlg.get_values()
            if not name:
                return
            # Capture current config
            data = {
                "name": name,
                "desc": desc,
                "interval_ms": self.page_home.get_interval_ms(),
                "click_count": self.page_home.get_click_count(),
                "button": self.page_home.get_mouse_button(),
                "time_limit_ms": self.page_home.get_time_limit_ms(),
                "stop_mode": self.page_home.stop_mode,
                "jitter_ms": self.page_settings.get_jitter_ms(),
                "delay_ms": self.page_settings.get_delay_ms(),
            }
            fixed, px, py = self.page_home.get_position_config()
            data["use_fixed_position"] = fixed
            data["fixed_x"] = px
            data["fixed_y"] = py
            self.page_preset.add_preset(data)

    def _on_load_preset(self, data: dict):
        # Apply preset to UI
        hp = self.page_home

        # Interval
        interval = data.get("interval_ms", 100)
        hp.spin_interval.blockSignals(True)
        hp.unit_combo.setCurrentIndex(0)  # Milliseconds
        hp.spin_interval.setValue(interval)
        hp.spin_interval.blockSignals(False)

        # Stop mode
        mode = data.get("stop_mode", "never")
        hp._set_stop_mode(mode)
        if mode == "cycles":
            hp.spin_cycles.setValue(data.get("click_count", 100))
        elif mode == "timed":
            tl = data.get("time_limit_ms", 0)
            hours = tl // 3600000
            minutes = (tl % 3600000) // 60000
            seconds = (tl % 60000) // 1000
            ms = tl % 1000
            hp.spin_hours.setValue(hours)
            hp.spin_minutes.setValue(minutes)
            hp.spin_seconds.setValue(seconds)
            hp.spin_milliseconds.setValue(ms)

        # Button
        hp._select_button(data.get("button", "left"))

        # Position
        if data.get("use_fixed_position", False):
            hp._set_position_mode("custom")
            hp.spin_pos_x.setValue(data.get("fixed_x", 960))
            hp.spin_pos_y.setValue(data.get("fixed_y", 540))
        else:
            hp._set_position_mode("follow")

        # Settings page
        self.page_settings.jitter_slider.setValue(data.get("jitter_ms", 0))
        delay = data.get("delay_ms", 0)
        self.page_settings.spin_delay.setValue(delay)

        # Switch to home page
        self._switch_page(self.PAGE_HOME)
        self._update_top_avg_cps()

    def _on_session_start(self):
        self._session_start = _time_module.time()
        self.page_home.cps_spark.start()
        self._overlay.set_running(True)
        self._overlay_time.start()
        self._log_event("Session started")

    def _on_session_stop(self):
        self._flush_pending_click_stats()
        self._save_smart_stabilize_profile()
        if self._session_start is not None:
            duration = _time_module.time() - self._session_start
            self.stats.record_session(duration)
            self._session_start = None
        self.page_home.cps_spark.stop()
        self.page_home.hide_cps_drift()
        self._overlay.set_running(False)
        self._overlay.set_cps(0)
        self._overlay_time.stop()
        self._overlay.set_elapsed(0)
        # XP bar after session XP
        self._refresh_xp_bar()
        # Check theme unlocks after each session
        newly = check_and_unlock_all(self.stats)
        if newly:
            self.page_settings.refresh_themes()
        self._check_new_achievements()
        self._log_event("Session stopped")

    def _tick_overlay_time(self):
        if self._session_start is None:
            self._overlay.set_elapsed(0)
            return
        elapsed = int(_time_module.time() - self._session_start)
        self._overlay.set_elapsed(elapsed)

    def _init_search_index(self):
        self._search_routes = [
            {"terms": ["theme", "color", "skin", "palette", "cosmetic", "themes"], "page": self.PAGE_SETTINGS, "widget": getattr(self.page_settings, "lbl_theme_title", None), "toast": "themes"},
            {"terms": ["scroll", "wheel", "scroll key", "scroll hotkey"], "page": self.PAGE_SETTINGS, "widget": getattr(self.page_settings, "btn_scroll_key", None), "toast": "scroll"},
            {"terms": ["emergency", "panic", "stop key", "emergency stop"], "page": self.PAGE_SETTINGS, "widget": getattr(self.page_settings, "btn_emergency_key", None), "toast": "emergency"},
            {"terms": ["lag", "performance", "fps", "lag guard", "stability"], "page": self.PAGE_SETTINGS, "widget": getattr(self.page_settings, "chk_lag_guard", None), "toast": "lag protection"},
            {"terms": ["preset", "profile", "workflow", "macro builder", "builder"], "page": self.PAGE_PRESET, "widget": getattr(self.page_preset, "preset_list", None), "toast": "presets"},
            {"terms": ["project", "plugin", "plugins", "plugin options", "extensions"], "page": self.PAGE_PROJECTS, "widget": None, "toast": "plugins"},
            {"terms": ["market", "marketplace", "store", "shop", "install plugin"], "page": self.PAGE_MARKETPLACE, "widget": getattr(self.page_marketplace, "input_search", None), "toast": "marketplace"},
            {"terms": ["about", "info", "credits"], "page": self.PAGE_LOGIN, "help_tab": "about", "widget": None, "toast": "about"},
            {"terms": ["support", "help", "guide", "bug", "diagnostics", "profile save"], "page": self.PAGE_LOGIN, "help_tab": "support", "widget": getattr(self.page_support, "input_profile", None), "toast": "support"},
            {"terms": ["home", "main", "click interval", "interval", "click speed", "cps"], "page": self.PAGE_HOME, "widget": getattr(self.page_home, "spin_interval", None), "toast": "home"},
            {"terms": ["stats", "analytics", "tokens", "heatmap", "sessions"], "page": self.PAGE_TOKENS, "widget": None, "toast": "stats"},
            {"terms": ["achievement", "badge", "unlock", "secret"], "page": self.PAGE_ACHIEVEMENTS, "widget": None, "toast": "achievements"},
        ]
        term_set = set()
        for route in self._search_routes:
            for term in route.get("terms", []):
                t = str(term).strip().lower()
                if t:
                    term_set.add(t)
        self._search_terms = sorted(term_set)

        self._search_model = QStringListModel(self._search_terms, self)
        self._search_completer = QCompleter(self._search_model, self)
        self._search_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._search_completer.setFilterMode(Qt.MatchContains)
        self._search_completer.setCompletionMode(QCompleter.PopupCompletion)
        self._search_completer.popup().setObjectName("SearchSuggestList")
        self.input_search.setCompleter(self._search_completer)

    def _update_search_suggestions(self, raw: str):
        text = (raw or "").strip().lower()
        if not text:
            self._search_model.setStringList(self._search_terms)
            return
        contains = [t for t in self._search_terms if text in t]
        close = _difflib.get_close_matches(text, self._search_terms, n=10, cutoff=0.5)
        merged: list[str] = []
        for s in contains + close:
            if s not in merged:
                merged.append(s)
        if not merged:
            merged = self._search_terms[:10]
        self._search_model.setStringList(merged)

    def _navigate_search_result(self, route: dict):
        page = int(route.get("page", self.PAGE_HOME))
        if page == self.PAGE_MARKETPLACE:
            self._open_marketplace_tab()
        elif page == self.PAGE_PROJECTS:
            self._open_plugins_tab()
        elif page == self.PAGE_LOGIN and route.get("help_tab") in ("about", "support"):
            self._open_help_tab(route.get("help_tab"))
        else:
            self._switch_page(page)
        widget = route.get("widget")
        if widget is not None:
            try:
                widget.setFocus(Qt.OtherFocusReason)
            except Exception:
                pass
        self._show_status_toast(f"Found: {route.get('toast', 'result')}")

    def _on_global_search(self):
        text = self.input_search.text().strip().lower()
        if not text:
            return
        best_route = None
        best_score = 0.0
        for route in self._search_routes:
            for term in route.get("terms", []):
                t = str(term).strip().lower()
                if not t:
                    continue
                score = _difflib.SequenceMatcher(None, text, t).ratio()
                if text in t:
                    score = max(score, 0.93)
                if t in text:
                    score = max(score, 0.88)
                if score > best_score:
                    best_score = score
                    best_route = route
        if best_route is not None and best_score >= 0.50:
            self._navigate_search_result(best_route)
            return
        self._switch_page(self.PAGE_HOME)

    def _log_event(self, message: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self._session_events.append(f"[{stamp}] {message}")
        if len(self._session_events) > 500:
            self._session_events = self._session_events[-500:]

    def _open_plugins_tab(self):
        self._switch_page(self.PAGE_PROJECTS)
        if hasattr(self, "page_plugins_market") and hasattr(self.page_plugins_market, "set_fused_index"):
            self.page_plugins_market.set_fused_index(0)

    def _open_marketplace_tab(self):
        self._switch_page(self.PAGE_PROJECTS)
        if hasattr(self, "page_plugins_market") and hasattr(self.page_plugins_market, "set_fused_index"):
            self.page_plugins_market.set_fused_index(1)

    def _open_help_tab(self, tab: str):
        self._switch_page(self.PAGE_LOGIN)
        if hasattr(self, "_admin_active") and self._admin_active:
            return
        if not hasattr(self, "page_login") or not hasattr(self.page_login, "set_fused_index"):
            return
        idx = 1 if (tab or "").strip().lower() == "support" else 0
        self.page_login.set_fused_index(idx)

    def _refresh_xp_bar(self):
        cur, needed, lvl = self.stats.xp_progress()
        self.page_home.xp_bar.set_xp(cur, needed, lvl)

    def _on_overlay_toggled(self, enabled: bool):
        if enabled:
            self._overlay.show()
        else:
            self._overlay.hide()

    def retranslateUi(self):
        """Update all translatable text in MainWindow."""
        self.setWindowTitle(tr("app_title"))
        self.title_label.setText(tr("app_title"))
        self.btn_home.setText(tr("home"))
        self.btn_preset.setText(tr("workflow_studio"))
        self.btn_settings.setText(tr("settings"))
        self.btn_tokens.setText(tr("stats"))
        self.btn_achievements.setText(tr("achievements"))
        self.btn_support.setText(tr("support_hub"))
        self.btn_projects.setText("Plugins")
        self.btn_login.setText("Help Center")
        # Re-set the current page title
        idx = self.pages.currentIndex()
        title_keys = {
            self.PAGE_HOME: "home", self.PAGE_PRESET: "workflow_studio",
            self.PAGE_SETTINGS: "settings", self.PAGE_TOKENS: "stats",
            self.PAGE_PROJECTS: "plugins", self.PAGE_LOGIN: "help_center",
            self.PAGE_ACHIEVEMENTS: "achievements", self.PAGE_BUILDER: "workflow_studio", self.PAGE_SUPPORT: "support_hub",
            self.PAGE_MARKETPLACE: "marketplace",
            self.PAGE_PLUGIN_OPTIONS: "plugin_options",
        }
        key = title_keys.get(idx, "home")
        if key == "help_center":
            self.lbl_top_title.setText("Help Center")
        elif key == "plugin_options":
            self.lbl_top_title.setText("Plugin Options")
        elif key == "plugins":
            self.lbl_top_title.setText("Plugins")
        else:
            self.lbl_top_title.setText(tr(key) if key != "about" else "About")

    def _make_fused_page(self, left_title: str, left_widget: QWidget, right_title: str, right_widget: QWidget) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)
        btn_left = QPushButton(left_title)
        btn_right = QPushButton(right_title)
        for btn in (btn_left, btn_right):
            btn.setObjectName("ToggleButton")
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setProperty("active", False)

        stack = AdaptiveStack()
        stack.addWidget(left_widget)
        stack.addWidget(right_widget)

        # Store fused metadata so scroll clamping can use the active tab only.
        page._fused_stack = stack
        page._fused_top_height = 36

        def set_idx(i: int):
            stack.setCurrentIndex(i)
            btn_left.setProperty("active", i == 0)
            btn_right.setProperty("active", i == 1)
            for b in (btn_left, btn_right):
                b.style().unpolish(b)
                b.style().polish(b)
                b.update()
            # Fused pages can have very different heights between tabs; recompute
            # scroll limits after the active tab changes.
            QTimer.singleShot(0, self._do_clamp_scroll)

        btn_left.clicked.connect(lambda: set_idx(0))
        btn_right.clicked.connect(lambda: set_idx(1))
        set_idx(0)
        page.set_fused_index = set_idx

        top.addWidget(btn_left)
        top.addWidget(btn_right)
        top.addStretch(1)
        lay.addLayout(top)
        lay.addWidget(stack, 1)
        return page

    def _on_sidebar_config_changed(self, prefs: dict):
        self._apply_sidebar_preferences(prefs)

    def _sidebar_button_map(self) -> dict[str, QPushButton]:
        return {
            "home": self.btn_home,
            "preset": self.btn_preset,
            "settings": self.btn_settings,
            "stats": self.btn_tokens,
            "achievements": self.btn_achievements,
            "projects": self.btn_projects,
            "help": self.btn_login,
        }

    def _apply_sidebar_preferences(self, prefs: dict):
        if not hasattr(self, "_sidebar_nav_layout"):
            return
        while self._sidebar_nav_layout.count():
            item = self._sidebar_nav_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        order = list(prefs.get("order", [])) or ["home", "preset", "settings", "stats", "achievements", "projects", "help"]
        visible = prefs.get("visible", {})
        btn_map = self._sidebar_button_map()

        order = ["projects" if key == "marketplace" else key for key in order]
        help_btn = btn_map.get("help")

        for key in order:
            if key == "help":
                continue
            btn = btn_map.get(key)
            if btn is None:
                continue
            if key in ("stats", "achievements", "projects"):
                if not bool(visible.get(key, True)):
                    continue
            self._sidebar_nav_layout.addWidget(btn)
        self._sidebar_nav_layout.addStretch(1)
        if help_btn is not None and bool(visible.get("help", True)):
            self._sidebar_nav_layout.addWidget(help_btn)

    def _on_language_changed(self, code: str):
        set_language(code)
        self.retranslateUi()
        # Refresh all pages
        for page in (self.page_home, self.page_preset, self.page_settings,
                     self.page_stats, self.page_achievements, self.page_builder, self.page_support, self.page_marketplace):
            if hasattr(page, 'retranslateUi'):
                page.retranslateUi()
