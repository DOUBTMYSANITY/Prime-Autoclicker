"""Custom difficulty builder — contract modifier reference and reward estimator."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass
class DifficultyState:
    evidence_count: int = 3
    starting_sanity: int = 100
    sanity_drain: float = 1.0
    ghost_speed: float = 1.0
    hunt_duration: float = 1.0
    player_speed: float = 1.0
    flashlight_drain: float = 1.0
    reward_multiplier: float = 1.0
    grace_period: bool = True
    fingerprint_chance: float = 1.0
    ghost_activity: float = 1.0


class DifficultyBuilderPage(QWidget):
    """Interactive custom difficulty panel (Zero-Network difficulty builder inspired)."""

    changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PhasmoDifficultyPage")
        self._state = DifficultyState()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        intro = QLabel(
            "Tune contract modifiers to match your lobby custom difficulty or weekly challenge. "
            "Evidence count syncs with the Ghost Type filter when you apply."
        )
        intro.setObjectName("PhasmoSupport")
        intro.setWordWrap(True)
        root.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        grid = QHBoxLayout(body)
        grid.setSpacing(14)

        self._player_form = self._section("Player")
        self._ghost_form = self._section("Ghost")
        self._contract_form = self._section("Contract")
        grid.addWidget(self._player_form[0], 1)
        grid.addWidget(self._ghost_form[0], 1)
        grid.addWidget(self._contract_form[0], 1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        summary = QFrame()
        summary.setObjectName("DifficultySummary")
        sum_lay = QVBoxLayout(summary)
        sum_lay.setContentsMargins(14, 12, 14, 12)
        self.lbl_reward = QLabel("Estimated reward multiplier: x1.00")
        self.lbl_reward.setObjectName("PhasmoSectionTitle")
        self.lbl_evidence = QLabel("")
        self.lbl_evidence.setObjectName("PhasmoSupport")
        self.lbl_evidence.setWordWrap(True)
        self.lbl_hunt = QLabel("")
        self.lbl_hunt.setObjectName("PhasmoSupport")
        self.lbl_hunt.setWordWrap(True)
        sum_lay.addWidget(self.lbl_reward)
        sum_lay.addWidget(self.lbl_evidence)
        sum_lay.addWidget(self.lbl_hunt)
        root.addWidget(summary)

        self._wire()
        self._refresh_summary()

    def _section(self, title: str) -> tuple[QFrame, QFormLayout]:
        frame = QFrame()
        frame.setObjectName("PhasmoGridWrap")
        lay = QVBoxLayout(frame)
        head = QLabel(title.upper())
        head.setObjectName("PhasmoSectionTitle")
        lay.addWidget(head)
        form = QFormLayout()
        form.setSpacing(10)
        lay.addLayout(form)
        return frame, form

    def _wire(self) -> None:
        pf = self._player_form[1]
        gf = self._ghost_form[1]
        cf = self._contract_form[1]

        self.cmb_evidence = QComboBox()
        for label, val in (
            ("3 evidence (Amateur / Intermediate)", 3),
            ("2 evidence (Nightmare)", 2),
            ("1 evidence (Insanity)", 1),
            ("0 evidence (Apocalypse)", 0),
        ):
            self.cmb_evidence.addItem(label, val)
        pf.addRow("Evidence slots", self.cmb_evidence)

        self.spin_start_sanity = QSpinBox()
        self.spin_start_sanity.setRange(0, 100)
        self.spin_start_sanity.setValue(100)
        self.spin_start_sanity.setSuffix("%")
        pf.addRow("Starting sanity", self.spin_start_sanity)

        self.spin_drain = QDoubleSpinBox()
        self.spin_drain.setRange(0.25, 3.0)
        self.spin_drain.setSingleStep(0.05)
        self.spin_drain.setValue(1.0)
        pf.addRow("Sanity drain", self.spin_drain)

        self.spin_player_speed = QDoubleSpinBox()
        self.spin_player_speed.setRange(0.5, 2.0)
        self.spin_player_speed.setSingleStep(0.05)
        self.spin_player_speed.setValue(1.0)
        pf.addRow("Player speed", self.spin_player_speed)

        self.spin_flash = QDoubleSpinBox()
        self.spin_flash.setRange(0.25, 3.0)
        self.spin_flash.setSingleStep(0.05)
        self.spin_flash.setValue(1.0)
        pf.addRow("Flashlight drain", self.spin_flash)

        self.spin_ghost_speed = QDoubleSpinBox()
        self.spin_ghost_speed.setRange(0.5, 2.0)
        self.spin_ghost_speed.setSingleStep(0.05)
        self.spin_ghost_speed.setValue(1.0)
        gf.addRow("Ghost speed", self.spin_ghost_speed)

        self.spin_hunt_dur = QDoubleSpinBox()
        self.spin_hunt_dur.setRange(0.25, 3.0)
        self.spin_hunt_dur.setSingleStep(0.05)
        self.spin_hunt_dur.setValue(1.0)
        gf.addRow("Hunt duration", self.spin_hunt_dur)

        self.spin_activity = QDoubleSpinBox()
        self.spin_activity.setRange(0.25, 3.0)
        self.spin_activity.setSingleStep(0.05)
        self.spin_activity.setValue(1.0)
        gf.addRow("Ghost activity", self.spin_activity)

        self.spin_fingerprint = QDoubleSpinBox()
        self.spin_fingerprint.setRange(0.0, 2.0)
        self.spin_fingerprint.setSingleStep(0.05)
        self.spin_fingerprint.setValue(1.0)
        gf.addRow("Fingerprint chance", self.spin_fingerprint)

        self.spin_reward = QDoubleSpinBox()
        self.spin_reward.setRange(0.1, 5.0)
        self.spin_reward.setSingleStep(0.05)
        self.spin_reward.setValue(1.0)
        cf.addRow("Reward multiplier", self.spin_reward)

        for widget in (
            self.cmb_evidence,
            self.spin_start_sanity,
            self.spin_drain,
            self.spin_player_speed,
            self.spin_flash,
            self.spin_ghost_speed,
            self.spin_hunt_dur,
            self.spin_activity,
            self.spin_fingerprint,
            self.spin_reward,
        ):
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._on_change)
            else:
                widget.valueChanged.connect(self._on_change)

    def _on_change(self) -> None:
        self._state = DifficultyState(
            evidence_count=int(self.cmb_evidence.currentData()),
            starting_sanity=int(self.spin_start_sanity.value()),
            sanity_drain=float(self.spin_drain.value()),
            ghost_speed=float(self.spin_ghost_speed.value()),
            hunt_duration=float(self.spin_hunt_dur.value()),
            player_speed=float(self.spin_player_speed.value()),
            flashlight_drain=float(self.spin_flash.value()),
            reward_multiplier=float(self.spin_reward.value()),
            fingerprint_chance=float(self.spin_fingerprint.value()),
            ghost_activity=float(self.spin_activity.value()),
        )
        self._refresh_summary()
        self.changed.emit(self._state)

    def _refresh_summary(self) -> None:
        s = self._state
        hidden = max(0, 3 - s.evidence_count)
        est = s.reward_multiplier
        if s.evidence_count <= 1:
            est *= 1.15
        if s.ghost_speed > 1.05:
            est *= 1.05
        if s.sanity_drain > 1.05:
            est *= 1.05
        self.lbl_reward.setText(f"Estimated reward multiplier: x{est:.2f}")
        self.lbl_evidence.setText(
            f"Journal shows {s.evidence_count} evidence type(s); "
            f"{hidden} forced hidden per ghost on this contract."
        )
        self.lbl_hunt.setText(
            f"Hunt length ~{s.hunt_duration:.0%} of default · "
            f"Ghost speed ~{s.ghost_speed:.0%} · "
            f"Activity ~{s.ghost_activity:.0%} · "
            f"Starting sanity {s.starting_sanity}%"
        )

    def set_evidence_count(self, count: int) -> None:
        for i in range(self.cmb_evidence.count()):
            if self.cmb_evidence.itemData(i) == count:
                self.cmb_evidence.blockSignals(True)
                self.cmb_evidence.setCurrentIndex(i)
                self.cmb_evidence.blockSignals(False)
                break
        self._on_change()

    def evidence_count(self) -> int:
        return int(self.cmb_evidence.currentData())
