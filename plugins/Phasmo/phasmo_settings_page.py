"""Settings page for overlay toggles and plugin options."""
from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from plugins.Phasmo.phasmo_settings import PhasmoSettings, save_settings
from plugins.Phasmo.phasmo_fan_disclaimer import SHORT_DISCLAIMER, show_fan_content_disclaimer


class PhasmoSettingsPage(QWidget):
    settings_changed = pyqtSignal(object)
    display_boost_preview = pyqtSignal(object)

    def __init__(self, settings: PhasmoSettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(80)
        self._preview_timer.timeout.connect(self._emit_display_preview)
        outer = QVBoxLayout(self)
        outer.setSpacing(12)

        head = QLabel("Settings")
        head.setObjectName("PhasmoSectionTitle")
        outer.addWidget(head)
        sub = QLabel("Overlays stay on screen across all Phasmo tabs when enabled.")
        sub.setObjectName("PhasmoToolCopy")
        sub.setWordWrap(True)
        outer.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        lay = QVBoxLayout(host)

        hud = QLabel("On-screen overlays")
        hud.setObjectName("PhasmoSectionTitle")
        lay.addWidget(hud)

        self.chk_smudge = QCheckBox("Smudge timer HUD (Num1)")
        self.chk_crucifix = QCheckBox("Crucifix timer HUD (Num2)")
        self.chk_obambo = QCheckBox("Obambo timer HUD (Num3)")
        self.chk_bpm = QCheckBox("BPM finder HUD (F / R)")
        for chk, attr in (
            (self.chk_smudge, "overlay_smudge"),
            (self.chk_crucifix, "overlay_crucifix"),
            (self.chk_obambo, "overlay_obambo"),
            (self.chk_bpm, "overlay_bpm"),
        ):
            chk.setChecked(getattr(settings, attr))
            chk.toggled.connect(self._emit)
            lay.addWidget(chk)

        lay.addWidget(QLabel("Ghost filters"))
        form = QFormLayout()
        self.cmb_forced = QComboBox()
        self.cmb_forced.addItem("3 evidence (Normal / Intermediate / Professional)", 3)
        self.cmb_forced.addItem("2 evidence (Nightmare)", 2)
        self.cmb_forced.addItem("1 evidence (Insanity)", 1)
        self.cmb_forced.addItem("0 evidence (Apocalypse)", 0)
        for i in range(self.cmb_forced.count()):
            if self.cmb_forced.itemData(i) == settings.forced_evidence_count:
                self.cmb_forced.setCurrentIndex(i)
                break
        self.cmb_forced.currentIndexChanged.connect(self._emit)
        form.addRow("Forced evidence slots", self.cmb_forced)

        lay.addLayout(form)

        bright = QLabel("Display boost")
        bright.setObjectName("PhasmoSectionTitle")
        lay.addWidget(bright)
        bright_copy = QLabel(
            "Best results: enable both. Gamma auto-crank the hardware backlight to 100%, then lifts dark "
            "areas with a software curve. Past that you are washing out contrast, not making more light. "
            "HDR peak brightness must be enabled in Windows display settings — it cannot be pushed from here."
        )
        bright_copy.setObjectName("PhasmoToolCopy")
        bright_copy.setWordWrap(True)
        lay.addWidget(bright_copy)

        monitor = QLabel("Hardware backlight")
        monitor.setObjectName("PhasmoSectionTitle")
        lay.addWidget(monitor)
        monitor_copy = QLabel(
            "The real brightness knob — your monitor's actual backlight. Use 100% for the biggest real gain."
        )
        monitor_copy.setObjectName("PhasmoToolCopy")
        monitor_copy.setWordWrap(True)
        lay.addWidget(monitor_copy)

        self.chk_brightness = QCheckBox("Enable hardware backlight (Num5)")
        self.chk_brightness.setChecked(settings.brightness_enabled)
        self.chk_brightness.toggled.connect(self._emit)
        lay.addWidget(self.chk_brightness)

        self.brightness_level = QSlider(Qt.Horizontal)
        self.brightness_level.setRange(0, 100)
        self.brightness_level.setValue(settings.brightness_level)
        self.brightness_level.setTracking(True)
        self.brightness_level.valueChanged.connect(self._on_brightness_level_changed)
        self.brightness_level.sliderReleased.connect(self._commit_settings)
        self.lbl_brightness_level = QLabel(self._brightness_label(settings.brightness_level))
        self.lbl_brightness_level.setObjectName("PhasmoToolCopy")
        lay.addWidget(self.lbl_brightness_level)
        lay.addWidget(self.brightness_level)

        gamma = QLabel("Gamma boost")
        gamma.setObjectName("PhasmoSectionTitle")
        lay.addWidget(gamma)
        gamma_copy = QLabel(
            "Lifts the gamma curve (raises blacks) for a brighter perceived image in fullscreen games. "
            "Automatically sets hardware backlight to 100% while active."
        )
        gamma_copy.setObjectName("PhasmoToolCopy")
        gamma_copy.setWordWrap(True)
        lay.addWidget(gamma_copy)

        self.chk_gamma = QCheckBox("Enable gamma boost (Num4)")
        self.chk_gamma.setChecked(settings.gamma_enabled)
        self.chk_gamma.toggled.connect(self._emit)
        lay.addWidget(self.chk_gamma)

        self.gamma_level = QSlider(Qt.Horizontal)
        self.gamma_level.setRange(0, 100)
        self.gamma_level.setValue(settings.gamma_level)
        self.gamma_level.setTracking(True)
        self.gamma_level.valueChanged.connect(self._on_gamma_level_changed)
        self.gamma_level.sliderReleased.connect(self._commit_settings)
        self.lbl_gamma_level = QLabel(self._gamma_label(settings.gamma_level))
        self.lbl_gamma_level.setObjectName("PhasmoToolCopy")
        lay.addWidget(self.lbl_gamma_level)
        lay.addWidget(self.gamma_level)

        compact = QLabel("Compact window")
        compact.setObjectName("PhasmoSectionTitle")
        lay.addWidget(compact)
        self.compact_radius = QSlider(Qt.Horizontal)
        self.compact_radius.setRange(8, 28)
        self.compact_radius.setValue(settings.compact_radius)
        self.compact_radius.valueChanged.connect(self._schedule_display_preview)
        self.compact_radius.sliderReleased.connect(self._commit_settings)
        lay.addWidget(QLabel("Corner radius"))
        lay.addWidget(self.compact_radius)

        legal = QLabel("Fan content notice")
        legal.setObjectName("PhasmoSectionTitle")
        lay.addWidget(legal)
        legal_copy = QLabel(SHORT_DISCLAIMER)
        legal_copy.setObjectName("PhasmoToolCopy")
        legal_copy.setWordWrap(True)
        lay.addWidget(legal_copy)
        legal_btn = QPushButton("View full Kinetic Games notice")
        legal_btn.setObjectName("PhasmoToolButton")
        legal_btn.setCursor(Qt.PointingHandCursor)
        legal_btn.clicked.connect(lambda: show_fan_content_disclaimer(self))
        lay.addWidget(legal_btn)

        lay.addStretch(1)
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)

    def _brightness_label(self, level: int) -> str:
        return f"Hardware backlight: {int(level)}%"

    def _gamma_label(self, level: int) -> str:
        factor = 1.0 + (int(level) / 100.0) * 0.4
        offset = (int(level) / 100.0) * 40.0
        return f"Gamma lift: {int(level)}% (factor {factor:.1f}, offset {offset:.0f})"

    def _on_brightness_level_changed(self, value: int) -> None:
        self.lbl_brightness_level.setText(self._brightness_label(value))
        self._schedule_display_preview()

    def _on_gamma_level_changed(self, value: int) -> None:
        self.lbl_gamma_level.setText(self._gamma_label(value))
        self._schedule_display_preview()

    def _schedule_display_preview(self) -> None:
        self._preview_timer.start()

    def _emit_display_preview(self) -> None:
        self.display_boost_preview.emit(self.collect())

    def _commit_settings(self) -> None:
        self._preview_timer.stop()
        self._emit()

    def _emit(self) -> None:
        s = self.collect()
        save_settings(s)
        self.settings_changed.emit(s)

    def collect(self) -> PhasmoSettings:
        self._settings.overlay_smudge = self.chk_smudge.isChecked()
        self._settings.overlay_crucifix = self.chk_crucifix.isChecked()
        self._settings.overlay_obambo = self.chk_obambo.isChecked()
        self._settings.overlay_bpm = self.chk_bpm.isChecked()
        self._settings.forced_evidence_count = int(self.cmb_forced.currentData())
        self._settings.compact_radius = self.compact_radius.value()
        self._settings.brightness_enabled = self.chk_brightness.isChecked()
        self._settings.brightness_level = self.brightness_level.value()
        self._settings.gamma_enabled = self.chk_gamma.isChecked()
        self._settings.gamma_level = self.gamma_level.value()
        return self._settings
