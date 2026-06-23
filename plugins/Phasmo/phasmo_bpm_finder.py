"""Tap-to-BPM ghost footstep speed finder (zero-network style)."""
from __future__ import annotations

import time
from dataclasses import dataclass

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from plugins.Phasmo.phasmo_ghost_speeds import format_speed_matches

# Community formula: apparent m/s from taps = (BPM * step_m / 60).
# Lobby ghost-speed % scales footstep rate (150% = 1.5x faster taps). We divide
# by that factor so tier tables (defined at 100%) still match.
STEP_METERS = 0.85
SPEED_MULTIPLIERS = (50, 75, 100, 125, 150)


def bpm_to_mps(bpm: int, multiplier_pct: float = 100.0, offset_pct: float = 0.0) -> float:
    """Convert tapped BPM to normalized m/s for ghost tier matching at 100% baseline."""
    if bpm <= 0 or multiplier_pct <= 0:
        return 0.0
    apparent = (bpm * STEP_METERS) / 60.0
    normalized = apparent / (multiplier_pct / 100.0)
    return normalized * (1.0 + offset_pct / 100.0)


@dataclass
class BpmTapState:
    bpm: int | None = None
    tap_count: int = 0


class BpmTapEngine:
    """Average recent tap intervals into a BPM reading."""

    RESET_GAP_SEC = 2.5
    MAX_INTERVALS = 12

    def __init__(self) -> None:
        self._times: list[float] = []

    def reset(self) -> None:
        self._times.clear()

    def tap(self, now: float | None = None) -> BpmTapState:
        now = time.monotonic() if now is None else now
        if self._times and now - self._times[-1] > self.RESET_GAP_SEC:
            self._times = []
        self._times.append(now)
        if len(self._times) < 2:
            return BpmTapState(bpm=None, tap_count=len(self._times))
        intervals = [
            self._times[i] - self._times[i - 1] for i in range(1, len(self._times))
        ]
        intervals = intervals[-self.MAX_INTERVALS :]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval <= 0:
            return BpmTapState(bpm=None, tap_count=len(self._times))
        bpm = max(1, round(60.0 / avg_interval))
        return BpmTapState(bpm=bpm, tap_count=len(self._times))


class BpmFinderOverlay(QWidget):
    """Always-on-top BPM / m/s readout for in-game footstep tapping."""

    multiplier_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        flags = Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        super().__init__(parent, flags)
        self._drag_origin: QPoint | None = None
        self._multiplier_pct = 100
        self._offset_pct = 0.0
        self._hud_enabled = False
        self._accent = "#3b82f6"
        self._radius = 10
        self._opacity = 0.92

        self.setFixedWidth(240)
        self.setMinimumHeight(160)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        title = QLabel("BPM FINDER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #60a5fa; font-size: 10px; font-weight: 900; letter-spacing: 1px;")
        lay.addWidget(title)

        self.lbl_bpm = QLabel("0")
        self.lbl_bpm.setAlignment(Qt.AlignCenter)
        bpm_font = QFont("Consolas", 28, QFont.Bold)
        self.lbl_bpm.setFont(bpm_font)
        lay.addWidget(self.lbl_bpm)

        bpm_caption = QLabel("bpm")
        bpm_caption.setAlignment(Qt.AlignCenter)
        bpm_caption.setStyleSheet("color: #9ca3af; font-size: 10px; font-weight: 700;")
        lay.addWidget(bpm_caption)

        self.lbl_speed = QLabel("0.00 m/s")
        self.lbl_speed.setAlignment(Qt.AlignCenter)
        self.lbl_speed.setFont(QFont("Consolas", 16, QFont.Bold))
        lay.addWidget(self.lbl_speed)

        mult_row = QHBoxLayout()
        mult_row.setSpacing(4)
        self._mult_buttons: dict[int, QPushButton] = {}
        for pct in SPEED_MULTIPLIERS:
            btn = QPushButton(f"{pct}%")
            btn.setCheckable(True)
            btn.setFixedHeight(24)
            btn.clicked.connect(lambda _checked, p=pct: self._set_multiplier(p))
            self._mult_buttons[pct] = btn
            mult_row.addWidget(btn)
        lay.addLayout(mult_row)
        self._set_multiplier(100)

        offset_row = QHBoxLayout()
        offset_row.setSpacing(4)
        self.btn_offset_down = QPushButton("-")
        self.btn_offset_up = QPushButton("+")
        self.lbl_offset = QLabel("0.0%")
        self.lbl_offset.setAlignment(Qt.AlignCenter)
        for btn in (self.btn_offset_down, self.btn_offset_up):
            btn.setFixedSize(28, 24)
        self.btn_offset_down.clicked.connect(lambda: self._adjust_offset(-0.1))
        self.btn_offset_up.clicked.connect(lambda: self._adjust_offset(0.1))
        offset_row.addWidget(self.btn_offset_down)
        offset_row.addWidget(self.lbl_offset, 1)
        offset_row.addWidget(self.btn_offset_up)
        lay.addLayout(offset_row)

        self.lbl_matches = QLabel("Tap F on each footstep")
        self.lbl_matches.setWordWrap(True)
        self.lbl_matches.setAlignment(Qt.AlignCenter)
        self.lbl_matches.setStyleSheet("color: #d1d5db; font-size: 10px;")
        lay.addWidget(self.lbl_matches)

        hint = QLabel("F = tap · R = reset · % = lobby ghost speed (150% → ÷1.5 for match)")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #6b7280; font-size: 9px;")
        lay.addWidget(hint)

        self._apply_style()

    def apply_style(self, color: str, radius: int, opacity: float) -> None:
        self._accent = color
        self._radius = radius
        self._opacity = opacity
        self._apply_style()

    def set_hud_enabled(self, enabled: bool) -> None:
        self._hud_enabled = enabled
        if enabled:
            self.show()
            self.raise_()
        else:
            self.hide()

    def _apply_style(self) -> None:
        alpha = int(max(0.0, min(1.0, self._opacity)) * 255)
        accent = self._accent
        radius = self._radius
        self.setStyleSheet(
            f"""
            QWidget {{
                background: rgba(10, 10, 10, {alpha});
                border: 2px solid {accent};
                border-radius: {radius}px;
            }}
            QPushButton {{
                background: #1f2937;
                color: #e5e7eb;
                border: 1px solid #374151;
                border-radius: 4px;
                font-size: 9px;
                font-weight: 700;
            }}
            QPushButton:checked {{
                background: {accent};
                border-color: {accent};
                color: #ffffff;
            }}
            QPushButton:hover {{
                border-color: {accent};
            }}
            """
        )
        self.lbl_bpm.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        self.lbl_speed.setStyleSheet(f"color: {accent}; background: transparent; border: none;")

    def _set_multiplier(self, pct: int) -> None:
        self._multiplier_pct = pct
        for value, btn in self._mult_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(value == pct)
            btn.blockSignals(False)
        self.multiplier_changed.emit(pct)
        self._refresh_speed_label(self._current_bpm())

    def _adjust_offset(self, delta: float) -> None:
        self._offset_pct = round(self._offset_pct + delta, 1)
        self.lbl_offset.setText(f"{self._offset_pct:+.1f}%")
        self._refresh_speed_label(self._current_bpm())

    def _current_bpm(self) -> int | None:
        text = self.lbl_bpm.text().strip()
        if not text or text == "0":
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def update_reading(self, state: BpmTapState) -> None:
        if state.bpm is None:
            self.lbl_bpm.setText(str(state.tap_count) if state.tap_count else "0")
            self.lbl_speed.setText("— m/s")
            self.lbl_matches.setText("Keep tapping F on footsteps…")
            return
        self.lbl_bpm.setText(str(state.bpm))
        speed = bpm_to_mps(state.bpm, self._multiplier_pct, self._offset_pct)
        self._refresh_speed_label(state.bpm, speed)
        label, _names = format_speed_matches(speed)
        self.lbl_matches.setText(label)

    def _refresh_speed_label(self, bpm: int | None, speed: float | None = None) -> None:
        if bpm is None:
            self.lbl_speed.setText("— m/s")
            return
        if speed is None:
            speed = bpm_to_mps(bpm, self._multiplier_pct, self._offset_pct)
        self.lbl_speed.setText(f"{speed:.2f} m/s")

    def reset_reading(self) -> None:
        self.lbl_bpm.setText("0")
        self.lbl_speed.setText("0.00 m/s")
        self.lbl_matches.setText("Tap F on each footstep")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_origin = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PhasmoBpmFinderManager:
    """Tap engine + overlay for ghost footstep BPM."""

    def __init__(self) -> None:
        self.overlay = BpmFinderOverlay()
        self._engine = BpmTapEngine()

    def position_overlay(self) -> None:
        app = QApplication.instance()
        screen = app.primaryScreen().availableGeometry() if app else None
        if screen is None:
            return
        x = screen.right() - self.overlay.width() - 24
        y = screen.top() + 24
        self.overlay.move(x, y)

    def apply_style(self, settings) -> None:
        self.overlay.apply_style(settings.bpm_color, settings.bpm_radius, settings.bpm_opacity)

    def set_hud_enabled(self, enabled: bool) -> None:
        self.overlay.set_hud_enabled(enabled)
        if enabled:
            self.position_overlay()

    def show(self) -> None:
        if self.overlay._hud_enabled:
            self.position_overlay()
            self.overlay.show()
            self.overlay.raise_()

    def hide(self) -> None:
        if not self.overlay._hud_enabled:
            self.overlay.hide()

    def tap(self) -> None:
        state = self._engine.tap()
        self.overlay.update_reading(state)

    def reset(self) -> None:
        self._engine.reset()
        self.overlay.reset_reading()

    def shutdown(self) -> None:
        self.reset()
        self.overlay.close()
