"""Always-on-top Phasmophobia timer overlays (smudge, crucifix, obambo)."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from PyQt5.QtCore import QObject, QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.Phasmo.phasmo_settings import TimerStyleConfig

try:
    from pynput import keyboard
except ImportError:
    keyboard = None  # type: ignore

NUMPAD_VK = {
    97: "smudge",
    98: "crucifix",
    99: "obambo",
    100: "gamma",
    101: "brightness",
}
VK_BPM_TAP = 0x46
VK_BPM_RESET = 0x52


def _format_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def obambo_state(elapsed_seconds: float) -> str:
    if elapsed_seconds < 60:
        return "Weakened"
    phase_index = int((elapsed_seconds - 60) // 120)
    return "Enraged" if phase_index % 2 == 0 else "Weakened"


class TimerOverlay(QWidget):
    def __init__(self, config: TimerStyleConfig, *, show_status: bool = False, parent=None):
        flags = Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        super().__init__(parent, flags)
        self._config = config
        self._running = False
        self._hud_enabled = False
        self._elapsed_ms = 0
        self._drag_origin: QPoint | None = None
        self._tick = QTimer(self)
        self._tick.setInterval(100)
        self._tick.timeout.connect(self._on_tick)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        self.lbl_title = QLabel(config.title.upper())
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_time = QLabel("00:00")
        self.lbl_time.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_time)

        self.lbl_status: QLabel | None = None
        if show_status:
            self.lbl_status = QLabel("Weakened")
            self.lbl_status.setAlignment(Qt.AlignCenter)
            lay.addWidget(self.lbl_status)

        self.apply_config(config)
        self.hide()

    def apply_config(self, config: TimerStyleConfig) -> None:
        self._config = config
        self.lbl_title.setText(config.title.upper())
        self.setFixedWidth(config.width)
        self.setMinimumHeight(78 if self.lbl_status else 62)
        font = QFont("Consolas", config.font_pt, QFont.Bold)
        self.lbl_time.setFont(font)
        alpha = int(max(0.0, min(1.0, config.opacity)) * 255)
        accent = config.color
        self.setStyleSheet(
            f"""
            QWidget {{
                background: rgba(10, 10, 10, {alpha});
                border: {config.border}px solid {accent};
                border-radius: {config.radius}px;
            }}
            QLabel {{
                color: {accent};
                background: transparent;
                border: none;
                font-weight: 800;
            }}
            """
        )
        self.lbl_title.setStyleSheet(
            f"color: {accent}; font-size: 10px; font-weight: 900; letter-spacing: 0.5px;"
        )
        if self.lbl_status is not None:
            self.lbl_status.setStyleSheet(
                f"color: {accent}; font-size: 11px; font-weight: 700;"
            )

    def set_hud_enabled(self, enabled: bool) -> None:
        self._hud_enabled = enabled
        if enabled:
            self.show()
            self.raise_()
            return
        self._running = False
        self._tick.stop()
        self.hide()

    def toggle(self) -> None:
        if not self._hud_enabled:
            return
        if self._running:
            self.pause()
        else:
            self.start()

    def start(self) -> None:
        if not self._hud_enabled:
            return
        self._running = True
        if self._elapsed_ms == 0:
            self._refresh_display()
        self.show()
        self.raise_()
        self._tick.start()

    def pause(self) -> None:
        self._running = False
        self._tick.stop()
        self._elapsed_ms = 0
        self._refresh_display()

    def stop(self) -> None:
        self.pause()

    def is_running(self) -> bool:
        return self._running

    def elapsed_seconds(self) -> float:
        return self._elapsed_ms / 1000.0

    def _on_tick(self) -> None:
        self._elapsed_ms += self._tick.interval()
        self._refresh_display()

    def _refresh_display(self) -> None:
        self.lbl_time.setText(_format_elapsed(self.elapsed_seconds()))
        self.refresh_status()

    def refresh_status(self) -> None:
        return

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


class ObamboTimerOverlay(TimerOverlay):
    def __init__(self, config: TimerStyleConfig, parent=None):
        super().__init__(config, show_status=True, parent=parent)

    def refresh_status(self) -> None:
        if self.lbl_status is None:
            return
        self.lbl_status.setText(obambo_state(self.elapsed_seconds()))


class PhasmoTimerOverlayManager(QObject):
    _hotkey_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        from plugins.Phasmo.phasmo_settings import PhasmoSettings

        defaults = PhasmoSettings()
        self.smudge = TimerOverlay(defaults.smudge)
        self.crucifix = TimerOverlay(defaults.crucifix)
        self.obambo = ObamboTimerOverlay(defaults.obambo)
        self._listener = None
        self._listener_thread: threading.Thread | None = None

    def apply_styles(self, settings) -> None:
        self.smudge.apply_config(settings.smudge)
        self.crucifix.apply_config(settings.crucifix)
        self.obambo.apply_config(settings.obambo)
        self.position_overlays()

    def apply_visibility(self, settings) -> None:
        self.smudge.set_hud_enabled(settings.overlay_smudge)
        self.crucifix.set_hud_enabled(settings.overlay_crucifix)
        self.obambo.set_hud_enabled(settings.overlay_obambo)

    def position_overlays(self) -> None:
        app = QApplication.instance()
        screen = app.primaryScreen().availableGeometry() if app else None
        if screen is None:
            return
        x = screen.left() + 24
        y = screen.top() + 24
        self.smudge.move(x, y)
        gap = 8
        self.crucifix.move(x, y + self.smudge.height() + gap)
        self.obambo.move(x + self.smudge.width() + gap, y)

    def toggle_smudge(self) -> None:
        self.smudge.toggle()

    def toggle_crucifix(self) -> None:
        self.crucifix.toggle()

    def toggle_obambo(self) -> None:
        self.obambo.toggle()

    def start_global_hotkeys(self) -> None:
        if keyboard is None or self._listener is not None:
            return

        def _run_listener() -> None:
            def on_press(key):
                vk = getattr(key, "vk", None)
                if vk in NUMPAD_VK:
                    self._hotkey_signal.emit(NUMPAD_VK[vk])
                elif vk == VK_BPM_TAP:
                    self._hotkey_signal.emit("bpm_tap")
                elif vk == VK_BPM_RESET:
                    self._hotkey_signal.emit("bpm_reset")

            listener = keyboard.Listener(on_press=on_press)
            self._listener = listener
            listener.run()

        self._listener_thread = threading.Thread(target=_run_listener, daemon=True)
        self._listener_thread.start()

    def stop_global_hotkeys(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._listener_thread = None

    def shutdown(self) -> None:
        self.stop_global_hotkeys()
        for overlay in (self.smudge, self.crucifix, self.obambo):
            overlay.set_hud_enabled(False)
            overlay.close()
