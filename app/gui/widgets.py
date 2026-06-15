from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QPointF, QRect, QRectF, pyqtSignal, pyqtProperty
from PyQt5.QtGui import QPainter, QLinearGradient, QColor, QPen, QPainterPath, QBrush
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QSpinBox, QGraphicsDropShadowEffect, QLineEdit, QGridLayout,
    QStackedWidget, QSizePolicy,
)

import math
import collections
import re
import os
import json


class AdaptiveStack(QStackedWidget):
    """QStackedWidget that constrains its height to the current page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.currentChanged.connect(self._on_page_changed)

    def addWidget(self, w: QWidget) -> int:
        idx = super().addWidget(w)
        if idx == 0:
            QTimer.singleShot(0, lambda: self._on_page_changed(0))
        return idx

    def _on_page_changed(self, _idx: int) -> None:
        w = self.widget(_idx)
        if w is not None:
            hint = w.sizeHint().height()
            # Let pages expand to fill available space instead of snapping
            # to their minimum size, which caused off-center layouts.
            self.setMinimumHeight(max(hint, 360))
            self.setMaximumHeight(16_777_215)  # QWIDGETSIZE_MAX – no ceiling


class ToastNotification(QFrame):
    """Slide-in toast that shows an achievement unlock message."""

    _active_toasts: list[ToastNotification] = []  # class-level stack
    _stacked_toasts: dict[tuple[str, str], ToastNotification] = {}

    @staticmethod
    def _clamp_channel(value: float, lo: int = 0, hi: int = 255) -> int:
        return max(lo, min(hi, int(round(value))))

    @staticmethod
    def _parse_css_color(spec: str | None, fallback: QColor) -> QColor:
        """Parse hex/rgb/rgba CSS colour strings, including float alpha."""
        if not spec:
            return QColor(fallback)

        parsed = QColor(spec)
        if parsed.isValid():
            return parsed

        txt = str(spec).strip()
        m = re.match(r"^(rgba?|RGBA?)\(([^\)]*)\)$", txt)
        if not m:
            return QColor(fallback)

        parts = [p.strip() for p in m.group(2).split(",")]
        if len(parts) not in (3, 4):
            return QColor(fallback)

        try:
            r = ToastNotification._clamp_channel(float(parts[0]))
            g = ToastNotification._clamp_channel(float(parts[1]))
            b = ToastNotification._clamp_channel(float(parts[2]))
            a = 255
            if len(parts) == 4:
                alpha_raw = float(parts[3])
                if alpha_raw <= 1.0:
                    a = ToastNotification._clamp_channel(alpha_raw * 255.0)
                else:
                    a = ToastNotification._clamp_channel(alpha_raw)
            return QColor(r, g, b, a)
        except Exception:
            return QColor(fallback)

    @staticmethod
    def _blend(c1: QColor, c2: QColor, t: float) -> QColor:
        t = max(0.0, min(1.0, t))
        return QColor(
            ToastNotification._clamp_channel(c1.red() + (c2.red() - c1.red()) * t),
            ToastNotification._clamp_channel(c1.green() + (c2.green() - c1.green()) * t),
            ToastNotification._clamp_channel(c1.blue() + (c2.blue() - c1.blue()) * t),
            ToastNotification._clamp_channel(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
        )

    def __init__(self, text: str, bg_color: str, border_color: str, text_color: str = "#E9EDFF", icon: str = "\u2139", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumHeight(58)
        self._base_text = text
        self._stack_count = 1
        self._stack_key: tuple[str, str] | None = None
        self._radius = 15

        # Keep toast colours tied to current theme palette with robust parsing.
        solid_bg = bg_color or "rgba(31,42,68,0.96)"
        solid_border = border_color or "rgba(91,115,232,1.0)"
        self._bg = self._parse_css_color(solid_bg, QColor(31, 42, 68, 244))
        self._border = self._parse_css_color(solid_border, QColor(91, 115, 232, 255))
        self._text = self._parse_css_color(text_color, QColor("#E9EDFF"))

        # Keep the palette coherent: preserve theme background character,
        # then lightly tint with border/accent instead of overmixing.
        self._bg_top = self._blend(self._bg, QColor(255, 255, 255, self._bg.alpha()), 0.09)
        self._bg_mid = self._blend(self._bg, self._border, 0.08)
        self._bg_bottom = self._blend(self._bg, QColor(0, 0, 0, self._bg.alpha()), 0.14)
        self._accent = self._blend(self._border, QColor(255, 255, 255, self._border.alpha()), 0.12)

        border_soft = QColor(self._border)
        border_soft.setAlpha(max(110, min(180, self._border.alpha())))
        self._border_soft = border_soft

        icon_bg = self._blend(self._bg_top, self._border, 0.22)
        icon_bg.setAlpha(max(80, min(130, self._bg.alpha() - 90)))
        icon_border = QColor(self._border_soft)
        icon_border.setAlpha(max(140, self._border_soft.alpha()))

        self.setStyleSheet(
            f"QLabel {{ color: rgba({self._text.red()},{self._text.green()},{self._text.blue()},{self._text.alpha()}); background: transparent; }}"
            f"QFrame#ToastIconBadge {{ background: rgba({icon_bg.red()},{icon_bg.green()},{icon_bg.blue()},{icon_bg.alpha()});"
            f" border: 1px solid rgba({icon_border.red()},{icon_border.green()},{icon_border.blue()},{icon_border.alpha()}); border-radius: 11px; }}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(12)

        self.icon_badge = QFrame(self)
        self.icon_badge.setObjectName("ToastIconBadge")
        self.icon_badge.setFixedSize(32, 32)
        icon_lay = QHBoxLayout(self.icon_badge)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        icon_lay.setSpacing(0)

        self.icon = QLabel(icon, self.icon_badge)
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setStyleSheet("font-size: 16px; font-weight: 800;")
        icon_lay.addWidget(self.icon)

        self.msg = QLabel(text)
        self.msg.setStyleSheet("font-size: 13px; font-weight: 700; font-family: Segoe UI Variable Text, Segoe UI, Arial;")
        self.msg.setWordWrap(True)

        lay.addWidget(self.icon_badge)
        lay.addWidget(self.msg, 1)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._dismiss)

        self.adjustSize()
        self.setMinimumWidth(320)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self._radius, self._radius)

        # Base premium gradient panel.
        panel = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        panel.setColorAt(0.0, self._bg_top)
        panel.setColorAt(0.52, self._bg_mid)
        panel.setColorAt(1.0, self._bg_bottom)
        p.fillPath(path, panel)

        # Soft top sheen for a glass-like finish.
        sheen = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top() + rect.height() * 0.55)
        sheen_col = QColor(255, 255, 255, 18)
        sheen.setColorAt(0.0, sheen_col)
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(path, sheen)

        # Accent rail tied to current theme accent/border.
        rail = QRectF(rect.left() + 8, rect.top() + 9, 3, max(12.0, rect.height() - 18.0))
        rail_grad = QLinearGradient(rail.left(), rail.top(), rail.left(), rail.bottom())
        rail_top = QColor(self._accent)
        rail_top.setAlpha(190)
        rail_bot = QColor(self._border_soft)
        rail_bot.setAlpha(120)
        rail_grad.setColorAt(0.0, rail_top)
        rail_grad.setColorAt(1.0, rail_bot)
        rail_path = QPainterPath()
        rail_path.addRoundedRect(rail, 2.0, 2.0)
        p.fillPath(rail_path, rail_grad)

        border_pen = QPen(self._border_soft, 1.2)
        p.setPen(border_pen)
        p.drawPath(path)
        super().paintEvent(event)

    def show_toast(self, duration_ms: int = 3500, position: str = "top-right"):
        """Animate in from the right, auto-dismiss after *duration_ms*."""
        # Respect global disable setting to suppress toasts.
        try:
            settings_path = os.path.join(os.path.expanduser("~"), ".mtautoclicker_settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, "r") as sf:
                    data = json.load(sf)
                    if data.get("disable_toasts", False):
                        # Do not display the toast when disabled.
                        self.deleteLater()
                        return
        except Exception:
            # If reading settings fails, fall back to showing the toast.
            pass
        norm_pos = (position or "top-right").lower()
        stack_key = (self._base_text, norm_pos)
        existing = ToastNotification._stacked_toasts.get(stack_key)
        if existing is not None and existing is not self and existing.isVisible():
            existing.bump(duration_ms)
            self.deleteLater()
            return

        self._stack_key = stack_key
        ToastNotification._stacked_toasts[stack_key] = self
        ToastNotification._active_toasts.append(self)

        # Position: top-right (default) or bottom-right of parent/screen.
        top_mode = norm_pos == "top-right"
        if self.parent():
            pr = self.parent().geometry()
            slot = len(ToastNotification._active_toasts) - 1
            if top_mode:
                target_y = pr.top() + 56 + slot * 62
            else:
                target_y = pr.bottom() - 70 - slot * 62
            target_x = pr.right() - self.width() - 24
            start_x = pr.right() + 10
        else:
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            slot = len(ToastNotification._active_toasts) - 1
            if top_mode:
                target_y = screen.top() + 36 + slot * 62
            else:
                target_y = screen.bottom() - 70 - slot * 62
            target_x = screen.right() - self.width() - 24
            start_x = screen.right() + 10

        self.move(start_x, target_y)
        self.show()
        self.raise_()

        # Slide-in animation
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(350)
        self._anim.setStartValue(QPoint(start_x, target_y))
        self._anim.setEndValue(QPoint(target_x, target_y))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        self._dismiss_timer.start(duration_ms)

    def bump(self, duration_ms: int = 3500):
        self._stack_count += 1
        self._update_message_text()
        self._dismiss_timer.start(duration_ms)

    def _update_message_text(self):
        if self._stack_count <= 1:
            self.msg.setText(self._base_text)
        else:
            self.msg.setText(f"{self._base_text} ({self._stack_count}x)")

    def _dismiss(self):
        if self._stack_key is not None:
            mapped = ToastNotification._stacked_toasts.get(self._stack_key)
            if mapped is self:
                del ToastNotification._stacked_toasts[self._stack_key]
            self._stack_key = None
        if self in ToastNotification._active_toasts:
            ToastNotification._active_toasts.remove(self)
        # Slide-out
        self._anim_out = QPropertyAnimation(self, b"pos")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(self.pos())
        end = QPoint(self.pos().x() + self.width() + 40, self.pos().y())
        self._anim_out.setEndValue(end)
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.finished.connect(self.deleteLater)
        self._anim_out.start()


def add_shadow(w: QWidget, blur: int = 22, y: int = 8, alpha: int = 120):
    sh = QGraphicsDropShadowEffect(w)
    sh.setBlurRadius(blur)
    sh.setOffset(0, y)
    sh.setColor(QColor(0, 0, 0, alpha))
    w.setGraphicsEffect(sh)


class GradientBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors = ["#0B1630", "#0B1B3A", "#7A2CFF"]

    def set_gradient(self, colors: list[str]):
        """Set 3-stop gradient colours and repaint."""
        self._colors = colors[:3] if len(colors) >= 3 else colors + ["#000000"] * (3 - len(colors))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor(self._colors[0]))
        g.setColorAt(0.55, QColor(self._colors[1]))
        g.setColorAt(1.0, QColor(self._colors[2]))
        p.fillRect(self.rect(), g)


class Card(QFrame):
    def __init__(self, radius: int = 22):
        super().__init__()
        self.setObjectName("Card")
        self.setProperty("radius", radius)
        self.setFrameShape(QFrame.NoFrame)


class _SecretLineEdit(QLineEdit):
    """QLineEdit that tracks keypresses for a secret code."""

    def __init__(self, parent_spin, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spin = parent_spin

    def keyPressEvent(self, event):
        # Enter/Return is handled by the global _EnterDefocusFilter in GUIAuto.
        # Only track the secret code here.
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Let the global filter handle focus; just pass through
            super().keyPressEvent(event)
            return
        txt = event.text()
        if txt and self._spin._SECRET:
            buf = self._spin._key_buf
            buf.append(txt)
            secret = self._spin._SECRET
            if len(buf) > len(secret):
                self._spin._key_buf = buf[-len(secret):]
                buf = self._spin._key_buf
            if "".join(buf) == secret:
                buf.clear()
                self._spin.secret_code_entered.emit()
        super().keyPressEvent(event)


class FocusClearSpinBox(QSpinBox):
    """QSpinBox that clears focus when Enter/Return is pressed."""
    from PyQt5.QtCore import pyqtSignal as _sig
    secret_code_entered = _sig()

    @staticmethod
    def admin_easter_egg_code() -> str:
        return (os.getenv("MTA_ADMIN_EASTER_EGG") or "").strip()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._key_buf: list[str] = []
        self._SECRET = self.admin_easter_egg_code()
        self.setLineEdit(_SecretLineEdit(self))


class PillButton(QPushButton):
    def __init__(self, text: str, icon_text: str = ""):
        super().__init__("")
        self.setObjectName("PillButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self._icon = QLabel(icon_text, self)
        self._icon.setObjectName("PillIcon")
        self._icon.setFixedSize(28, 28)
        self._icon.setAlignment(Qt.AlignCenter)
        self._text = QLabel(text, self)
        self._text.setObjectName("PillText")
        self._text.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 14, 0)
        lay.setSpacing(10)
        lay.addWidget(self._icon)
        lay.addWidget(self._text, 1)


# ═══════════════════════════════════════════════════════
#  XP Progress Bar
# ═══════════════════════════════════════════════════════
class XPBar(QWidget):
    """Animated XP progress bar with level badge."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self._progress = 0.0   # 0..1
        self._level = 1
        self._xp_text = ""
        self._track_color = QColor(255, 255, 255, 15)
        self._fill_start = QColor("#5b73e8")
        self._fill_end = QColor("#8b5cf6")
        self._badge_bg = QColor("#1a1a2e")
        self._badge_border = QColor("#8b5cf6")
        self._badge_text = QColor("#e0e0e0")
        self._xp_text_color = QColor(255, 255, 255, 180)
        self._anim = QPropertyAnimation(self, b"prog")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    # Qt property for animation
    def _get_prog(self):
        return self._progress

    def _set_prog(self, v):
        self._progress = v
        self.update()

    prog = pyqtProperty(float, _get_prog, _set_prog)

    def set_xp(self, current_in_level: int, needed: int, level: int):
        self._level = level
        target = current_in_level / max(needed, 1)
        self._xp_text = f"{current_in_level:,} / {needed:,} XP"
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def set_theme(self, palette: dict):
        """Apply theme colours to XP visuals."""
        self._track_color = QColor(palette.get("badge_bg", "rgba(255,255,255,0.10)"))
        if not self._track_color.isValid():
            self._track_color = QColor(255, 255, 255, 20)

        self._fill_start = QColor(palette.get("accent_solid", "#5b73e8"))
        if not self._fill_start.isValid():
            self._fill_start = QColor("#5b73e8")

        self._fill_end = QColor(palette.get("slider_handle", palette.get("accent_solid", "#8b5cf6")))
        if not self._fill_end.isValid():
            self._fill_end = QColor("#8b5cf6")

        self._badge_bg = QColor(palette.get("sidebar", "#1a1a2e"))
        if not self._badge_bg.isValid():
            self._badge_bg = QColor("#1a1a2e")

        self._badge_border = QColor(palette.get("pill_active_border", "#8b5cf6"))
        if not self._badge_border.isValid():
            self._badge_border = QColor("#8b5cf6")

        self._badge_text = QColor(palette.get("text_primary", "#e0e0e0"))
        if not self._badge_text.isValid():
            self._badge_text = QColor("#e0e0e0")

        self._xp_text_color = QColor(palette.get("text_secondary", "rgba(255,255,255,0.7)"))
        if not self._xp_text_color.isValid():
            self._xp_text_color = QColor(255, 255, 255, 180)

        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        radius = h / 2

        # Background track
        p.setPen(Qt.NoPen)
        p.setBrush(self._track_color)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Filled portion – gradient
        fill_w = max(h, w * self._progress)  # at least circle-sized
        grad = QLinearGradient(0, 0, fill_w, 0)
        grad.setColorAt(0.0, self._fill_start)
        grad.setColorAt(1.0, self._fill_end)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(0, 0, fill_w, h), radius, radius)

        # Level badge
        badge_r = h - 4
        p.setBrush(self._badge_bg)
        p.setPen(QPen(self._badge_border, 2))
        p.drawEllipse(QRectF(4, 2, badge_r, badge_r))
        p.setPen(self._badge_text)
        font = p.font()
        font.setPixelSize(int(badge_r * 0.52))
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(4, 2, badge_r, badge_r), Qt.AlignCenter, str(self._level))

        # XP text – right-aligned
        p.setPen(self._xp_text_color)
        font.setPixelSize(11)
        font.setBold(False)
        p.setFont(font)
        p.drawText(QRectF(0, 0, w - 10, h), Qt.AlignVCenter | Qt.AlignRight, self._xp_text)
        p.end()


# ═══════════════════════════════════════════════════════
#  CPS Sparkline  (live animated graph)
# ═══════════════════════════════════════════════════════
class CPSSparkline(QWidget):
    """Tiny live CPS line chart that auto-updates."""

    def __init__(self, max_points: int = 60, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._max = max_points
        self._data: list[float] = []
        self._click_count = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._click_count = 0
        self._data.clear()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        # push a final zero
        self._data.append(0)
        self.update()

    def record_click(self):
        self._click_count += 1

    @property
    def current_cps(self) -> float:
        if self._data:
            return self._data[-1]
        return 0.0

    def _tick(self):
        self._data.append(self._click_count)
        self._click_count = 0
        # Keep a long but bounded history (24h at 1 sample/sec)
        if len(self._data) > 86_400:
            self._data = self._data[-86_400:]
        self.update()

    def paintEvent(self, _event):
        if len(self._data) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad = 4
        area_h = h - 2 * pad

        # Adaptive downsample so full session history fits current width.
        max_points = max(2, w)
        if len(self._data) > max_points:
            step = len(self._data) / float(max_points)
            sampled = [self._data[int(i * step)] for i in range(max_points)]
            sampled[-1] = self._data[-1]
        else:
            sampled = self._data

        peak = max(max(sampled), 1)
        n = len(sampled)
        step = w / max(n - 1, 1)

        path = QPainterPath()
        for i, v in enumerate(sampled):
            x = i * step
            y = pad + area_h * (1.0 - v / peak)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        # Gradient fill under the line
        fill = QPainterPath(path)
        fill.lineTo(w, h)
        fill.lineTo(0, h)
        fill.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(91, 115, 232, 60))
        grad.setColorAt(1.0, QColor(91, 115, 232, 5))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(fill)

        # Line
        pen = QPen(QColor("#5b73e8"), 2)
        pen.setCosmetic(True)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # CPS text
        p.setPen(QColor(255, 255, 255, 180))
        font = p.font()
        font.setPixelSize(11)
        font.setBold(True)
        p.setFont(font)
        cps_val = self._data[-1] if self._data else 0
        p.drawText(QRectF(0, 0, w - 6, h), Qt.AlignTop | Qt.AlignRight, f"{cps_val:.0f} CPS")
        p.end()


# ═══════════════════════════════════════════════════════
#  Compact Overlay
# ═══════════════════════════════════════════════════════
class CompactOverlay(QWidget):
    """Tiny always-on-top floating widget showing CPS + start/stop."""

    toggle_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(220, 72)
        self._drag_pos = None
        self._click_count = 0
        self._elapsed_label = "00:00"
        self._hotkey_label = "-"

        bg = QFrame(self)
        bg.setGeometry(0, 0, 220, 72)
        bg.setStyleSheet(
            "QFrame { background: rgba(10,14,28,0.92); border-radius: 14px;"
            " border: 1px solid rgba(255,255,255,0.08); }"
        )

        lay = QHBoxLayout(bg)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(10)

        # CPS / status column
        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl_cps = QLabel("0 CPS")
        self.lbl_cps.setStyleSheet("color:#e0e0e0;font-size:16px;font-weight:700;background:transparent;")
        self.lbl_status = QLabel("Stopped")
        self.lbl_status.setStyleSheet("color:rgba(255,255,255,0.45);font-size:10px;background:transparent;")
        self.lbl_meta = QLabel("00:00 | HK:-")
        self.lbl_meta.setStyleSheet("color:rgba(255,255,255,0.35);font-size:9px;background:transparent;")
        info.addWidget(self.lbl_cps)
        info.addWidget(self.lbl_status)
        info.addWidget(self.lbl_meta)
        lay.addLayout(info)
        lay.addStretch(1)

        # Toggle button
        self.btn_toggle = QPushButton("\u25b6")
        self.btn_toggle.setFixedSize(36, 36)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.08);border:none;border-radius:18px;"
            "color:#e0e0e0;font-size:16px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.14);}"
        )
        lay.addWidget(self.btn_toggle)

    def set_click_count(self, count: int):
        self._click_count = max(0, int(count))
        self._refresh_meta()

    def _refresh_meta(self):
        hk = self.lbl_meta.text().split("|")[-1].strip() if "|" in self.lbl_meta.text() else "HK:-"
        elapsed = self.lbl_meta.text().split("|")[0].strip() if "|" in self.lbl_meta.text() else "00:00"
        self.lbl_meta.setText(f"{elapsed} | {self._click_count} clicks | {hk}")

    def set_running(self, running: bool):
        self.btn_toggle.setText("\u25a0" if running else "\u25b6")
        self.lbl_status.setText("Running" if running else "Stopped")

    def set_cps(self, cps: float):
        self.lbl_cps.setText(f"{cps:.0f} CPS")

    def set_hotkey(self, hotkey: str):
        self._hotkey_label = hotkey.upper() if hotkey else "-"
        self._refresh_meta()

    def set_elapsed(self, seconds: int):
        mm = max(0, seconds) // 60
        ss = max(0, seconds) % 60
        self._elapsed_label = f"{mm:02d}:{ss:02d}"
        self._refresh_meta()

    def _refresh_meta(self):
        elapsed = getattr(self, "_elapsed_label", "00:00")
        hk = getattr(self, "_hotkey_label", "-")
        clicks = getattr(self, "_click_count", 0)
        self.lbl_meta.setText(f"{elapsed} | {clicks} clicks | HK:{hk}")

    # Drag support
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class QuickPresetRing(QWidget):
    """Circular avatar-like widget with 4 hoverable quarter segments."""

    segment_clicked = pyqtSignal(int)  # 0..3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 54)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._hover_segment = -1

    def _segment_at(self, pos: QPoint) -> int:
        cx, cy = self.width() / 2.0, self.height() / 2.0
        dx, dy = pos.x() - cx, pos.y() - cy
        if abs(dx) < 1 and abs(dy) < 1:
            return 0
        # Quadrants: 0=top-right,1=top-left,2=bottom-left,3=bottom-right
        if dx >= 0 and dy < 0:
            return 0
        if dx < 0 and dy < 0:
            return 1
        if dx < 0 and dy >= 0:
            return 2
        return 3

    def enterEvent(self, _event):
        self._hover = True
        self.update()

    def leaveEvent(self, _event):
        self._hover = False
        self._hover_segment = -1
        self.update()

    def mouseMoveEvent(self, event):
        self._hover_segment = self._segment_at(event.pos())
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._segment_at(event.pos())
            self.segment_clicked.emit(idx)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        r = min(w, h)
        center = QRectF(8, 8, r - 16, r - 16)

        # Core circle
        p.setPen(QPen(QColor(255, 255, 255, 35), 1))
        p.setBrush(QColor(255, 255, 255, 20))
        p.drawEllipse(center)

        # Ring split into 4 quarter arcs on hover.
        if self._hover:
            ring = QRectF(3, 3, r - 6, r - 6)
            base_col = QColor(255, 255, 255, 70)
            hi_col = QColor(120, 190, 255, 200)
            starts = [0, 90, 180, 270]
            # Qt arc uses 1/16 degree, counterclockwise from 3 o'clock.
            for idx, start in enumerate(starts):
                pen = QPen(hi_col if idx == self._hover_segment else base_col, 4)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawArc(ring, start * 16, 90 * 16)

        # Center glyph
        p.setPen(QColor(233, 237, 255, 210))
        font = p.font()
        font.setPixelSize(13)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "P")
        p.end()


def make_placeholder_page(title: str, subtitle: str) -> QWidget:
    page = QWidget()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(16)
    card = Card()
    card.setObjectName("Hero")
    add_shadow(card, blur=28, y=10, alpha=110)
    cl = QVBoxLayout(card)
    cl.setContentsMargins(28, 22, 28, 22)
    cl.setSpacing(8)
    t = QLabel(title)
    t.setObjectName("HeroTitle")
    s = QLabel(subtitle)
    s.setObjectName("HeroSub")
    cl.addWidget(t)
    cl.addWidget(s)
    cl.addStretch(1)
    lay.addWidget(card)
    lay.addStretch(1)
    return page


def make_projects_page() -> QWidget:
    page = QWidget()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(16)
    hero = Card()
    hero.setObjectName("Hero")
    add_shadow(hero, blur=28, y=10, alpha=110)
    hl = QVBoxLayout(hero)
    hl.setContentsMargins(28, 22, 28, 22)
    hl.setSpacing(8)
    t = QLabel("Plugins")
    t.setObjectName("HeroTitle")

    s = QLabel("Manage installed plugins and configure their tools.")
    s.setObjectName("HeroSub")
    hl.addWidget(t)
    hl.addWidget(s)
    grid = QHBoxLayout()
    grid.setSpacing(16)
    projects = []
    page._project_buttons = {}  # store clickable emoji buttons by name
    page._install_buttons = {}
    page._delete_buttons = {}
    page._status_labels = {}
    page._plugin_files = {}

    for proj_title, desc, icon, plugin_file in projects:
        card = Card()
        card.setObjectName("ConfigCard")
        add_shadow(card, blur=22, y=8, alpha=100)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(10)

        icon_btn = QPushButton(icon)
        icon_btn.setObjectName("IconBtn")
        icon_btn.setFixedSize(44, 44)
        icon_btn.setCursor(Qt.PointingHandCursor)
        page._project_buttons[proj_title] = icon_btn
        cl.addWidget(icon_btn)

        title_lbl = QLabel(proj_title)
        title_lbl.setObjectName("CardHeader")
        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("HeroSub")
        desc_lbl.setWordWrap(True)

        status_lbl = QLabel("Status: Not installed")
        status_lbl.setObjectName("HeroSub")

        row = QHBoxLayout()
        row.setSpacing(8)
        btn_install = QPushButton("Install")
        btn_install.setObjectName("HotkeyBtn")
        btn_delete = QPushButton("Delete")
        btn_delete.setObjectName("HotkeyBtn")
        row.addWidget(btn_install)
        row.addWidget(btn_delete)

        page._install_buttons[proj_title] = btn_install
        page._delete_buttons[proj_title] = btn_delete
        page._status_labels[proj_title] = status_lbl
        page._plugin_files[proj_title] = plugin_file

        cl.addWidget(title_lbl)
        cl.addWidget(desc_lbl)
        cl.addWidget(status_lbl)
        cl.addLayout(row)
        cl.addStretch(1)
        grid.addWidget(card)
    manage = Card()
    manage.setObjectName("ConfigCard")
    add_shadow(manage, blur=20, y=6, alpha=95)
    ml = QVBoxLayout(manage)
    ml.setContentsMargins(18, 16, 18, 16)
    ml.setSpacing(8)

    mh = QLabel("Installed Plugins")
    mh.setObjectName("CardHeader")
    md = QLabel("Manage all installed plugins from Marketplace and project tools.")
    md.setObjectName("HeroSub")
    md.setWordWrap(True)
    ml.addWidget(mh)
    ml.addWidget(md)

    page._managed_plugins_layout = QGridLayout()
    page._managed_plugins_layout.setContentsMargins(0, 4, 0, 0)
    page._managed_plugins_layout.setHorizontalSpacing(10)
    page._managed_plugins_layout.setVerticalSpacing(8)
    ml.addLayout(page._managed_plugins_layout)

    empty = QLabel("No plugins installed yet.")
    empty.setObjectName("WarnText")
    page._managed_empty_label = empty
    page._managed_plugins_layout.addWidget(empty, 0, 0, 1, 2)

    lay.addWidget(hero)
    if projects:
        lay.addLayout(grid)
    lay.addWidget(manage)

    editor_card = Card()
    editor_card.setObjectName("ConfigCard")
    add_shadow(editor_card, blur=20, y=6, alpha=95)
    el = QVBoxLayout(editor_card)
    el.setContentsMargins(0, 0, 0, 0)
    el.setSpacing(0)

    editor_top = QFrame()
    editor_top.setObjectName("TopBar")
    editor_top.setFixedHeight(48)
    etl = QHBoxLayout(editor_top)
    etl.setContentsMargins(14, 8, 10, 8)
    etl.setSpacing(8)
    editor_title = QLabel("Plugin Options")
    editor_title.setObjectName("TopTitle")
    editor_close = QPushButton("\u2715")
    editor_close.setObjectName("TitleBarBtn")
    editor_close.setFixedSize(30, 26)
    editor_close.setCursor(Qt.PointingHandCursor)
    etl.addWidget(editor_title)
    etl.addStretch(1)
    etl.addWidget(editor_close)

    editor_host = QWidget()
    editor_host_lay = QVBoxLayout(editor_host)
    editor_host_lay.setContentsMargins(16, 14, 16, 16)
    editor_host_lay.setSpacing(10)

    el.addWidget(editor_top)
    el.addWidget(editor_host)

    page._plugin_editor_card = editor_card
    page._plugin_editor_title = editor_title
    page._plugin_editor_close_btn = editor_close
    page._plugin_editor_host = editor_host
    page._plugin_editor_layout = editor_host_lay
    editor_card.hide()

    lay.addWidget(editor_card)
    lay.addStretch(1)
    return page

# 
#  Cinematic Loading Screen
# 
class CinematicLoadingScreen(QWidget):
    """Ultra-cinematic loading screen with spinning rings, glowing text, and theme integration."""

    finished = pyqtSignal()

    def __init__(self, theme_colors: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Animation state
        self._angle_outer = 0.0      # 12 RPM = 1.2 deg/frame at 60 FPS
        self._angle_mid = 0.0        # 20 RPM = 2.0 deg/frame
        self._angle_inner = 0.0      # 35 RPM = 3.5 deg/frame
        self._text_phase = 0.0       # For breathing/pulsing effect
        self._glow_intensity = 0.0   # For text glow animation
        self._opacity = 1.0          # For fade-out effect
        
        # Rotation speeds in degrees per frame (60 FPS)
        self._rpm_outer = 1.2
        self._rpm_mid = 2.0
        self._rpm_inner = 3.5
        
        # Theme colors (fallback to dark blue theme)
        self._colors = theme_colors or {
            "bg_start": "#0B1630",
            "bg_mid": "#0B1B3A",
            "bg_end": "#7A2CFF",
            "primary": "#5B73E8",
            "secondary": "#8B5CF6",
            "accent": "#00D9FF",
            "text_primary": "#E0E0E0"
        }
        
        # Animation timer
        self._timer = QTimer(self)
        self._timer.setInterval(24)  # ~42 FPS for smoother startup on slower machines
        self._timer.timeout.connect(self._animate_frame)
        
        # Fade-out animation
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InQuad)
        self._fade_anim.finished.connect(self.hide)

    def show_animated(self, geometry: QRect | None = None):
        """Show the loading screen centered on screen."""
        if geometry is None:
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            geometry = screen
        
        self.setGeometry(geometry)
        self.show()
        self.raise_()
        self._timer.start()
        self._angle_outer = 0.0
        self._angle_mid = 0.0
        self._angle_inner = 0.0
        self._text_phase = 0.0
        self._glow_intensity = 0.0
        self._opacity = 1.0

    def stop_and_hide(self):
        """Stop animation and fade out smoothly."""
        self._timer.stop()
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.start()
        self.finished.emit()

    def _animate_frame(self):
        """Update all animation states each frame."""
        self._angle_outer = (self._angle_outer + self._rpm_outer) % 360
        self._angle_mid = (self._angle_mid + self._rpm_mid) % 360
        self._angle_inner = (self._angle_inner + self._rpm_inner) % 360
        
        # Text breathing effect: 0..2p every 60 frames (~1 second)
        self._text_phase = (self._text_phase + 0.105) % (2 * math.pi)
        
        # Glow pulse: sin wave between 0.3 and 1.0
        self._glow_intensity = 0.65 + 0.35 * math.sin(self._text_phase)
        
        self.update()

    def paintEvent(self, _event):
        """Render cinematic loading screen with gradient background, rings, and glowing text."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        
        # -------------------------------------------
        # 1. Gradient background (3-stop)
        # -------------------------------------------
        grad = QLinearGradient(0, 0, w, h)
        bg_start = QColor(self._colors.get("bg_start", "#0B1630"))
        bg_mid = QColor(self._colors.get("bg_mid", "#0B1B3A"))
        bg_end = QColor(self._colors.get("bg_end", "#7A2CFF"))
        
        if not bg_start.isValid():
            bg_start = QColor(11, 22, 48)
        if not bg_mid.isValid():
            bg_mid = QColor(11, 27, 58)
        if not bg_end.isValid():
            bg_end = QColor(122, 44, 255)
        
        grad.setColorAt(0.0, bg_start)
        grad.setColorAt(0.55, bg_mid)
        grad.setColorAt(1.0, bg_end)
        
        p.fillRect(self.rect(), grad)
        
        # -------------------------------------------
        # 2. Three rotating rings with glow effect
        # -------------------------------------------
        center = QPointF(cx, cy)
        
        # Ring colors
        col_outer = QColor(self._colors.get("primary", "#5B73E8"))
        col_mid = QColor(self._colors.get("secondary", "#8B5CF6"))
        col_inner = QColor(self._colors.get("accent", "#00D9FF"))
        
        if not col_outer.isValid():
            col_outer = QColor(91, 115, 232)
        if not col_mid.isValid():
            col_mid = QColor(139, 92, 246)
        if not col_inner.isValid():
            col_inner = QColor(0, 217, 255)
        
        ring_radii = [120, 80, 45]
        angles = [self._angle_outer, self._angle_mid, self._angle_inner]
        colors = [col_outer, col_mid, col_inner]
        arc_spans = [75, 90, 60]  # Different arc lengths for visual interest
        
        for i, (radius, angle, color, span) in enumerate(zip(ring_radii, angles, colors, arc_spans)):
            # Draw glowing arc
            rect = QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius)
            
            # Glow effect: draw multiple slightly offset arcs with fading alpha
            for glow_offset in [3, 2, 1]:
                glow_col = QColor(color)
                glow_col.setAlpha(int(80 / (glow_offset + 1)))
                pen = QPen(glow_col, 4 + glow_offset)
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawArc(rect, int(angle * 16), int(span * 16))
            
            # Main bright arc
            pen = QPen(color, 4)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawArc(rect, int(angle * 16), int(span * 16))
        
        # -------------------------------------------
        # 3. Center circle with breathing pulse
        # -------------------------------------------
        breathing_scale = 0.95 + 0.1 * math.sin(self._text_phase)
        center_r = 12 * breathing_scale
        
        # Glowing center
        for glow_r in [center_r + 6, center_r + 3]:
            glow_col = QColor(col_inner)
            glow_col.setAlpha(int(100 * (1.0 - glow_r / (center_r + 8))))
            p.setBrush(glow_col)
            p.setPen(Qt.NoPen)
            p.drawEllipse(center, glow_r, glow_r)
        
        p.setBrush(col_inner)
        p.setPen(Qt.NoPen)
        p.drawEllipse(center, center_r, center_r)
        
        # -------------------------------------------
        # 4. Glowing animated text
        # -------------------------------------------
        text = "Loading..."
        text_col = QColor(self._colors.get("text_primary", "#E0E0E0"))
        if not text_col.isValid():
            text_col = QColor(224, 224, 224)
        
        # Apply glow intensity to text opacity
        text_col.setAlpha(int(255 * self._glow_intensity))
        p.setPen(text_col)
        
        font = p.font()
        font.setPixelSize(20)
        font.setBold(True)
        font.setFamily("Segoe UI")
        p.setFont(font)
        
        text_rect = QRectF(cx - 100, cy + 80, 200, 50)
        p.drawText(text_rect, Qt.AlignCenter, text)
        
        # Optional: Add slightly offset glow text beneath
        glow_col = QColor(col_inner)
        glow_col.setAlpha(int(60 * self._glow_intensity))
        p.setPen(glow_col)
        glow_rect = QRectF(cx - 100, cy + 82, 200, 50)
        p.drawText(glow_rect, Qt.AlignCenter, text)
        
        p.end()
