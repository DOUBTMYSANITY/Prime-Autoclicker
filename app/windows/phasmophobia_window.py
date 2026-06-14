from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QEvent, QPoint, QSize, pyqtSignal
from PyQt5.QtGui import QColor, QKeySequence, QPainter, QLinearGradient, QPen
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QShortcut,
    QVBoxLayout,
    QWidget,
)
from app import setup_paths

setup_paths()

from app.styling.themes import get_theme, get_selected_theme_id
from app.gui.widgets import AdaptiveStack, Card, PillButton, add_shadow
from plugins.Phasmo.phasmo_bpm_finder import PhasmoBpmFinderManager
from plugins.Phasmo.phasmo_brightness_booster import PhasmoBrightnessManager
from plugins.Phasmo.phasmo_compact_window import PhasmoCompactWindow
from plugins.Phasmo.phasmo_data import (
    BEHAVIOR_FILTER_SPECS,
    MIMIC_FAKE_EVIDENCE,
    SUPPORTED_VERSION,
    behavior_filter_match,
    forced_evidence_tell_lines,
    ghost_matches_evidence,
    ghost_shortlist,
)
from plugins.Phasmo.phasmo_global_search import GlobalSearchDialog
from plugins.Phasmo.phasmo_timer_overlays import PhasmoTimerOverlayManager
from plugins.Phasmo.phasmo_settings import load_settings, save_settings
from plugins.Phasmo.phasmo_settings_page import PhasmoSettingsPage
from plugins.Phasmo.phasmo_timer_custom_ui import TimersCustomizePanel
from plugins.Phasmo.phasmo_version import default_save_path, load_save, read_game_version_from_save
from plugins.Phasmo.phasmo_difficulty_builder import DifficultyBuilderPage, DifficultyState
from plugins.Phasmo.phasmo_field_guide import FieldGuidePage


@dataclass(frozen=True)
class GhostEntry:
    name: str
    evidence: tuple[str, ...]
    sanity: str
    speed: str
    audio: str
    tells: tuple[str, ...]


class PhasmoBackdrop(QWidget):
    def paintEvent(self, _event):
        theme = get_theme()
        p = theme.get("palette", {})
        bg_start = QColor(p.get("bg_start", "#06070B"))
        bg_mid = QColor(p.get("bg_mid", "#0B1020"))
        bg_end = QColor(p.get("bg_end", "#23103A"))

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0.0, bg_start)
        grad.setColorAt(0.55, bg_mid)
        grad.setColorAt(1.0, bg_end)
        painter.fillRect(rect, grad)

        painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
        step_x = max(82, rect.width() // 20)
        step_y = max(72, rect.height() // 13)
        for y in range(30, rect.height(), step_y):
            for x in range(20, rect.width(), step_x):
                for i in range(5):
                    dx = x + i * 7
                    painter.drawLine(dx, y, dx, y + 18)
                painter.drawLine(x - 3, y + 8, x + 31, y + 3)


class StyledPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)


class StyledScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


class TriStateEvidenceCheckBox(QCheckBox):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setTristate(True)
        self.setCheckState(Qt.Unchecked)

    def nextCheckState(self):
        state = self.checkState()
        if state == Qt.Unchecked:
            self.setCheckState(Qt.Checked)
            return
        if state == Qt.Checked:
            self.setCheckState(Qt.PartiallyChecked)
            return
        self.setCheckState(Qt.Unchecked)

    def evidence_state(self) -> str:
        state = self.checkState()
        if state == Qt.Checked:
            return "include"
        if state == Qt.PartiallyChecked:
            return "exclude"
        return "neutral"


class DragStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._dragging = False
        self._drag_offset = QPoint()
        self.setMouseTracking(True)
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPos() - self.window().frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

class GhostCard(Card):
    clicked = pyqtSignal(str)

    def __init__(self, entry: GhostEntry, match: bool = False):
        super().__init__(radius=18)
        self.entry = entry
        self.setObjectName("GhostCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumSize(360, 246)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(8)
        left.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.setSpacing(8)

        name = QLabel(entry.name.upper())
        name.setObjectName("GhostName")
        name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        close_btn = QPushButton("×")
        close_btn.setObjectName("CardCloseBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(lambda: self.setVisible(False))

        header.addWidget(name, 1)
        header.addStretch(1)
        header.addWidget(close_btn)

        evidence_row = QVBoxLayout()
        evidence_row.setSpacing(4)
        evidence_row.setContentsMargins(0, 0, 0, 0)
        for ev in entry.evidence:
            tag = QLabel(self._evidence_tag_text(ev))
            tag.setObjectName("EvidenceTag")
            tag.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            tag.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            evidence_row.addWidget(tag)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        meta_items = [("🧠", entry.sanity), ("👣", entry.speed)]
        if entry.audio and entry.audio.upper() not in ("N/A", ""):
            meta_items.append(("🔊", entry.audio))
        for icon, text in meta_items:
            stat = QLabel(f"{icon} {text}")
            stat.setObjectName("GhostMeta")
            stat.setAlignment(Qt.AlignCenter)
            stat.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            stats_row.addWidget(stat)
        stats_row.addStretch(1)

        left.addLayout(header)
        left.addLayout(evidence_row)
        left.addLayout(stats_row)

        tells = QFrame()
        tells.setObjectName("TellPanel")
        tells.setMinimumWidth(160)
        tells_lay = QVBoxLayout(tells)
        tells_lay.setContentsMargins(10, 10, 10, 10)
        tells_lay.setSpacing(6)
        tells_title = QLabel("Tells")
        tells_title.setObjectName("TellsTitle")
        tells_lay.addWidget(tells_title)

        tells_scroll = QScrollArea()
        tells_scroll.setObjectName("TellScroll")
        tells_scroll.setWidgetResizable(True)
        tells_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tells_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tells_scroll.setFrameShape(QFrame.NoFrame)
        tells_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        tells_inner = QWidget()
        tells_inner.setAttribute(Qt.WA_StyledBackground, True)
        tells_inner_lay = QVBoxLayout(tells_inner)
        tells_inner_lay.setContentsMargins(0, 0, 0, 0)
        tells_inner_lay.setSpacing(0)

        self._tells_body = QLabel("\n".join(f"• {line}" for line in entry.tells))
        self._tells_body.setObjectName("TellsBody")
        self._tells_body.setWordWrap(True)
        self._tells_body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._tells_body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tells_inner_lay.addWidget(self._tells_body)
        tells_inner_lay.addStretch(1)

        tells_scroll.setWidget(tells_inner)
        tells_lay.addWidget(tells_scroll, 1)

        outer.addLayout(left, 3)
        outer.addWidget(tells, 2)

        self._base_tells = entry.tells
        self._apply_match(match)
        self._apply_selected(False)

    @staticmethod
    def _evidence_tag_text(ev: str) -> str:
        icon_map = {
            "EMF 5": "📡",
            "Ultraviolet": "🔦",
            "Writing": "✍️",
            "Freezing": "❄️",
            "DOTS": "🟢",
            "Ghost Orbs": "🔵",
            "Spirit Box": "📻",
        }
        return f"{icon_map.get(ev, '•')} {ev}"

    def _apply_match(self, match: bool):
        self.setProperty("match", bool(match))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _apply_selected(self, selected: bool):
        self.setProperty("selected", bool(selected))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_match(self, match: bool):
        self._apply_match(match)

    def set_selected(self, selected: bool):
        self._apply_selected(selected)

    def set_tell_lines(self, extra_lines: tuple[str, ...] = ()) -> None:
        lines = list(self._base_tells)
        if extra_lines:
            lines.extend(extra_lines)
        self._tells_body.setText("\n".join(f"• {line}" for line in lines))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.entry.name)
        super().mousePressEvent(event)


class PhasmophobiaWindow(QMainWindow):
    go_back_to_autoclicker = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle("Phasmophobia Cheat Sheet")
        self.resize(1900, 1080)

        self._drag_pos = None
        self._drag_surfaces: set[QWidget] = set()
        self._ghost_cards: list[GhostCard] = []
        self._behavior_filter_checks: dict[str, QCheckBox] = {}
        self._behavior_filter_targets: dict[str, frozenset[str] | None] = {}
        self._behavior_filter_special: dict[str, str | None] = {}
        self._evidence_checks: dict[str, TriStateEvidenceCheckBox] = {}

        self._ghost_entries = self._build_ghost_entries()
        self._ghost_rules = self._build_ghost_rules()
        self._search_items = self._build_search_items()
        self._selected_ghost: str | None = None
        self._settings = load_settings()
        self._search_filter = ""
        self._compact_window: PhasmoCompactWindow | None = None
        self._timer_overlays = PhasmoTimerOverlayManager(self)
        self._bpm_finder = PhasmoBpmFinderManager()
        self._brightness = PhasmoBrightnessManager()
        self._timer_overlays._hotkey_signal.connect(self._on_overlay_hotkey)

        self._build_ui()
        self.apply_theme(get_selected_theme_id())
        self._wire()
        self._refresh_matches()
        self._sync_sidebar_width()
        self._refresh_version_banner()
        self._apply_plugin_settings(self._settings)

    def _build_ui(self):
        root = PhasmoBackdrop()
        root.setAttribute(Qt.WA_StyledBackground, True)
        self._drag_surfaces.add(root)
        self._install_drag_surface(root)
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        self.sidebar = Card(radius=20)
        self.sidebar.setObjectName("PhasmoSidebar")
        self.sidebar.setAttribute(Qt.WA_StyledBackground, True)
        self._drag_surfaces.add(self.sidebar)
        self._install_drag_surface(self.sidebar)
        self.sidebar.setFixedWidth(236)
        add_shadow(self.sidebar, blur=24, y=10, alpha=120)
        sb = QVBoxLayout(self.sidebar)
        sb.setContentsMargins(18, 18, 18, 18)
        sb.setSpacing(14)

        brand_row = QHBoxLayout()
        brand_mark = QLabel("👻")
        brand_mark.setObjectName("PhasmoBrandMark")
        brand_mark.setAlignment(Qt.AlignCenter)
        brand_mark.setFixedSize(58, 58)
        brand_text = QLabel("PHASMO\nCHEAT SHEET")
        brand_text.setObjectName("PhasmoBrandText")
        brand_row.addWidget(brand_mark)
        brand_row.addWidget(brand_text)
        brand_row.addStretch(1)
        sb.addLayout(brand_row)

        self.btn_ghost_type = PillButton("Ghost Type", "👻")
        self.btn_field_guide = PillButton("Field Guide", "📖")
        self.btn_difficulty = PillButton("Difficulty", "⚡")
        self.btn_settings = PillButton("Settings", "⚙")
        self.btn_back = PillButton("Back", "↩")

        sb.addWidget(self.btn_ghost_type)
        sb.addWidget(self.btn_field_guide)
        sb.addWidget(self.btn_difficulty)
        sb.addWidget(self.btn_settings)
        sb.addStretch(1)
        timer_hint = QLabel(
            "Overlays: Num1 Smudge · Num2 Crucifix · Num3 Obambo · Num4 Gamma · Num5 Brightness · F BPM · R reset"
        )
        timer_hint.setObjectName("PhasmoSupport")
        timer_hint.setWordWrap(True)
        sb.addWidget(timer_hint)
        sb.addWidget(self.btn_back)

        content_wrap = Card(radius=22)
        content_wrap.setObjectName("PhasmoContent")
        content_wrap.setAttribute(Qt.WA_StyledBackground, True)
        self._drag_surfaces.add(content_wrap)
        self._install_drag_surface(content_wrap)
        add_shadow(content_wrap, blur=28, y=10, alpha=120)
        content_lay = QVBoxLayout(content_wrap)
        content_lay.setContentsMargins(18, 18, 18, 18)
        content_lay.setSpacing(14)

        self.drag_bar = DragStrip()
        top_bar = QHBoxLayout(self.drag_bar)
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(12)
        self.drag_bar.setStyleSheet("background: transparent;")
        self.lbl_title = QLabel("Ghost Identification Cheat Sheet")
        self.lbl_title.setObjectName("PhasmoTitle")
        self.lbl_subtitle = QLabel("Filter by evidence, speed, and sanity — Ctrl+K to jump anywhere.")
        self.lbl_subtitle.setObjectName("PhasmoSub")
        title_col = QVBoxLayout()
        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_subtitle)
        top_bar.addLayout(title_col)
        top_bar.addStretch(1)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("PhasmoSearch")
        self.search_input.setPlaceholderText("Search ghosts… (Ctrl+K)")
        self.search_input.setMinimumWidth(340)
        self.search_input.setFixedHeight(40)
        top_bar.addWidget(self.search_input)
        self.btn_compact = PillButton("Compact HUD", "◫")
        self.btn_compact.setMinimumWidth(150)
        top_bar.addWidget(self.btn_compact)
        content_lay.addWidget(self.drag_bar)

        self.lbl_version_banner = QLabel("")
        self.lbl_version_banner.setObjectName("PhasmoSupport")
        self.lbl_version_banner.setWordWrap(True)
        self.lbl_version_banner.hide()
        content_lay.addWidget(self.lbl_version_banner)

        self.stack = AdaptiveStack()
        self.page_ghost_type = self._make_ghost_type_page()
        self._drag_surfaces.update({self.page_ghost_type})
        self._install_drag_surface(self.page_ghost_type)
        self.stack.addWidget(self.page_ghost_type)
        self.page_field_guide = FieldGuidePage()
        self._drag_surfaces.update({self.page_field_guide})
        self._install_drag_surface(self.page_field_guide)
        self.stack.addWidget(self.page_field_guide)
        self.page_difficulty = DifficultyBuilderPage()
        self.page_difficulty.set_evidence_count(self._settings.forced_evidence_count)
        self.page_difficulty.changed.connect(self._on_difficulty_builder_changed)
        self._drag_surfaces.update({self.page_difficulty})
        self._install_drag_surface(self.page_difficulty)
        self.stack.addWidget(self.page_difficulty)
        self.page_settings = PhasmoSettingsPage(self._settings)
        self._drag_surfaces.update({self.page_settings})
        self._install_drag_surface(self.page_settings)
        self.stack.addWidget(self.page_settings)
        content_lay.addWidget(self.stack, 1)

        outer.addWidget(self.sidebar)
        outer.addWidget(content_wrap, 1)

        self.setStyleSheet(
            "QWidget { color: #FFFFFF; background: transparent; }"
            "QFrame#PhasmoSidebar { background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(58, 58, 58, 0.5); }"
            "QFrame#PhasmoContent { background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(58, 58, 58, 0.5); }"
            "QFrame#MapTopBar { background: #050505; border: 1px solid #3A3A3A; border-radius: 14px; }"
            "QLabel#PhasmoTitle { font-size: 28px; font-weight: 900; letter-spacing: 1px; color: #FFFFFF; font-family: Impact, Arial Narrow, sans-serif; }"
            "QLabel#PhasmoSub { color: #BDBDBD; font-size: 12px; }"
            "QLabel#PhasmoBrandMark { font-size: 24px; background: #111111; border: 1px solid #5A5A5A; border-radius: 16px; }"
            "QLabel#PhasmoBrandText { font-size: 15px; font-weight: 900; letter-spacing: 1px; color: #FFFFFF; }"
            "QFrame#GhostCard { background: #0B0B0B; border: 1px solid #4B4B4B; border-radius: 18px; }"
            "QFrame#GhostCard[match='true'] { border: 1px solid #3DDC84; background: #0C1610; }"
            "QFrame#GhostCard[selected='true'] { border: 2px solid #FFFFFF; background: #121212; }"
            "QFrame#GhostCard:hover { border: 1px solid #8A8A8A; background: #151515; }"
            "QFrame#PhasmoMapWrap { background: #0B0B0B; border: 1px solid #4B4B4B; border-radius: 20px; }"
            "QFrame#PhasmoGridWrap { background: #0B0B0B; border: 1px solid #4B4B4B; border-radius: 20px; }"
            "QWidget#PhasmoSaveEditorPage { background: transparent; }"
            "QWidget#PhasmoSaveEditorPage QFrame#PhasmoGridWrap { background: rgba(11, 11, 11, 0.7); }"
            "QPushButton#PhasmoMapButton { background: #0A0A0A; border: 1px solid #4D4D4D; border-radius: 10px; color: #FFFFFF; font-weight: 800; text-align: center; padding: 10px 16px; font-size: 12px; }"
            "QPushButton#PhasmoMapButton:hover { background: #1A1A1A; border: 1px solid #6A6A6A; }"
            "QLabel#PhasmoMapTitle { color: #FFFFFF; font-size: 22px; font-weight: 900; }"
            "QLabel#PhasmoMapSubtitle { color: #C8C8C8; font-size: 12px; }"
            "QLabel#GhostTitle { font-size: 18px; font-weight: 900; color: #FFFFFF; font-family: Impact, Bahnschrift Condensed, Arial Narrow, sans-serif; }"
            "QLabel#EvidenceTag { font-size: 10px; font-weight: 700; color: #FFFFFF; background: #1A1A1A; border: 1px solid #4A4A4A; border-radius: 9px; padding: 2px 5px; }"
            "QLabel#GhostMeta { color: #D0D0D0; font-size: 10px; }"
            "QLabel#GhostTell { color: #E0E0E0; font-size: 10px; }"
            "QLabel#MapTitle { font-size: 17px; font-weight: 800; color: #FFFFFF; }"
            "QLabel#MapNotes { color: #C8C8C8; font-size: 11px; }"
            "QPushButton#PillButton { background: #0A0A0A; border: 1px solid #4D4D4D; border-radius: 16px; color: #FFFFFF; font-weight: 800; text-align: left; padding-left: 2px; }"
            "QPushButton#PillButton:hover { background: #161616; border: 1px solid #FFFFFF; }"
            "QPushButton#PillButton:pressed { background: #222222; border: 1px solid #FFFFFF; }"
            "QPushButton#PillButton QLabel#PillIcon { background: #1A1A1A; border: 1px solid #4D4D4D; border-radius: 13px; }"
            "QPushButton#PillButton QLabel#PillText { color: #FFFFFF; font-size: 13px; font-weight: 800; }"
            "QPushButton#PhasmoTab { background: #0A0A0A; border: 1px solid #4D4D4D; border-radius: 12px; color: #D0D0D0; font-weight: 800; }"
            "QPushButton#PhasmoTab[active='true'] { background: #1A1A1A; border: 1px solid #FFFFFF; color: #FFFFFF; }"
            "QPushButton#PhasmoReset, QPushButton#PhasmoToolButton { background: #0A0A0A; border: 1px solid #4D4D4D; border-radius: 12px; color: #FFFFFF; font-weight: 800; }"
            "QPushButton#PhasmoReset:hover, QPushButton#PhasmoToolButton:hover { background: #1A1A1A; border: 1px solid #FFFFFF; }"
            "QLabel#PhasmoSectionTitle { color: #FFFFFF; font-size: 13px; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }"
            "QLabel#PhasmoCurrentMap { color: #FFFFFF; font-size: 13px; font-weight: 800; padding: 10px 12px; border-radius: 12px; background: #101010; border: 1px solid #4A4A4A; }"
            "QLabel#PhasmoSupport { color: #BDBDBD; font-size: 11px; }"
            "QLabel#PhasmoToolCopy { color: #CFCFCF; font-size: 12px; }"
            "QLabel#PhasmoGridTitle { color: #FFFFFF; font-size: 18px; font-weight: 900; }"
            "QLabel#PhasmoGridInfo, QLabel#MapHeroSub { color: #C8C8C8; font-size: 12px; }"
            "QLabel#MapHeroTitle { color: #FFFFFF; font-size: 18px; font-weight: 900; }"
            "QLabel#GhostName { font-size: 21px; font-weight: 900; color: #FFFFFF; font-family: Impact, Creepster, Nosifer, Butcherman, Eater, Arial Narrow, sans-serif; }"
            "QToolButton, QPushButton#CardCloseBtn { background: #0A0A0A; border: 1px solid #4D4D4D; border-radius: 10px; color: #FFFFFF; }"
            "QToolButton:hover, QPushButton#CardCloseBtn:hover { background: #1A1A1A; }"
            "QFrame#TellPanel { background: #050505; border: 1px solid #3A3A3A; border-radius: 14px; }"
            "QLabel#TellsTitle { color: #FFFFFF; font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }"
            "QLabel#TellsBody { color: #E0E0E0; font-size: 11px; }"
            "QFrame#InstantConfirmRow { background: #0A0A0A; border: 1px solid #3A3A3A; border-radius: 14px; }"
            "QLabel#InstantConfirmGhost { color: #FFFFFF; font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }"
            "QLabel#InstantConfirmBullet { color: #E0E0E0; font-size: 11px; padding-left: 8px; }"
            "QScrollArea#TellScroll { background: transparent; border: none; }"
            "QScrollArea#TellScroll > QWidget > QWidget { background: transparent; }"
            "QScrollArea#TellScroll::viewport { background: transparent; }"
            "QScrollArea#TellScroll QScrollBar:vertical { width: 0px; background: transparent; border: none; }"
            "QScrollArea#TellScroll QScrollBar::handle:vertical { background: transparent; min-height: 0px; }"
            "QScrollBar:vertical { background: #111111; width: 10px; margin: 4px 0 4px 0; border-radius: 5px; }"
            "QScrollBar::handle:vertical { background: #7A7A7A; min-height: 28px; border-radius: 5px; }"
            "QScrollBar::handle:vertical:hover { background: #FFFFFF; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; background: transparent; }"
            "QComboBox, QCheckBox { color: #FFFFFF; background: transparent; }"
            "QCheckBox { spacing: 8px; padding: 2px 0; border: none; }"
            "QCheckBox[evidenceState='include'] { color: #FFFFFF; font-weight: 700; }"
            "QCheckBox[evidenceState='exclude'] { color: #B0B0B0; text-decoration: line-through; }"
            "QCheckBox[evidenceState='neutral'] { color: #FFFFFF; }"
            "QCheckBox::indicator { width: 16px; height: 16px; border-radius: 5px; border: 1px solid #5A5A5A; background: #111111; }"
            "QCheckBox::indicator:unchecked { background: #111111; }"
            "QCheckBox::indicator:unchecked:hover { background: #1B1B1B; }"
            "QCheckBox::indicator:hover { border: 1px solid #FFFFFF; }"
            "QCheckBox[evidenceState='include']::indicator { background: #FFFFFF; border: 1px solid #FFFFFF; }"
            "QCheckBox[evidenceState='include']::indicator:checked { background: #FFFFFF; border: 1px solid #FFFFFF; }"
            "QCheckBox[evidenceState='exclude']::indicator { background: #222222; border: 1px solid #FFFFFF; }"
            "QCheckBox[evidenceState='exclude']::indicator:unchecked { background: #222222; }"
            "QCheckBox[evidenceState='exclude']::indicator:checked { background: #222222; }"
            "QCheckBox[evidenceState='neutral']::indicator { background: #111111; border: 1px solid #5A5A5A; }"
            "QCheckBox::indicator:checked { background: #FFFFFF; border: 1px solid #FFFFFF; }"
            "QCheckBox::indicator:indeterminate { background: #222222; border: 1px solid #FFFFFF; }"
            "QCheckBox::indicator:pressed { background: #DDDDDD; }"
            "QLineEdit#PhasmoSearch { background: rgba(10, 10, 10, 0.75); border: 1px solid #4D4D4D; border-radius: 12px; padding: 8px 14px; color: #FFFFFF; font-size: 13px; }"
            "QLineEdit#PhasmoSearch:focus { border: 1px solid #FFFFFF; }"
            "QComboBox { background: #0A0A0A; border: 1px solid #4D4D4D; border-radius: 12px; padding: 8px 12px; }"
            "QComboBox::drop-down { border: none; width: 24px; }"
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea::viewport { background: transparent; }"
            "QFrame#GuideCard { background: #0B0B0B; border: 1px solid #4B4B4B; border-radius: 14px; }"
            "QLabel#GuideCardTitle { color: #FFFFFF; font-size: 15px; font-weight: 900; }"
            "QLabel#GuideCardTag { color: #3ddc84; font-size: 10px; font-weight: 800; padding: 2px 8px; border: 1px solid #3a5a40; border-radius: 8px; }"
            "QLabel#GuideCardBody { color: #C8C8C8; font-size: 12px; }"
            "QLabel#GuideCardBullet { color: #E0E0E0; font-size: 11px; padding-left: 4px; }"
            "QLabel#GuideTab[active='true'] { color: #FFFFFF; border-color: #FFFFFF; background: #1A1A1A; }"
            "QPushButton#GuideTab { color: #BDBDBD; font-size: 12px; font-weight: 800; padding: 6px 12px; border: 1px solid #4D4D4D; border-radius: 10px; background: transparent; }"
            "QPushButton#GuideTab[active='true'] { color: #FFFFFF; border-color: #FFFFFF; background: #1A1A1A; }"
            "QPushButton#GuideTab:hover { border-color: #FFFFFF; }"
            "QFrame#DifficultySummary { background: #0B0B0B; border: 1px solid #4B4B4B; border-radius: 14px; }"
        )

    def _install_drag_surface(self, widget: QWidget):
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj in self._drag_surfaces:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                child = obj.childAt(event.pos())
                if child is None or child.objectName() in {"PhasmoBackdrop", "PhasmoSidebar", "PhasmoContent", "InstantConfirmRow", "TellPanel", "MapHero", "PhasmoGridWrap"}:
                    self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                    event.accept()
                    return True
            if event.type() == QEvent.MouseMove and self._drag_pos is not None and event.buttons() & Qt.LeftButton:
                self.move(event.globalPos() - self._drag_pos)
                event.accept()
                return True
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._drag_pos = None
                event.accept()
                return True
        return False

    def _make_ghost_type_page(self) -> QWidget:
        page = StyledPage()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        filters = Card(radius=20)
        filters.setObjectName("PhasmoFilters")
        add_shadow(filters, blur=22, y=8, alpha=90)
        fl = QVBoxLayout(filters)
        fl.setContentsMargins(16, 14, 16, 14)
        fl.setSpacing(12)

        tab_row = QHBoxLayout()
        self.btn_filters_tab = QPushButton("Filters")
        self.btn_tools_tab = QPushButton("Instant Ghost")
        self.btn_timers_tab = QPushButton("Timers")
        for btn in (self.btn_filters_tab, self.btn_tools_tab, self.btn_timers_tab):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setObjectName("PhasmoTab")
        self.btn_filters_tab.setProperty("active", True)
        tab_row.addWidget(self.btn_filters_tab)
        tab_row.addWidget(self.btn_tools_tab)
        tab_row.addWidget(self.btn_timers_tab)
        fl.addLayout(tab_row)

        self.tabs = QStackedWidget()
        self.tabs.addWidget(self._make_filters_tab())
        self.tabs.addWidget(self._make_tools_tab())
        self.timers_panel = TimersCustomizePanel(self._settings)
        self.tabs.addWidget(self.timers_panel)
        fl.addWidget(self.tabs, 1)

        grid_wrap = Card(radius=20)
        grid_wrap.setObjectName("PhasmoGridWrap")
        add_shadow(grid_wrap, blur=24, y=10, alpha=100)
        gw = QVBoxLayout(grid_wrap)
        gw.setContentsMargins(14, 14, 14, 14)
        gw.setSpacing(10)

        header_row = QHBoxLayout()
        grid_title = QLabel("Ghost Cards")
        grid_title.setObjectName("PhasmoGridTitle")
        grid_info = QLabel("Matching ghosts stay visible with a green border. Click a card to pin it.")
        grid_info.setObjectName("PhasmoGridInfo")
        header_col = QVBoxLayout()
        header_col.addWidget(grid_title)
        header_col.addWidget(grid_info)
        header_row.addLayout(header_col)
        header_row.addStretch(1)
        gw.addLayout(header_row)

        scroll = StyledScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setAttribute(Qt.WA_StyledBackground, True)
        self.ghost_grid = QGridLayout(inner)
        self.ghost_grid.setContentsMargins(2, 2, 2, 2)
        self.ghost_grid.setHorizontalSpacing(10)
        self.ghost_grid.setVerticalSpacing(10)
        self.ghost_grid.setAlignment(Qt.AlignTop)
        scroll.setWidget(inner)
        self._ghost_grid_inner = inner
        gw.addWidget(scroll, 1)

        for index, entry in enumerate(self._ghost_entries):
            card = GhostCard(entry, match=False)
            card.clicked.connect(self._handle_card_click)
            self._ghost_cards.append(card)
            row = index // 3
            col = index % 3
            self.ghost_grid.addWidget(card, row, col)

        lay.addWidget(filters)
        lay.addWidget(grid_wrap, 1)
        return page

    def _make_filters_tab(self) -> QWidget:
        page = StyledPage()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        scroll = StyledScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        inner = QWidget()
        inner.setAttribute(Qt.WA_StyledBackground, True)
        body = QVBoxLayout(inner)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        def _section(title: str, subtitle: str | None = None) -> QVBoxLayout:
            box = QVBoxLayout()
            box.setSpacing(8)
            head = QLabel(title)
            head.setObjectName("PhasmoSectionTitle")
            box.addWidget(head)
            if subtitle:
                sub = QLabel(subtitle)
                sub.setObjectName("PhasmoSupport")
                sub.setWordWrap(True)
                box.addWidget(sub)
            return box

        evidence = _section(
            "Evidence Filters",
            "Set how many evidence slots your difficulty allows, then mark found (✓) or ruled-out (strike) evidence",
        )
        self.cmb_forced_evidence = QComboBox()
        self.cmb_forced_evidence.addItem("3 evidence (Normal / Intermediate / Professional)", 3)
        self.cmb_forced_evidence.addItem("2 evidence (Nightmare)", 2)
        self.cmb_forced_evidence.addItem("1 evidence (Insanity)", 1)
        self.cmb_forced_evidence.addItem("0 evidence (Apocalypse — Ghost Orbs only)", 0)
        for i in range(self.cmb_forced_evidence.count()):
            if self.cmb_forced_evidence.itemData(i) == self._settings.forced_evidence_count:
                self.cmb_forced_evidence.setCurrentIndex(i)
                break
        self.cmb_forced_evidence.currentIndexChanged.connect(self._on_forced_evidence_changed)
        evidence.addWidget(self.cmb_forced_evidence)
        self.lbl_evidence_slots = QLabel("")
        self.lbl_evidence_slots.setObjectName("PhasmoSupport")
        self.lbl_evidence_slots.setWordWrap(True)
        evidence.addWidget(self.lbl_evidence_slots)
        evidence_list = QVBoxLayout()
        evidence_list.setSpacing(8)
        evidence_list.setContentsMargins(0, 0, 0, 0)
        evidence_items = [
            ("EMF 5", "EMF 5"),
            ("UV", "Ultraviolet"),
            ("Writing", "Writing"),
            ("Freezing", "Freezing"),
            ("DOTS", "DOTS"),
            ("Ghost Orbs", "Ghost Orbs"),
            ("Spirit Box", "Spirit Box"),
        ]
        for label, evidence_name in evidence_items:
            chk = self._make_check(label, False, evidence=True)
            chk.setCursor(Qt.PointingHandCursor)
            chk.setFocusPolicy(Qt.NoFocus)
            chk.stateChanged.connect(self._on_evidence_state_changed)
            evidence_list.addWidget(chk)
            self._evidence_checks[evidence_name] = chk
        evidence.addLayout(evidence_list)
        self._apply_evidence_enable_states()
        body.addLayout(evidence)

        speed = _section("Speed", "Use hunt movement to narrow the candidate ghosts")
        speed_list = QVBoxLayout()
        speed_list.setSpacing(8)
        speed_list.setContentsMargins(0, 0, 0, 0)
        self.chk_slow = self._make_check("Slow", False)
        self.chk_normal = self._make_check("Normal", False)
        self.chk_fast = self._make_check("Fast", False)
        for chk in (self.chk_slow, self.chk_normal, self.chk_fast):
            chk.setCursor(Qt.PointingHandCursor)
            chk.setFocusPolicy(Qt.NoFocus)
            chk.stateChanged.connect(self._refresh_matches)
            speed_list.addWidget(chk)
        speed.addLayout(speed_list)
        body.addLayout(speed)

        sanity = _section("Hunt Sanity", "Filter by the sanity range that triggered the hunt")
        sanity_list = QVBoxLayout()
        sanity_list.setSpacing(8)
        sanity_list.setContentsMargins(0, 0, 0, 0)
        self.chk_late = self._make_check("Late (<40%)", False)
        self.chk_norm = self._make_check("Normal (>40%)", False)
        self.chk_early = self._make_check("Early (>50%)", False)
        self.chk_very_early = self._make_check("Very Early (>75%)", False)
        for chk in (self.chk_late, self.chk_norm, self.chk_early, self.chk_very_early):
            chk.setCursor(Qt.PointingHandCursor)
            chk.setFocusPolicy(Qt.NoFocus)
            chk.stateChanged.connect(self._refresh_matches)
            sanity_list.addWidget(chk)
        sanity.addLayout(sanity_list)
        body.addLayout(sanity)

        behavior = _section(
            "Behavioral Filters",
            "Check only what you have positively observed — unchecked means no effect on the list.",
        )
        behavior_list = QVBoxLayout()
        behavior_list.setSpacing(8)
        behavior_list.setContentsMargins(0, 0, 0, 0)

        for label, targets, special in BEHAVIOR_FILTER_SPECS:
            chk = self._make_check(label, False, evidence=False)
            chk.setCursor(Qt.PointingHandCursor)
            chk.setFocusPolicy(Qt.NoFocus)
            chk.stateChanged.connect(self._refresh_matches)
            behavior_list.addWidget(chk)
            self._behavior_filter_checks[label] = chk
            self._behavior_filter_targets[label] = targets
            self._behavior_filter_special[label] = special
        behavior.addLayout(behavior_list)
        body.addLayout(behavior)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("PhasmoReset")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setFixedHeight(40)
        self.lbl_support = QLabel("Support info and version v0.17.1.5")
        self.lbl_support.setObjectName("PhasmoSupport")
        body.addWidget(self.btn_reset)
        
        # Note: 'Disable Toasts' setting moved to the main Settings page
        # to provide a single global toggle. Previously present here.
        
        body.addWidget(self.lbl_support)
        body.addItem(QSpacerItem(20, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))

        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return page

    def _make_tools_tab(self) -> QWidget:
        page = StyledPage()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        head = QLabel("Instant Ghost")
        head.setObjectName("PhasmoSectionTitle")
        lay.addWidget(head)

        info = QLabel("Read-only references that instantly narrow the suspect list.")
        info.setObjectName("PhasmoToolCopy")
        info.setWordWrap(True)
        lay.addWidget(info)

        scroll = StyledScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setAttribute(Qt.WA_StyledBackground, True)
        confirm_list = QVBoxLayout(inner)
        confirm_list.setContentsMargins(0, 0, 0, 0)
        confirm_list.setSpacing(8)

        confirm_items = [
            ("Obake", [
                "6-fingered handprint (doors, windows, coolers)",
                "5-finger fingerprint (keyboards, cell doors)",
                "Double fingerprint (light switches)",
                "Fingerprint disappears within ~20 seconds",
            ]),
            ("Yurei", [
                "Door fully opened or fully closed by ghost (no in-between)",
                "Door touched twice in rapid succession",
            ]),
            ("Banshee", [
                "Unique scream heard through Parabolic Microphone",
                "Ghost roams toward a specific player from across the map",
            ]),
            ("Phantom", [
                "Photo of ghost during event is clear and undistorted (ghost vanishes)",
                "Ghost teleports to a player (EMF 2 spawns at that player's location)",
                "Ghost teleports + walks through salt (no reaction)",
            ]),
            ("Poltergeist", [
                "Multiple objects thrown simultaneously / item pile explodes",
            ]),
            ("Myling", [
                "Footsteps audible only within ~12m during hunt (abnormally quiet)",
            ]),
            ("Hantu", [
                "Visible icy breath from ghost during hunt with breaker off",
            ]),
            ("Demon", [
                "Hunt starts above 70% sanity with no electronics or talking nearby",
            ]),
            ("Onryo", [
                "Ghost stops hunting at exactly 4m from a lit flame",
                "Hunt triggered right after the 3rd flame is blown out",
            ]),
            ("Revenant", [
                "Speed drops dramatically (3 m/s -> 1 m/s) when you hide",
            ]),
            ("Goryo", [
                "Ghost only shows DOTS through video camera, never naked eye",
                "Ghost never leaves its starting room",
            ]),
            ("The Twins", [
                "Two simultaneous interactions in different locations",
            ]),
            ("Jinn", [
                "25% sanity drop near breaker, with EMF 2 on the breaker",
            ]),
            ("Mare", [
                "Light turns off the instant you flip it on (any distance)",
            ]),
            ("Moroi", [
                "Sanity drains twice as fast after a Spirit Box / Parabolic response",
            ]),
            ("Deogen", [
                "Heavy breathing audible through walls / on Spirit Box",
                "Ghost sprints toward you from far, slows to a crawl up close",
            ]),
            ("Yokai", [
                "Hunt only starts when player is within 2.5m and talking",
            ]),
            ("Wraith or Phantom (check salt next)", [
                "Ghost teleports to a player (EMF 2 spawns at that player's location)",
            ]),
            ("Wraith", [
                "Ghost teleports + refuses to step on salt",
            ]),
            ("Thaye", [
                "Ghost ages on Ouija Board (age increases when asked)",
                "Activity decreases dramatically over the course of the contract",
            ]),
            ("Raiju", [
                "Ghost speeds up only when active electronics are within 15m",
            ]),
            ("The Mimic", [
                "Ghost orbs visible despite Ghost Orbs not being one of its 3 evidences",
                "Ghost behavior contradicts the 3 confirmed evidence types",
            ]),
            ("Spirit", [
                "Smudge prevents hunts for 180 seconds (instead of usual 90)",
            ]),
            ("Dayan", [
                "Speed dramatically changes based on player movement within 10m",
            ]),
            ("Gallu", [
                "Ghost enters enraged state after stepping in salt",
            ]),
            ("Obambo", [
                "Ghost cycles between calm and aggressive every ~2 minutes",
                "Hunt starts in calm state (slow speed, 50%) -> switches to fast (65%)",
            ]),
            ("Aswang", [
                "Hunt ends instantly when ghost reaches you inside an official hide spot",
                "Accelerates to ~2.53 m/s faster than normal LOS ghosts (~17s vs ~26s)",
                "Does not slow down when losing line of sight (unlike Revenant)",
            ]),
            ("Kormos", [
                "Completely blind during hunts — walks past hidden players",
                "Hunt threshold rises to 70% if anyone sprints in its room",
                "Kills through walls/furniture within ~1.5m",
                "No mist-ball ghost events",
            ]),
            ("Oni", [
                "Cannot perform mist-ball / smoke ghost events",
                "Much more active when players are grouped within ~6m",
                "More visible during hunts (blinks less often)",
            ]),
            ("Shade", [
                "Will not hunt above ~35% average sanity",
                "Will not hunt or trigger events while a player is in its room",
                "Very few interactions compared to other ghosts",
            ]),
        ]
        for ghost, bullets in confirm_items:
            row = QFrame()
            row.setObjectName("InstantConfirmRow")
            row_lay = QVBoxLayout(row)
            row_lay.setContentsMargins(12, 10, 12, 10)
            row_lay.setSpacing(6)
            ghost_label = QLabel(f"{ghost}:")
            ghost_label.setObjectName("InstantConfirmGhost")
            ghost_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row_lay.addWidget(ghost_label)
            for bullet in bullets:
                obs = QLabel(f"- {bullet}")
                obs.setObjectName("InstantConfirmBullet")
                obs.setWordWrap(True)
                obs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                row_lay.addWidget(obs)
            confirm_list.addWidget(row)

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        return page

    def _make_check(self, text: str, checked: bool, evidence: bool = False) -> QCheckBox:
        chk = TriStateEvidenceCheckBox(text) if evidence else QCheckBox(text)
        if evidence:
            chk.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        else:
            chk.setChecked(checked)
        chk.setAttribute(Qt.WA_StyledBackground, True)
        return chk

    def _wire(self):
        self.btn_back.clicked.connect(self._go_back)
        self.btn_ghost_type.clicked.connect(lambda: self._switch_page(0))
        self.btn_field_guide.clicked.connect(lambda: self._switch_page(1))
        self.btn_difficulty.clicked.connect(lambda: self._switch_page(2))
        self.btn_settings.clicked.connect(lambda: self._switch_page(3))
        self.btn_filters_tab.clicked.connect(lambda: self._switch_filter_tab(0))
        self.btn_tools_tab.clicked.connect(lambda: self._switch_filter_tab(1))
        self.btn_timers_tab.clicked.connect(lambda: self._switch_filter_tab(2))
        self.btn_reset.clicked.connect(self._reset_filters)
        self.btn_compact.clicked.connect(self._toggle_compact_window)
        self.search_input.textChanged.connect(self._on_search_text)
        self.search_input.returnPressed.connect(self._open_global_search)
        self.timers_panel.settings_changed.connect(self._on_timer_settings_changed)
        self.page_settings.settings_changed.connect(self._on_plugin_settings_changed)
        self.page_settings.display_boost_preview.connect(self._on_display_boost_preview)
        QShortcut(QKeySequence("Ctrl+K"), self, self._open_global_search)
        QShortcut(QKeySequence("Num+1"), self, self._timer_overlays.toggle_smudge)
        QShortcut(QKeySequence("Num+2"), self, self._timer_overlays.toggle_crucifix)
        QShortcut(QKeySequence("Num+3"), self, self._timer_overlays.toggle_obambo)
        QShortcut(QKeySequence("F"), self, self._bpm_finder.tap)
        QShortcut(QKeySequence("R"), self, self._bpm_finder.reset)

    def _build_search_items(self) -> list[tuple[str, str, str]]:
        return [("Ghost", entry.name, entry.name) for entry in self._ghost_entries]

    def _open_global_search(self) -> None:
        dialog = GlobalSearchDialog(
            self._search_items,
            self,
            initial=self.search_input.text().strip(),
        )
        dialog.picked.connect(self._on_search_picked)
        dialog.exec_()

    def _on_search_picked(self, kind: str, target: str) -> None:
        kind_l = kind.strip().lower()
        if kind_l == "ghost":
            self._switch_page(0)
            self.search_input.setText(target)
            self._selected_ghost = target
            self._refresh_matches()
            return
    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        pages = (
            ("Ghost Identification Cheat Sheet", "Filter by evidence, speed, and sanity — Ctrl+K to jump anywhere."),
            ("Field Guide", "Cursed possessions, equipment usage, and difficulty reference."),
            ("Difficulty Builder", "Match custom lobby modifiers — evidence slots sync with ghost filters."),
            ("Phasmo Settings", "Toggle overlays and customize timer HUDs. Enabled overlays stay on all tabs."),
        )
        if 0 <= index < len(pages):
            title, subtitle = pages[index]
            self.lbl_title.setText(title)
            self.lbl_subtitle.setText(subtitle)
        self._apply_plugin_settings(self._settings)

    def _switch_filter_tab(self, index: int):
        self.tabs.setCurrentIndex(index)
        self.btn_filters_tab.setProperty("active", index == 0)
        self.btn_tools_tab.setProperty("active", index == 1)
        self.btn_timers_tab.setProperty("active", index == 2)
        for btn in (self.btn_filters_tab, self.btn_tools_tab, self.btn_timers_tab):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _build_ghost_entries(self) -> list[GhostEntry]:
        return [
            GhostEntry("Aswang", ("Freezing", "Writing", "DOTS"), "50%", "1.53 - 2.53 m/s", "N/A", ("Identity: Random gender and ghost model", "Strength: Accelerates much faster than normal ghosts when locked onto a target in line of sight", "Weakness: Hunt ends instantly if it reaches you inside an official hide spot — closets/lockers are safe", "Reaches top hunt speed (~2.53 m/s) in about 17 seconds instead of the usual 26", "Prefers chasing over searching during hunts", "Shares two evidences with Revenant — speed acceleration is the key difference", "Does not slow down when losing sight (unlike Revenant which crawls)")),
            GhostEntry("Banshee", ("Ultraviolet", "Ghost Orbs", "DOTS"), "12 / 50 / 87%", "1.7 m/s", "Unique screams", ("Identity: Always female ghost name and model", "Strength: Targets one specific player and only uses their sanity to decide whether to hunt", "Weakness: Unique scream betrays it through the Parabolic Microphone", "33% chance of producing a distinct shriek on the Parabolic Mic instead of normal whispers", "During a hunt, ignores everyone except its chosen target if that target is inside", "Higher chance of triggering the singing ghost event compared to other ghosts", "Roams toward its target in DOTS state from anywhere on the map")),
            GhostEntry("Dayan", ("EMF 5", "Ghost Orbs", "Spirit Box"), "45 / 50 / 65%", "1.2 - 2.25 m/s", "State-based", ("Identity: Always female ghost name and model", "Strength: Nearly doubles in speed when players within 10m are moving", "Weakness: Slows dramatically if nearby players stand completely still", "Hunt sanity threshold rises to 65% when a player is close", "Speed test: move while it's chasing, then stop — sharp speed difference confirms it", "Easy to confuse with Twins (use EMF reading patterns to differentiate)", "At base it moves at 1.7 m/s, but jumps to 2.25 m/s when targets are walking")),
            GhostEntry("Demon", ("Ultraviolet", "Writing", "Freezing"), "70%+", "1.7 m/s", "Aggressive", ("Identity: Random gender and model", "Strength: Hunts more aggressively than any other ghost — can begin at 70% sanity, plus a chance to hunt at any sanity", "Weakness: Extended crucifix range — works at up to 5m instead of the normal 3m", "Standard hunt cooldown is 20 seconds instead of 25", "Smudges only stop it from hunting for 60 seconds instead of 90", "Chain hunting is possible due to short cooldowns", "A crucifix burning at 4-5m distance confirms it")),
            GhostEntry("Deogen", ("Spirit Box", "Writing", "DOTS"), "40%", "0.4 - 3.0 m/s", "Heavy breathing", ("Identity: Random gender and model", "Strength: Always knows exactly where every player is", "Weakness: Cannot hunt above 40% sanity — late hunter", "Sprints at 3 m/s when far from players, drops to 0.4 m/s up close", "Heavy breathing is audible through walls and on the Spirit Box", "Cannot be hidden from — it walks directly to you", "Best strategy is to keep running in circles since it's slow up close")),
            GhostEntry("Gallu", ("EMF 5", "Ultraviolet", "Spirit Box"), "40 / 50 / 60%", "1.36 - 1.96 m/s", "3-state cycle", ("Identity: Random gender and model", "Strength: Becomes enraged when protective equipment is used, weakening that equipment's effect", "Weakness: Repeated enraging exhausts it, making tools work better again later", "Cycles between three speed tiers: slow, normal, and fast", "When enraged it walks through salt without reacting (similar to Wraith behavior)", "Two consecutive uses of protection drop it down a speed tier", "Triggered by salt, crucifix, smudge, or incense")),
            GhostEntry("Goryo", ("EMF 5", "Ultraviolet", "DOTS"), "50%", "1.7 m/s", "Camera DOTS", ("Identity: Random gender and model", "Strength: DOTS only visible through a video camera, never with the naked eye", "Weakness: Will not leave its favorite room", "Never changes rooms throughout the contract", "DOTS evidence requires placing a camera and watching remotely", "Limited roaming makes its location predictable", "If you see DOTS shape with your own eyes, it's not a Goryo")),
            GhostEntry("Hantu", ("Ultraviolet", "Ghost Orbs", "Freezing"), "50%", "1.4 - 2.7 m/s", "Cold breath", ("Identity: Random gender and model", "Strength: Moves faster the colder the room is — up to 2.7 m/s in freezing rooms", "Weakness: Slows down significantly in warm areas — max 1.4 m/s", "Cannot turn the breaker back on, only off (twice as likely as other ghosts)", "Visible icy breath emanates from it during hunts when the breaker is off", "Does not gain speed from line of sight", "Use a thermometer in different rooms to track its speed shifts")),
            GhostEntry("Jinn", ("EMF 5", "Ultraviolet", "Freezing"), "50%", "1.7 / 2.5 m/s", "Breaker boost", ("Identity: Random gender and model", "Strength: Travels faster when chasing players with line of sight, provided the breaker is on", "Weakness: Cannot turn the breaker off — needs power for its abilities", "Drains 25% sanity instantly when within 3m of a player with the breaker on", "Triggers an EMF 2 reading on the breaker after using its ability", "Max hunt speed is 2.5 m/s only when breaker is on", "Always behaves like a normal ghost when the power is off")),
            GhostEntry("Kormos", ("Ghost Orbs", "Spirit Box", "Ultraviolet"), "50 / 70%", "1.7 - 3.65 m/s", "Blind hunt", ("Identity: Random gender and model", "Strength: Heightened hearing — can detect movement through walls and floors", "Weakness: Completely blind during hunts — no visual line of sight at all", "Hunt threshold rises to 70% if anyone sprints in its room", "Kills players by getting within 1.5m — ignores walls and obstacles", "Cannot perform mist form or chasing ghost events", "Stand still and stay silent during hunts and it likely won't find you", "Cannot remember player locations between hunts")),
            GhostEntry("Mare", ("Spirit Box", "Ghost Orbs", "Writing"), "40 / 60%", "1.7 m/s", "Darkness", ("Identity: Random gender and model", "Strength: Hunts at 60% sanity in the dark", "Weakness: Drops to 40% sanity threshold when lights in its room are on", "Will never turn lights on, only off", "Can instantly kill a light right after you turn it on, from any distance", "Higher chance of triggering the light-shattering ghost event", "Prefers dark rooms — favors darker areas during roams")),
            GhostEntry("Moroi", ("Spirit Box", "Writing", "Freezing"), "50%", "1.5 - 2.25 m/s", "Curse drain", ("Identity: Random gender and model", "Strength: Gets faster as team sanity drops — up to 3.71 m/s with line of sight at low sanity (one of the fastest in the game)", "Weakness: Sanity pills cancel its curse and slow it down", "Curses any player who receives a Spirit Box or Parabolic Mic response — doubles their sanity drain", "Curse persists even in well-lit rooms", "Smudges blind it for ~9 seconds during hunts instead of the usual 6", "At 100% sanity it moves at normal 1.7 m/s")),
            GhostEntry("Myling", ("EMF 5", "Ultraviolet", "Writing"), "50%", "1.7 m/s", "Quiet footsteps", ("Identity: Random gender and model", "Strength: More likely to make paranormal sounds through equipment than other ghosts", "Weakness: Quieter hunting footsteps — only audible within 12m instead of the standard 20", "Step sounds disappear at much closer range than expected during hunts", "Best detected with a dropped flashlight or Parabolic Mic", "More frequent audible activity outside of hunts", "Sound disappearance is the cleanest indicator")),
            GhostEntry("Obake", ("EMF 5", "Ultraviolet", "Ghost Orbs"), "50%", "1.7 m/s", "Shape shifts", ("Identity: Random gender and model", "Strength: Can shapeshift during a hunt, briefly changing its model", "Weakness: Has only a 75% chance of leaving a fingerprint per interaction (instead of guaranteed)", "6.66% chance to leave a 6-fingered handprint on doors, windows, and coolers", "Can leave 5 fingers on keyboards and cell doors (where 4 is normal)", "Can leave 2 fingerprints on a light switch (where 1 is normal)", "Fingerprints disappear in 20 seconds instead of the usual 40")),
            GhostEntry("Obambo", ("Writing", "Ultraviolet", "DOTS"), "10 / 65%", "1.45 / 1.96 m/s", "State timer", ("Identity: Random gender and model", "Strength: Hunts at 65% sanity when in aggressive state and moves 20% faster than normal", "Weakness: In calm state, slower to hunt and easier to track", "Switches between calm and aggressive every ~2 minutes", "Aggressive: high activity in ghost room, faster speed, earlier hunts", "Calm: low activity, slower speed, normal hunt threshold", "State changes are predictable on a timer, unlike Gallu's reactive shifts")),
            GhostEntry("Oni", ("EMF 5", "Freezing", "DOTS"), "50%", "1.7 m/s", "High activity", ("Identity: Random gender and model", "Strength: Much more active when players are grouped together — activity increases by 30 within 6m", "Weakness: More visible during hunts — blinks less than other ghosts", "Cannot perform the mist ball / smoke form ghost event (hissing fog ball)", "Higher chance of fully manifesting during ghost events instead of appearing as a shadow", "Ghost events drain 20% sanity instead of the usual 10%", "Overall activity is significantly higher than average")),
            GhostEntry("Onryo", ("Spirit Box", "Ghost Orbs", "Freezing"), "40 / 60 / 100%", "1.7 m/s", "Flame logic", ("Identity: Random gender and model", "Strength: Every third flame it extinguishes triggers a guaranteed hunt", "Weakness: Will not start a hunt if a lit flame is within 4m", "Hunt sanity threshold is 60% by default — can hunt earlier than most ghosts", "Prioritizes extinguishing flames over normal hunting behavior", "Ignores the 20-second cooldown on blowing flames out", "Lit candles work as a partial substitute for a crucifix")),
            GhostEntry("Phantom", ("Spirit Box", "Ultraviolet", "DOTS"), "50%", "1.7 m/s", "Photo vanish", ("Identity: Random gender and model", "Strength: Drains more sanity when visible during events and hunts (0.5% per second within 10m line of sight)", "Weakness: Vanishes the instant you photograph it", "Photo of a Phantom shows the location but the ghost is gone, with no equipment distortion", "Blinks far less often during hunts — invisible for much longer between flickers", "Can teleport to any player, leaving an EMF 2 reading at their position", "Different from Wraith — Phantom still walks through salt normally")),
            GhostEntry("Poltergeist", ("Spirit Box", "Ultraviolet", "Writing"), "50%", "1.7 m/s", "Burst throws", ("Identity: Random gender and model", "Strength: Can launch multiple items simultaneously and detonate piles", "Weakness: Useless in empty rooms with nothing to throw", "Each thrown item drains 2% sanity from nearby players", "Throws happen far more often during hunts than from other ghosts", "Can produce an EMF 3 reading from a pile detonation", "Multiple objects moving at the same time confirms it")),
            GhostEntry("Raiju", ("EMF 5", "Ghost Orbs", "DOTS"), "50 / 65%", "1.7 / 2.5 m/s", "Electronics boost", ("Identity: Random gender and model", "Strength: Speeds up when within 15m of active electronics (up to 2.5 m/s)", "Weakness: Behaves like a normal ghost without electronics nearby", "Hunt sanity threshold rises to 65% when electronics are powered nearby", "Can disrupt electronic equipment from 15m away (normal range is 6-10m)", "Does not gain speed from line of sight, only from electronics", "Flashlights flicker from a greater distance than usual")),
            GhostEntry("Revenant", ("Ghost Orbs", "Writing", "Freezing"), "50%", "1.0 / 3.0 m/s", "Sudden sprint", ("Identity: Random gender and model", "Strength: Hits 3 m/s when it has line of sight or hears you — among the fastest in the game when active", "Weakness: Drops to a crawl of 1 m/s when it loses track of all players", "Dramatic speed contrast is the cleanest test — hide and listen for slower footsteps", "Speed change is immediate, not gradual", "Running from a Revenant with line of sight is almost impossible", "Hiding is the only reliable counter")),
            GhostEntry("Shade", ("EMF 5", "Writing", "Freezing"), "35%", "1.7 m/s", "Quiet room", ("Identity: Random gender and model", "Strength: Very stealthy — produces fewer interactions than any other ghost", "Weakness: Cannot hunt while a living player is in the same room", "Will not start a hunt above 35% average sanity", "Will not trigger ghost events if a player is in its room", "0% chance of a ghost event at 100% sanity, increasing by 2% per percent of sanity lost", "Higher chance of appearing as a shadow form during events")),
            GhostEntry("Spirit", ("EMF 5", "Spirit Box", "Writing"), "50%", "1.7 m/s", "Long incense", ("Identity: Random gender and model", "Strength: No unique offensive ability — behaves as the default baseline ghost", "Weakness: Smudging it prevents hunts for 180 seconds instead of the usual 90", "No other behavioral identifiers — relies on the smudge timer", "Use a smudge stick and time the next hunt to confirm", "Often identified by elimination")),
            GhostEntry("Thaye", ("Ghost Orbs", "Writing", "DOTS"), "15 - 75%", "1.0 - 2.75 m/s", "Aging", ("Identity: Random gender and model", "Strength: Starts very fast (up to 2.75 m/s) and hunts at 75% sanity when young", "Weakness: Ages every 1-2 minutes a player is in its room, becoming progressively weaker", "Each age step reduces hunt threshold by 6% and lowers speed", "At age 10 it hunts only below 15% sanity", "Will tell you its age on an Ouija board (response increases over time)", "Does not gain speed from line of sight", "Activity is much higher at the start of a contract and tapers off")),
            GhostEntry("The Mimic", ("Spirit Box", "Ultraviolet", "Freezing", "Ghost Orbs"), "10 / 50 / 100%", "Varies (mimic)", "Fake orbs", ("Identity: Random gender and model", "Strength: Mimics behaviors and abilities of another ghost type, changing every 1-2 minutes", "Weakness: Always produces Ghost Orbs as a hidden fourth piece of evidence", "Visible orbs even when Ghost Orbs is not one of its three listed evidences", "Behavior may contradict the confirmed evidence types", "Can mimic any of the 28 other ghosts", "Often confirmed by elimination when something doesn't add up")),
            GhostEntry("The Twins", ("EMF 5", "Spirit Box", "Freezing"), "50%", "1.5 / 1.9 m/s", "Dual interactions", ("Identity: Random gender and model (both twins share appearance)", "Strength: Two interaction points — one main, one decoy — that can fire simultaneously", "Weakness: Reveals itself through unusual activity patterns on the truck monitor", "One twin is slightly slower than normal (1.5 m/s), one is slightly faster (1.9 m/s)", "Only one twin hunts per hunt, randomly chosen", "Two interactions in different locations at the same time confirms it", "Activity monitor shows unusual back-and-forth patterns")),
            GhostEntry("Wraith", ("EMF 5", "Spirit Box", "DOTS"), "50%", "1.7 m/s", "Teleport", ("Identity: Random gender and model", "Strength: Can teleport to any player in the location, creating an EMF 2 reading at their spot", "Weakness: Refuses to step on salt — leaves no trail", "The only ghost that does not interact with salt at all", "Can travel through walls during roams", "No footprints in salt confirms it (combined with salt evidence on the map)", "Floating ghost — does not touch the ground")),
            GhostEntry("Yokai", ("Spirit Box", "Ghost Orbs", "DOTS"), "50 / 80%", "1.7 m/s", "Talking", ("Identity: Random gender and model", "Strength: Hunt sanity threshold rises to 80% when players talk within 2.5m", "Weakness: Hearing range during hunts shrinks to 2.5m (from the standard 9m)", "Triggered by voice chat near the ghost", "Stay silent during hunts and it likely walks right past you", "Music Box needs to be within 2.5m to work (instead of 5m)", "Best test: speak loudly near the ghost room and watch for an early hunt")),
            GhostEntry("Yurei", ("Ghost Orbs", "Freezing", "DOTS"), "50%", "1.7 m/s", "Door trap", ("Identity: Random gender and model", "Strength: Drains 15% sanity from all players within 7.5m when using its door ability", "Weakness: Smudging traps it in its room for 90 seconds, blocking roaming and DOTS", "Will only fully open or fully close a door — never partway", "Can also touch a door twice in rapid succession, producing two EMF 2 readings", "Cannot use its ability if no open doors exist in its room", "Salt at the doorway is a good test: place incense, then watch movement")),
        ]

    def _build_ghost_rules(self) -> dict[str, dict[str, object]]:
        def rule(hunt_min: int, hunt_max: int, speed_flags: set[str], los: bool = True) -> dict[str, object]:
            return {
                "hunt_min": hunt_min,
                "hunt_max": hunt_max,
                "speed_flags": set(speed_flags),
                "los": bool(los),
            }

        return {
            "Aswang": rule(50, 50, {"slow", "fast"}),
            "Banshee": rule(12, 87, {"normal"}),
            "Dayan": rule(45, 65, {"slow", "normal", "fast"}),
            "Demon": rule(70, 100, {"normal"}),
            "Deogen": rule(40, 40, {"slow", "fast"}, False),
            "Gallu": rule(40, 60, {"slow", "normal", "fast"}),
            "Goryo": rule(50, 50, {"normal"}),
            "Hantu": rule(50, 50, {"slow", "fast"}),
            "Jinn": rule(50, 50, {"normal", "fast"}),
            "Kormos": rule(50, 70, {"normal", "fast"}),
            "Mare": rule(40, 60, {"normal"}),
            "Moroi": rule(50, 50, {"slow", "fast"}),
            "Myling": rule(50, 50, {"normal"}),
            "Obake": rule(50, 50, {"normal"}),
            "Obambo": rule(10, 65, {"slow", "normal", "fast"}),
            "Oni": rule(50, 50, {"normal"}),
            "Onryo": rule(40, 100, {"normal"}),
            "Phantom": rule(50, 50, {"normal"}),
            "Poltergeist": rule(50, 50, {"normal"}),
            "Raiju": rule(50, 65, {"normal", "fast"}),
            "Revenant": rule(50, 50, {"slow", "fast"}),
            "Shade": rule(35, 35, {"normal"}),
            "Spirit": rule(50, 50, {"normal"}),
            "Thaye": rule(15, 75, {"slow", "normal", "fast"}),
            "The Mimic": rule(10, 100, {"slow", "normal", "fast"}),
            "The Twins": rule(50, 50, {"slow", "normal", "fast"}),
            "Wraith": rule(50, 50, {"normal"}),
            "Yokai": rule(50, 80, {"normal"}),
            "Yurei": rule(50, 50, {"normal"}),
        }

    def _refresh_matches(self):
        selected_evidence = set(self._selected_evidence_filters())
        excluded_evidence = set(self._excluded_evidence_filters())
        findable_count = self._findable_evidence_count()
        selected_speed = self._selected_speed_filters()
        selected_sanity = self._selected_sanity_filters()
        behavior_active = any(chk.isChecked() for chk in self._behavior_filter_checks.values())
        any_filters = bool(selected_evidence or excluded_evidence or behavior_active)
        any_filters = any_filters or bool(selected_speed or selected_sanity)
        self._update_evidence_slots_hint(len(selected_evidence), findable_count)
        visible_cards = []
        for chk in self._evidence_checks.values():
            chk.setProperty("evidenceState", chk.evidence_state())
            chk.style().unpolish(chk)
            chk.style().polish(chk)
            chk.update()
        for card in self._ghost_cards:
            entry_name = card.entry.name
            behavior_match = self._ghost_matches_behavior(entry_name)
            evidence_ok = self._ghost_matches_evidence(
                entry_name, selected_evidence, excluded_evidence, findable_count
            )
            match = (
                behavior_match
                and evidence_ok
                and self._ghost_matches_speed(card.entry.name, selected_speed)
                and self._ghost_matches_sanity(card.entry.name, selected_sanity)
            )
            visible = (match if any_filters else True)
            if self._search_filter and self._search_filter not in entry_name.lower():
                visible = False
            is_selected = getattr(self, "_selected_ghost", None) == entry_name
            forced_tells = tuple(
                forced_evidence_tell_lines(
                    entry_name,
                    card.entry.evidence,
                    selected_evidence,
                    excluded_evidence,
                    findable_count,
                )
            )
            card.set_tell_lines(forced_tells)
            card.setVisible(visible)
            card.set_match(bool(any_filters and match))
            card.set_selected(bool(is_selected))
            if visible:
                visible_cards.append(card)
        self._rebuild_ghost_grid(visible_cards)
        self._update_compact_shortlist()

    def _update_compact_shortlist(self) -> None:
        selected_evidence = set(self._selected_evidence_filters())
        excluded_evidence = set(self._excluded_evidence_filters())
        findable_count = self._findable_evidence_count()
        shortlist = ghost_shortlist(
            self._ghost_entries,
            selected_evidence,
            excluded_evidence,
            findable_count,
            self._ghost_matches_evidence,
        )
        selected_speed = self._selected_speed_filters()
        selected_sanity = self._selected_sanity_filters()
        behavior_active = any(chk.isChecked() for chk in self._behavior_filter_checks.values())
        if selected_speed or selected_sanity or behavior_active:
            shortlist = [
                entry
                for entry in shortlist
                if self._ghost_matches_speed(entry.name, selected_speed)
                and self._ghost_matches_sanity(entry.name, selected_sanity)
                and self._ghost_matches_behavior(entry.name)
            ]
        if self._compact_window and self._compact_window.isVisible():
            self._compact_window.set_shortlist([e.name for e in shortlist])

    def _rebuild_ghost_grid(self, visible_cards: list[GhostCard]):
        lay = getattr(self, "ghost_grid", None)
        if lay is None:
            return
        while lay.count():
            item = lay.takeAt(0)
            widget = item.widget()
            if widget is not None:
                lay.removeWidget(widget)
        for index, card in enumerate(visible_cards):
            lay.addWidget(card, index // 3, index % 3)

    def _ghost_entries_by_name(self) -> dict[str, GhostEntry]:
        return {entry.name: entry for entry in self._ghost_entries}

    def _selected_evidence_filters(self) -> list[str]:
        filters = []
        for evidence_name, chk in self._evidence_checks.items():
            if chk.checkState() == Qt.Checked:
                filters.append(evidence_name)
        return filters

    def _excluded_evidence_filters(self) -> list[str]:
        filters = []
        for evidence_name, chk in self._evidence_checks.items():
            if chk.checkState() == Qt.PartiallyChecked:
                filters.append(evidence_name)
        return filters

    def _selected_speed_filters(self) -> set[str]:
        selected = set()
        if self.chk_slow.isChecked():
            selected.add("slow")
        if self.chk_normal.isChecked():
            selected.add("normal")
        if self.chk_fast.isChecked():
            selected.add("fast")
        return selected

    def _selected_sanity_filters(self) -> set[str]:
        selected = set()
        if self.chk_late.isChecked():
            selected.add("late")
        if self.chk_norm.isChecked():
            selected.add("normal")
        if self.chk_early.isChecked():
            selected.add("early")
        if self.chk_very_early.isChecked():
            selected.add("very_early")
        return selected

    def _findable_evidence_count(self) -> int:
        return int(self._settings.forced_evidence_count)

    def _tri_state(self, chk: QCheckBox) -> str:
        if chk.checkState() == Qt.Checked:
            return "include"
        if chk.checkState() == Qt.PartiallyChecked:
            return "exclude"
        return "neutral"

    def _count_included_evidence(self) -> int:
        return sum(
            1 for chk in self._evidence_checks.values() if chk.checkState() == Qt.Checked
        )

    def _on_evidence_state_changed(self, _state: int) -> None:
        sender = self.sender()
        findable = self._findable_evidence_count()

        if isinstance(sender, TriStateEvidenceCheckBox):
            evidence_name = next(
                (name for name, chk in self._evidence_checks.items() if chk is sender),
                None,
            )
            if findable == 0:
                if evidence_name != MIMIC_FAKE_EVIDENCE:
                    sender.blockSignals(True)
                    sender.setCheckState(Qt.Unchecked)
                    sender.blockSignals(False)
            elif sender.checkState() == Qt.Checked and self._count_included_evidence() > findable:
                sender.blockSignals(True)
                sender.setCheckState(Qt.Unchecked)
                sender.blockSignals(False)

        self._apply_evidence_enable_states()
        self._refresh_matches()

    def _sync_evidence_to_difficulty_limits(self) -> None:
        findable = self._findable_evidence_count()
        for name, chk in self._evidence_checks.items():
            if findable == 0 and name != MIMIC_FAKE_EVIDENCE and chk.checkState() != Qt.Unchecked:
                chk.blockSignals(True)
                chk.setCheckState(Qt.Unchecked)
                chk.blockSignals(False)

        if findable > 0:
            included = [
                chk for chk in self._evidence_checks.values() if chk.checkState() == Qt.Checked
            ]
            while len(included) > findable:
                chk = included.pop()
                chk.blockSignals(True)
                chk.setCheckState(Qt.Unchecked)
                chk.blockSignals(False)

        self._apply_evidence_enable_states()

    def _apply_evidence_enable_states(self) -> None:
        if not self._evidence_checks:
            return
        findable = self._findable_evidence_count()
        included = self._count_included_evidence()
        for name, chk in self._evidence_checks.items():
            if findable == 0:
                chk.setEnabled(name == MIMIC_FAKE_EVIDENCE)
                continue
            chk.setEnabled(chk.checkState() != Qt.Unchecked or included < findable)

    def _update_evidence_slots_hint(self, found_count: int, findable_count: int) -> None:
        if not hasattr(self, "lbl_evidence_slots"):
            return
        hidden = max(0, 3 - findable_count)
        if findable_count <= 0:
            self.lbl_evidence_slots.setText(
                "Apocalypse: only Ghost Orbs can be marked — identifies The Mimic."
            )
            self.lbl_evidence_slots.setStyleSheet("")
            return
        if found_count >= findable_count:
            self.lbl_evidence_slots.setText(
                f"All {findable_count} evidence slot{'s' if findable_count != 1 else ''} filled — "
                f"filtering by forced hidden evidence ({hidden} hidden per ghost)."
            )
            self.lbl_evidence_slots.setStyleSheet("color: #3ddc84; font-weight: 700;")
            return
        remaining = findable_count - found_count
        self.lbl_evidence_slots.setStyleSheet("")
        self.lbl_evidence_slots.setText(
            f"Mark up to {findable_count} found evidence ({found_count} selected, {remaining} remaining). "
            f"{hidden} evidence type{'s' if hidden != 1 else ''} forced hidden on this difficulty."
        )

    def _ghost_matches_behavior(self, ghost_name: str) -> bool:
        rule = self._ghost_rules[ghost_name]
        hunt_min = int(rule["hunt_min"])
        hunt_max = int(rule["hunt_max"])
        for label, chk in self._behavior_filter_checks.items():
            if not behavior_filter_match(
                ghost_name,
                label,
                self._behavior_filter_targets.get(label),
                self._behavior_filter_special.get(label),
                chk.isChecked(),
                hunt_min,
                hunt_max,
            ):
                return False
        return True

    def _ghost_matches_evidence(
        self,
        ghost_name: str,
        selected_evidence: set[str],
        excluded_evidence: set[str],
        findable_count: int | None = None,
    ) -> bool:
        if findable_count is None:
            findable_count = self._findable_evidence_count()
        entry = self._ghost_entries_by_name()[ghost_name]
        return ghost_matches_evidence(
            ghost_name,
            entry.evidence,
            selected_evidence,
            excluded_evidence,
            findable_count,
        )

    def _ghost_matches_speed(self, ghost_name: str, selected_speed: set[str]) -> bool:
        if not selected_speed:
            return True
        rule = self._ghost_rules[ghost_name]
        available = set(rule["speed_flags"])
        return not selected_speed or bool(available.intersection(selected_speed))

    def _ghost_matches_sanity(self, ghost_name: str, selected_sanity: set[str]) -> bool:
        if not selected_sanity:
            return True
        rule = self._ghost_rules[ghost_name]
        hunt_min = int(rule["hunt_min"])
        hunt_max = int(rule["hunt_max"])
        matches = set()
        if hunt_min < 40:
            matches.add("late")
        if hunt_min <= 50 and hunt_max >= 40:
            matches.add("normal")
        if hunt_max > 50:
            matches.add("early")
        if hunt_max >= 75:
            matches.add("very_early")
        return bool(matches.intersection(selected_sanity))

    def _set_selected_ghost(self, name: str):
        self._selected_ghost = name

    def _handle_card_click(self, name: str):
        self._selected_ghost = name if self._selected_ghost != name else None
        self._refresh_matches()

    def _reset_filters(self):
        for chk in tuple(self._evidence_checks.values()) + tuple(self._behavior_filter_checks.values()) + (
            self.chk_slow,
            self.chk_normal,
            self.chk_fast,
            self.chk_late,
            self.chk_norm,
            self.chk_early,
            self.chk_very_early,
        ):
            chk.blockSignals(True)
            if isinstance(chk, TriStateEvidenceCheckBox):
                chk.setCheckState(Qt.Unchecked)
                chk.setProperty("evidenceState", chk.evidence_state())
                chk.style().unpolish(chk)
                chk.style().polish(chk)
                chk.update()
            else:
                chk.setChecked(False)
            chk.blockSignals(False)
        self._selected_ghost = None
        self.search_input.clear()
        self._search_filter = ""
        self._apply_evidence_enable_states()
        self._refresh_matches()

    def _sync_sidebar_width(self):
        if not hasattr(self, "sidebar"):
            return
        sidebar_width = max(200, min(280, int(self.width() * 0.15)))
        if self.sidebar.width() != sidebar_width:
            self.sidebar.setFixedWidth(sidebar_width)

    def resizeEvent(self, event):
        QMainWindow.resizeEvent(self, event)
        self._sync_sidebar_width()
        self._refresh_matches()

    def mousePressEvent(self, event):
        # Allow dragging from empty areas of the window shell.
        if event.button() == Qt.LeftButton and self.childAt(event.pos()) is None:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        QMainWindow.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        QMainWindow.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = None
            event.accept()
            return
        QMainWindow.mouseReleaseEvent(self, event)

    def apply_theme(self, _theme_id: str | None = None):
        # Keep the Phasmophobia styling self-contained while still honoring the
        # application theme for the backdrop gradients.
        self.update()

    def _on_forced_evidence_changed(self) -> None:
        self._settings.forced_evidence_count = int(self.cmb_forced_evidence.currentData())
        if hasattr(self, "page_difficulty"):
            self.page_difficulty.set_evidence_count(self._settings.forced_evidence_count)
        if hasattr(self, "page_settings"):
            self.page_settings.cmb_forced.blockSignals(True)
            for i in range(self.page_settings.cmb_forced.count()):
                if self.page_settings.cmb_forced.itemData(i) == self._settings.forced_evidence_count:
                    self.page_settings.cmb_forced.setCurrentIndex(i)
                    break
            self.page_settings.cmb_forced.blockSignals(False)
        self._sync_evidence_to_difficulty_limits()
        save_settings(self._settings)
        self._refresh_matches()

    def _on_difficulty_builder_changed(self, state: DifficultyState) -> None:
        self._settings.forced_evidence_count = int(state.evidence_count)
        if hasattr(self, "cmb_forced_evidence"):
            self.cmb_forced_evidence.blockSignals(True)
            for i in range(self.cmb_forced_evidence.count()):
                if self.cmb_forced_evidence.itemData(i) == state.evidence_count:
                    self.cmb_forced_evidence.setCurrentIndex(i)
                    break
            self.cmb_forced_evidence.blockSignals(False)
        if hasattr(self, "page_settings"):
            self.page_settings.cmb_forced.blockSignals(True)
            for i in range(self.page_settings.cmb_forced.count()):
                if self.page_settings.cmb_forced.itemData(i) == state.evidence_count:
                    self.page_settings.cmb_forced.setCurrentIndex(i)
                    break
            self.page_settings.cmb_forced.blockSignals(False)
        self._sync_evidence_to_difficulty_limits()
        save_settings(self._settings)
        self._refresh_matches()

    def _on_display_boost_preview(self, settings) -> None:
        self._settings = settings
        self._brightness.apply(
            brightness_enabled=settings.brightness_enabled,
            brightness_level=settings.brightness_level,
            gamma_enabled=settings.gamma_enabled,
            gamma_level=settings.gamma_level,
        )
        if self._compact_window is not None:
            self._compact_window.set_corner_radius(settings.compact_radius)

    def _on_plugin_settings_changed(self, settings) -> None:
        self._settings = settings
        if hasattr(self, "cmb_forced_evidence"):
            self.cmb_forced_evidence.blockSignals(True)
            for i in range(self.cmb_forced_evidence.count()):
                if self.cmb_forced_evidence.itemData(i) == settings.forced_evidence_count:
                    self.cmb_forced_evidence.setCurrentIndex(i)
                    break
            self.cmb_forced_evidence.blockSignals(False)
        if hasattr(self, "page_difficulty"):
            self.page_difficulty.set_evidence_count(settings.forced_evidence_count)
        self._sync_evidence_to_difficulty_limits()
        self._apply_plugin_settings(settings)
        self._refresh_matches()

    def _on_timer_settings_changed(self, settings) -> None:
        self._settings = settings
        save_settings(settings)
        self._apply_plugin_settings(settings)

    def _apply_plugin_settings(self, settings) -> None:
        self._timer_overlays.apply_styles(settings)
        self._timer_overlays.apply_visibility(settings)
        self._bpm_finder.apply_style(settings)
        self._bpm_finder.set_hud_enabled(settings.overlay_bpm)
        self._brightness.apply(
            brightness_enabled=settings.brightness_enabled,
            brightness_level=settings.brightness_level,
            gamma_enabled=settings.gamma_enabled,
            gamma_level=settings.gamma_level,
        )
        self._timer_overlays.position_overlays()
        if self._compact_window is not None:
            self._compact_window.set_corner_radius(settings.compact_radius)

    def _on_search_text(self, text: str) -> None:
        self._search_filter = text.strip().lower()
        self._refresh_matches()

    def _toggle_compact_window(self) -> None:
        if self._compact_window is None:
            self._compact_window = PhasmoCompactWindow()
            self._compact_window.evidence_changed.connect(self._on_compact_evidence_changed)
        if self._compact_window.isVisible():
            self._compact_window.hide()
            return
        for evidence_name, chk in self._evidence_checks.items():
            self._compact_window.set_evidence_state(evidence_name, chk.evidence_state())
        self._compact_window.set_corner_radius(self._settings.compact_radius)
        self._update_compact_shortlist()
        self._compact_window.show()
        self._compact_window.raise_()

    def _on_compact_evidence_changed(self, evidence: str, state: str) -> None:
        chk = self._evidence_checks.get(evidence)
        if chk is None:
            return
        findable = self._findable_evidence_count()
        if findable == 0 and evidence != MIMIC_FAKE_EVIDENCE:
            return
        chk.blockSignals(True)
        if state == "include":
            chk.setCheckState(Qt.Checked)
        elif state == "exclude":
            chk.setCheckState(Qt.PartiallyChecked)
        else:
            chk.setCheckState(Qt.Unchecked)
        chk.blockSignals(False)
        if findable > 0 and chk.checkState() == Qt.Checked and self._count_included_evidence() > findable:
            chk.blockSignals(True)
            chk.setCheckState(Qt.Unchecked)
            chk.blockSignals(False)
        self._apply_evidence_enable_states()
        self._refresh_matches()

    def _refresh_version_banner(self) -> None:
        path = default_save_path()
        version = None
        if path.is_file():
            try:
                text, _iv, _plain = load_save(path)
                version = read_game_version_from_save(text)
            except Exception:
                version = None
        if version and version != SUPPORTED_VERSION:
            self.lbl_version_banner.setText(
                f"Save game version {version} differs from cheat sheet data ({SUPPORTED_VERSION}). "
                "Ghost stats or overlays may be outdated for your build."
            )
            self.lbl_version_banner.setStyleSheet("color: #e09030; font-weight: 700;")
            self.lbl_version_banner.show()
        else:
            self.lbl_version_banner.hide()

    def _on_overlay_hotkey(self, action: str) -> None:
        if action == "bpm_tap":
            self._bpm_finder.tap()
        elif action == "bpm_reset":
            self._bpm_finder.reset()
        elif action == "smudge":
            self._timer_overlays.toggle_smudge()
        elif action == "crucifix":
            self._timer_overlays.toggle_crucifix()
        elif action == "obambo":
            self._timer_overlays.toggle_obambo()
        elif action == "gamma":
            self._brightness.toggle_gamma()
        elif action == "brightness":
            self._brightness.toggle_brightness()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_plugin_settings(self._settings)
        self._timer_overlays.start_global_hotkeys()

    def hideEvent(self, event):
        self._timer_overlays.stop_global_hotkeys()
        super().hideEvent(event)

    def _go_back(self):
        if self._compact_window is not None:
            self._compact_window.close()
        self._timer_overlays.shutdown()
        self._bpm_finder.shutdown()
        self._brightness.shutdown()
        self.go_back_to_autoclicker.emit()

    def closeEvent(self, event):
        self._timer_overlays.shutdown()
        self._bpm_finder.shutdown()
        self._brightness.shutdown()
        self.go_back_to_autoclicker.emit()
        event.accept()
