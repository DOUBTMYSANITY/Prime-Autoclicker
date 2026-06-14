from __future__ import annotations

import json
import os
import sys

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QDialog, QLineEdit, QTextEdit, QListWidget, QListWidgetItem,
    QAbstractItemView,
)

from app.styling.localization import tr
from app.styling.themes import get_dialog_stylesheet, get_theme
from app.gui.widgets import Card, add_shadow, ToastNotification


PRESETS_FILE = os.path.join(os.path.expanduser("~"), ".mtautoclicker_presets.json")


def _load_presets() -> list[dict]:
    try:
        with open(PRESETS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _show_preset_save_error(message: str):
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
        print(f"[Presets] Failed to show error toast: {exc}", file=sys.stderr)


def _save_presets(presets: list[dict]) -> bool:
    try:
        with open(PRESETS_FILE, "w") as f:
            json.dump(presets, f, indent=2)
        return True
    except Exception as exc:
        print(f"[Presets] Failed to save presets: {exc}", file=sys.stderr)
        _show_preset_save_error("Couldn't save presets. Check file permissions.")
        return False


class PresetDialog(QDialog):
    """Styled popup to create/edit a preset."""

    def __init__(self, parent=None, name: str = "", desc: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Save Preset")
        self.setFixedSize(420, 300)
        self.setStyleSheet(get_dialog_stylesheet())
        p = get_theme().get("palette", {})
        label_color = p.get("text_secondary", "rgba(233,237,255,0.7)")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        title = QLabel("💾  Save Preset")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        lay.addWidget(title)

        lbl_name = QLabel("Preset Name")
        lbl_name.setStyleSheet(f"font-size: 12px; color: {label_color};")
        self.input_name = QLineEdit(name)
        self.input_name.setPlaceholderText("e.g. Fast Left Click")
        self.input_name.setFixedHeight(40)

        lbl_desc = QLabel("Description (optional)")
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {label_color};")
        self.input_desc = QTextEdit(desc)
        self.input_desc.setPlaceholderText("What is this preset for?")
        self.input_desc.setFixedHeight(70)

        lay.addWidget(lbl_name)
        lay.addWidget(self.input_name)
        lay.addWidget(lbl_desc)
        lay.addWidget(self.input_desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Preset")
        self.btn_save.setObjectName("SaveBtn")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.accept)

        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        lay.addLayout(btn_row)

    def get_values(self) -> tuple[str, str]:
        return self.input_name.text().strip(), self.input_desc.toPlainText().strip()


class PresetPage(QWidget):
    """Presets page: list saved presets, create new ones, load them."""

    preset_loaded = pyqtSignal(dict)  # emitted when user loads a preset

    def __init__(self, parent=None):
        super().__init__(parent)
        self._presets = _load_presets()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # Hero
        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=28, y=10, alpha=110)
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(28, 22, 28, 22)
        hl.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(8)
        self.hero_title = QLabel(tr("profiles"))
        self.hero_title.setObjectName("HeroTitle")
        self.hero_sub = QLabel(tr("profiles_sub"))
        self.hero_sub.setObjectName("HeroSub")
        left.addWidget(self.hero_title)
        left.addWidget(self.hero_sub)
        left.addStretch(1)

        self.btn_new = QPushButton(tr("new_preset"))
        self.btn_new.setObjectName("StartStopBtn")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.setFixedHeight(42)
        self.btn_new.setMinimumWidth(160)

        right_col = QVBoxLayout()
        right_col.addWidget(self.btn_new, 0, Qt.AlignRight)
        right_col.addStretch(1)

        hl.addLayout(left, 1)
        hl.addLayout(right_col, 0)

        # Preset list card
        list_card = Card()
        list_card.setObjectName("ConfigCard")
        add_shadow(list_card, blur=26, y=10, alpha=110)
        lc_lay = QVBoxLayout(list_card)
        lc_lay.setContentsMargins(20, 18, 20, 18)
        lc_lay.setSpacing(14)

        lc_header = QHBoxLayout()
        lc_header.setSpacing(10)
        lc_icon = QLabel("📋")
        lc_icon.setObjectName("HeaderIcon")
        lc_icon.setFixedSize(34, 34)
        lc_icon.setAlignment(Qt.AlignCenter)
        self.lbl_saved_presets = QLabel(tr("saved_presets"))
        self.lbl_saved_presets.setObjectName("CardHeader")
        lc_header.addWidget(lc_icon)
        lc_header.addWidget(self.lbl_saved_presets)
        lc_header.addStretch(1)
        lc_lay.addLayout(lc_header)

        self.preset_list = QListWidget()
        self.preset_list.setObjectName("PresetList")
        self.preset_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.preset_list.setMinimumHeight(200)
        lc_lay.addWidget(self.preset_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_load = QPushButton(tr("load"))
        self.btn_load.setObjectName("ToggleButton")
        self.btn_load.setProperty("active", True)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.setFixedHeight(38)

        self.btn_delete = QPushButton("🗑  " + tr("delete").lstrip("🗑  "))
        self.btn_delete.setObjectName("ToggleButton")
        self.btn_delete.setProperty("active", False)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFixedHeight(38)

        btn_row.addWidget(self.btn_load)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch(1)
        lc_lay.addLayout(btn_row)
        lc_lay.addStretch(1)

        # Hotkey profiles card
        hk_card = Card()
        hk_card.setObjectName("ConfigCard")
        add_shadow(hk_card, blur=26, y=10, alpha=110)
        hk_lay = QVBoxLayout(hk_card)
        hk_lay.setContentsMargins(20, 18, 20, 18)
        hk_lay.setSpacing(14)

        hk_header = QHBoxLayout()
        hk_header.setSpacing(10)
        hk_icon = QLabel("⌨")
        hk_icon.setObjectName("HeaderIcon")
        hk_icon.setFixedSize(34, 34)
        hk_icon.setAlignment(Qt.AlignCenter)
        self.lbl_hk_title = QLabel(tr("hotkey_profiles"))
        self.lbl_hk_title.setObjectName("CardHeader")
        hk_header.addWidget(hk_icon)
        hk_header.addWidget(self.lbl_hk_title)
        hk_header.addStretch(1)
        hk_lay.addLayout(hk_header)

        hk_inner = Card(radius=16)
        hk_inner.setObjectName("InnerPanel")
        hki_lay = QVBoxLayout(hk_inner)
        hki_lay.setContentsMargins(14, 14, 14, 14)
        hki_lay.setSpacing(10)

        self.hk_desc = QLabel(tr("hotkey_profiles_desc"))
        self.hk_desc.setObjectName("WarnText")
        self.hk_desc.setWordWrap(True)
        hki_lay.addWidget(self.hk_desc)

        self.hk_list = QListWidget()
        self.hk_list.setObjectName("PresetList")
        self.hk_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.hk_list.setMinimumHeight(120)
        hki_lay.addWidget(self.hk_list)

        hk_btn_row = QHBoxLayout()
        hk_btn_row.setSpacing(10)
        self.btn_assign_hk = QPushButton("🔑  " + tr("assign_hotkey"))
        self.btn_assign_hk.setObjectName("ToggleButton")
        self.btn_assign_hk.setProperty("active", True)
        self.btn_assign_hk.setCursor(Qt.PointingHandCursor)
        self.btn_assign_hk.setFixedHeight(38)
        self.btn_assign_hk.clicked.connect(self._assign_hotkey)

        self.btn_clear_hk = QPushButton("✖  Clear Key")
        self.btn_clear_hk.setObjectName("ToggleButton")
        self.btn_clear_hk.setProperty("active", False)
        self.btn_clear_hk.setCursor(Qt.PointingHandCursor)
        self.btn_clear_hk.setFixedHeight(38)
        self.btn_clear_hk.clicked.connect(self._clear_hotkey)

        hk_btn_row.addWidget(self.btn_assign_hk)
        hk_btn_row.addWidget(self.btn_clear_hk)
        hk_btn_row.addStretch(1)
        hki_lay.addLayout(hk_btn_row)
        hki_lay.addStretch(1)
        hk_lay.addWidget(hk_inner)

        lay.addWidget(hero)
        lay.addWidget(list_card)
        lay.addWidget(hk_card)
        lay.addStretch(1)

        # Connect
        self.btn_new.clicked.connect(self._on_new)
        self.btn_load.clicked.connect(self._on_load)
        self.btn_delete.clicked.connect(self._on_delete)
        self._refresh_list()

    def _refresh_list(self):
        self.preset_list.clear()
        self.hk_list.clear()
        for p in self._presets:
            name = p.get("name", "Unnamed")
            desc = p.get("desc", "")
            hk = p.get("hotkey", "")
            hk_label = hk.replace("_", " ").title() if hk else ""
            suffix = f"  [Key: {hk_label}]" if hk else ""
            text = f"{name}  —  {desc}{suffix}" if desc else f"{name}{suffix}"
            self.preset_list.addItem(QListWidgetItem(text))
            hk_text = f"{name}  →  {hk_label}" if hk else f"{name}  →  (none)"
            self.hk_list.addItem(QListWidgetItem(hk_text))

    def _on_new(self):
        # This will be called from MainWindow which passes current config
        pass  # Overridden via signal in MainWindow

    def _on_load(self):
        idx = self.preset_list.currentRow()
        if 0 <= idx < len(self._presets):
            self.preset_loaded.emit(self._presets[idx])

    def _on_delete(self):
        idx = self.preset_list.currentRow()
        if 0 <= idx < len(self._presets):
            self._presets.pop(idx)
            _save_presets(self._presets)
            self._refresh_list()

    def add_preset(self, data: dict):
        self._presets.append(data)
        _save_presets(self._presets)
        self._refresh_list()

    def _assign_hotkey(self):
        idx = self.hk_list.currentRow()
        if idx < 0 or idx >= len(self._presets):
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Assign Hotkey")
        dlg.setFixedSize(360, 140)
        dlg.setStyleSheet(get_dialog_stylesheet())
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        lbl = QLabel(
            f"Set a key token for '{self._presets[idx].get('name', '')}'. "
            "Examples: f8, mouse_x1, r"
        )
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        edit = QLineEdit()
        edit.setPlaceholderText("Key token...")
        lay.addWidget(edit)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("CancelBtn")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok = QPushButton("\u2714  Assign")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(dlg.accept)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)
        if dlg.exec_() == QDialog.Accepted and edit.text().strip():
            self._presets[idx]["hotkey"] = edit.text().strip().lower()
            _save_presets(self._presets)
            self._refresh_list()

    def _clear_hotkey(self):
        idx = self.hk_list.currentRow()
        if idx < 0 or idx >= len(self._presets):
            return
        self._presets[idx]["hotkey"] = ""
        _save_presets(self._presets)
        self._refresh_list()

    def get_preset_hotkeys(self) -> dict:
        """Return {token: preset_data} for all presets with assigned hotkeys."""
        result = {}
        for p in self._presets:
            hk = p.get("hotkey", "")
            if hk:
                result[hk.lower()] = p
        return result

    def get_presets(self) -> list[dict]:
        """Return a shallow copy of stored presets for quick-pick UI use."""
        return list(self._presets)

    def retranslateUi(self):
        """Update all translatable text."""
        self.hero_title.setText(tr("profiles"))
        self.hero_sub.setText(tr("profiles_sub"))
        self.btn_new.setText(tr("new_preset"))
        self.lbl_saved_presets.setText(tr("saved_presets"))
        self.btn_load.setText(tr("load"))
        self.btn_delete.setText(tr("delete"))
        self.lbl_hk_title.setText(tr("hotkey_profiles"))
        self.hk_desc.setText(tr("hotkey_profiles_desc"))
        self.btn_assign_hk.setText("\U0001F511  " + tr("assign_hotkey"))
