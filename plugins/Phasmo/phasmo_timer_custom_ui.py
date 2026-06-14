"""Timers customization tab for overlay HUD styles."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from plugins.Phasmo.phasmo_settings import TIMER_STYLE_PRESETS, PhasmoSettings, TimerStyleConfig


class _TimerEditor(QWidget):
    changed = pyqtSignal()

    def __init__(self, label: str, config: TimerStyleConfig, parent=None):
        super().__init__(parent)
        self._config = config
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        head = QLabel(label)
        head.setObjectName("PhasmoSectionTitle")
        lay.addWidget(head)

        form = QFormLayout()
        self.title = QLineEdit(config.title)
        self.title.textChanged.connect(self._emit)
        form.addRow("Title", self.title)

        self.color = QLineEdit(config.color)
        self.color.textChanged.connect(self._emit)
        form.addRow("Color (#hex)", self.color)

        self.preset = QComboBox()
        self.preset.addItems(list(TIMER_STYLE_PRESETS))
        idx = self.preset.findText(config.preset)
        if idx >= 0:
            self.preset.setCurrentIndex(idx)
        self.preset.currentTextChanged.connect(self._apply_preset)
        form.addRow("Style preset", self.preset)

        self.radius = QSlider(Qt.Horizontal)
        self.radius.setRange(4, 24)
        self.radius.setValue(config.radius)
        self.radius.valueChanged.connect(self._emit)
        form.addRow("Corner radius", self.radius)

        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(50, 100)
        self.opacity.setValue(int(config.opacity * 100))
        self.opacity.valueChanged.connect(self._emit)
        form.addRow("Opacity %", self.opacity)

        self.font_pt = QSlider(Qt.Horizontal)
        self.font_pt.setRange(14, 32)
        self.font_pt.setValue(config.font_pt)
        self.font_pt.valueChanged.connect(self._emit)
        form.addRow("Time font size", self.font_pt)

        self.border = QSlider(Qt.Horizontal)
        self.border.setRange(1, 5)
        self.border.setValue(config.border)
        self.border.valueChanged.connect(self._emit)
        form.addRow("Border width", self.border)

        self.width = QSlider(Qt.Horizontal)
        self.width.setRange(140, 260)
        self.width.setValue(config.width)
        self.width.valueChanged.connect(self._emit)
        form.addRow("Width", self.width)

        lay.addLayout(form)

        row = QHBoxLayout()
        self.btn_preview = QPushButton("Preview on HUD")
        self.btn_preview.clicked.connect(self.changed.emit)
        row.addWidget(self.btn_preview)
        lay.addLayout(row)

    def _apply_preset(self, name: str) -> None:
        preset = TIMER_STYLE_PRESETS.get(name)
        if not preset:
            return
        self.radius.setValue(preset["radius"])
        self.opacity.setValue(int(preset["opacity"] * 100))
        self.font_pt.setValue(preset["font_pt"])
        self.border.setValue(preset["border"])
        self._emit()

    def _emit(self) -> None:
        self.changed.emit()

    def value(self) -> TimerStyleConfig:
        return TimerStyleConfig(
            title=self.title.text().strip() or self._config.title,
            color=self.color.text().strip() or self._config.color,
            preset=self.preset.currentText(),
            radius=self.radius.value(),
            opacity=self.opacity.value() / 100.0,
            font_pt=self.font_pt.value(),
            border=self.border.value(),
            width=self.width.value(),
        )


class TimersCustomizePanel(QWidget):
    settings_changed = pyqtSignal(object)

    def __init__(self, settings: PhasmoSettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        outer = QVBoxLayout(self)
        outer.setSpacing(10)

        head = QLabel("Timer HUD customization")
        head.setObjectName("PhasmoSectionTitle")
        outer.addWidget(head)
        info = QLabel(
            "Style the on-screen timers. Num1/2/3 toggle timers. Enabled HUDs stay visible "
            "while you use any Phasmo tab."
        )
        info.setObjectName("PhasmoToolCopy")
        info.setWordWrap(True)
        outer.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        host_lay = QVBoxLayout(host)

        self.ed_smudge = _TimerEditor("Smudge timer", settings.smudge)
        self.ed_crucifix = _TimerEditor("Crucifix timer", settings.crucifix)
        self.ed_obambo = _TimerEditor("Obambo timer", settings.obambo)
        for ed in (self.ed_smudge, self.ed_crucifix, self.ed_obambo):
            ed.changed.connect(self._emit)
            host_lay.addWidget(ed)

        bpm_head = QLabel("BPM finder HUD")
        bpm_head.setObjectName("PhasmoSectionTitle")
        host_lay.addWidget(bpm_head)
        bpm_form = QFormLayout()
        self.bpm_color = QLineEdit(settings.bpm_color)
        self.bpm_color.textChanged.connect(self._emit)
        bpm_form.addRow("Accent color", self.bpm_color)
        self.bpm_radius = QSlider(Qt.Horizontal)
        self.bpm_radius.setRange(4, 24)
        self.bpm_radius.setValue(settings.bpm_radius)
        self.bpm_radius.valueChanged.connect(self._emit)
        bpm_form.addRow("Corner radius", self.bpm_radius)
        self.bpm_opacity = QSlider(Qt.Horizontal)
        self.bpm_opacity.setRange(50, 100)
        self.bpm_opacity.setValue(int(settings.bpm_opacity * 100))
        self.bpm_opacity.valueChanged.connect(self._emit)
        bpm_form.addRow("Opacity %", self.bpm_opacity)
        host_lay.addLayout(bpm_form)
        host_lay.addStretch(1)
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)

        self.btn_apply = QPushButton("Apply timer styles")
        self.btn_apply.setObjectName("PhasmoToolButton")
        self.btn_apply.clicked.connect(self._emit)
        outer.addWidget(self.btn_apply)

    def _emit(self) -> None:
        self.settings_changed.emit(self.collect())

    def collect(self) -> PhasmoSettings:
        self._settings.smudge = self.ed_smudge.value()
        self._settings.crucifix = self.ed_crucifix.value()
        self._settings.obambo = self.ed_obambo.value()
        self._settings.bpm_color = self.bpm_color.text().strip() or self._settings.bpm_color
        self._settings.bpm_radius = self.bpm_radius.value()
        self._settings.bpm_opacity = self.bpm_opacity.value() / 100.0
        return self._settings
