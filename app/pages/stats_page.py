from __future__ import annotations

import sys
import importlib
from pathlib import Path

from datetime import datetime

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QLinearGradient, QColor, QBrush, QPen
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSizePolicy, QComboBox,
)
from PyQt5.QtCore import QTimer

# Add parent directory to path if widgets is there
sys.path.insert(0, str(Path(__file__).parent))

from app.styling.localization import tr
from app.styling.themes import get_theme
from app.gui.widgets import Card, add_shadow
from app.services.stats_tracker import StatsTracker


# ----------------------------
# Bar Chart Widget
# ----------------------------

class BarChartWidget(QWidget):
    """Simple vertical bar chart for last-7-days data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[tuple[str, int]] = []
        self._grad_top = QColor("#6C5CE7")
        self._grad_bot = QColor("#4E8DFF")
        self._value_color = QColor(233, 237, 255, 200)
        self._label_color = QColor(233, 237, 255, 140)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_palette(self, palette: dict):
        top = QColor(palette.get("slider_handle", palette.get("accent_solid", "#6C5CE7")))
        self._grad_top = top if top.isValid() else QColor("#6C5CE7")

        bottom = QColor(palette.get("accent_solid", "#4E8DFF"))
        self._grad_bot = bottom if bottom.isValid() else QColor("#4E8DFF")

        value = QColor(palette.get("text_primary", "#E9EDFF"))
        if not value.isValid():
            value = QColor(233, 237, 255, 200)
        value.setAlpha(210)
        self._value_color = value

        label = QColor(palette.get("text_secondary", "rgba(233,237,255,0.70)"))
        if not label.isValid():
            label = QColor(233, 237, 255, 140)
        label.setAlpha(170)
        self._label_color = label
        self.update()

    def set_data(self, data: list[tuple[str, int]]):
        self._data = data
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        n = len(self._data)
        max_val = max((v for _, v in self._data), default=1) or 1
        bar_w = max(12, min(40, (w - 20) // n - 10))
        spacing = (w - bar_w * n) / (n + 1)
        label_h = 22
        chart_h = h - label_h - 20  # top padding

        # Draw bars
        for i, (label, val) in enumerate(self._data):
            x = spacing + i * (bar_w + spacing)
            bar_h = max(4, int((val / max_val) * chart_h)) if val > 0 else 4
            y = h - label_h - bar_h

            # Bar gradient
            g = QLinearGradient(x, y, x, y + bar_h)
            g.setColorAt(0.0, self._grad_top)
            g.setColorAt(1.0, self._grad_bot)
            p.setBrush(QBrush(g))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 4, 4)

            # Value on top
            p.setPen(QPen(self._value_color))
            p.setFont(p.font())
            val_text = self._format_number(val)
            p.drawText(int(x), int(y - 4), int(bar_w), 16, Qt.AlignCenter, val_text)

            # Day label
            p.setPen(QPen(self._label_color))
            p.drawText(int(x), int(h - label_h), int(bar_w), label_h, Qt.AlignCenter, label)

        p.end()

    @staticmethod
    def _format_number(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)


# ----------------------------
# Heatmap Widget
# ----------------------------

class HeatmapWidget(QWidget):
    """Renders a screen-based click heatmap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[tuple[int, int]] = []
        self._screen_w = 1920
        self._screen_h = 1080
        self._bg_color = QColor(8, 14, 30, 200)
        self._empty_text = QColor(233, 237, 255, 80)
        self._grid_color = QColor(255, 255, 255, 15)
        self._glow_color = QColor(78, 141, 255)
        self._core_color = QColor(120, 180, 255, 200)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_palette(self, palette: dict):
        bg = QColor(palette.get("input_bg", "rgba(8,14,30,0.78)"))
        self._bg_color = bg if bg.isValid() else QColor(8, 14, 30, 200)

        empty = QColor(palette.get("text_secondary", "rgba(233,237,255,0.50)"))
        self._empty_text = empty if empty.isValid() else QColor(233, 237, 255, 80)

        grid = QColor(palette.get("badge_border", "rgba(255,255,255,0.15)"))
        self._grid_color = grid if grid.isValid() else QColor(255, 255, 255, 15)

        glow = QColor(palette.get("accent_solid", "#4E8DFF"))
        self._glow_color = glow if glow.isValid() else QColor(78, 141, 255)

        core = QColor(palette.get("slider_handle", palette.get("accent_solid", "#78B4FF")))
        self._core_color = core if core.isValid() else QColor(120, 180, 255, 200)
        self.update()

    def set_data(self, points: list[tuple[int, int]], screen_w: int = 1920, screen_h: int = 1080):
        self._points = points
        self._screen_w = screen_w
        self._screen_h = screen_h
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()

        # Background
        p.setBrush(QBrush(self._bg_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, 12, 12)

        if not self._points:
            p.setPen(QPen(self._empty_text))
            p.drawText(self.rect(), Qt.AlignCenter, "No click data yet. Start clicking!")
            p.end()
            return

        # Grid lines
        p.setPen(QPen(self._grid_color))
        for i in range(1, 4):
            x = int(w * i / 4)
            p.drawLine(x, 0, x, h)
        for i in range(1, 3):
            y = int(h * i / 3)
            p.drawLine(0, y, w, y)

        # Draw heat dots
        sw, sh = max(1, self._screen_w), max(1, self._screen_h)
        for sx, sy in self._points:
            x = int(sx / sw * w)
            y = int(sy / sh * h)
            # Glow
            for radius, alpha in [(16, 8), (10, 20), (6, 50)]:
                c = QColor(self._glow_color)
                c.setAlpha(alpha)
                p.setBrush(QBrush(c))
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPoint(x, y), radius, radius)
            # Core
            p.setBrush(QBrush(self._core_color))
            p.drawEllipse(QPoint(x, y), 3, 3)

        p.end()


# ----------------------------
# Stats Page
# ----------------------------

class StatsPage(QWidget):
    def __init__(self, tracker: StatsTracker, parent=None):
        super().__init__(parent)
        self.tracker = tracker

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
        self.hero_title = QLabel(tr("click_analytics"))
        self.hero_title.setObjectName("HeroTitle")
        self.hero_sub = QLabel(tr("analytics_sub"))
        self.hero_sub.setObjectName("HeroSub")
        hl.addWidget(self.hero_title)
        hl.addWidget(self.hero_sub)
        hl.addStretch(1)

        # Stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)

        self.card_total = self._make_stat_card("🏆", tr("all_time"), "0")
        self.card_today = self._make_stat_card("📅", tr("today"), "0")
        self.card_week = self._make_stat_card("📊", tr("this_week"), "0")
        self.card_month = self._make_stat_card("📈", tr("this_month"), "0")

        stats_row.addWidget(self.card_total[0])
        stats_row.addWidget(self.card_today[0])
        stats_row.addWidget(self.card_week[0])
        stats_row.addWidget(self.card_month[0])

        # Bottom row: chart + extra stats
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        # Chart card
        chart_card = Card()
        chart_card.setObjectName("ConfigCard")
        add_shadow(chart_card, blur=26, y=10, alpha=110)
        cc_lay = QVBoxLayout(chart_card)
        cc_lay.setContentsMargins(20, 18, 20, 18)
        cc_lay.setSpacing(12)

        chart_header = QHBoxLayout()
        chart_header.setSpacing(10)
        chart_icon = QLabel("📉")
        chart_icon.setObjectName("HeaderIcon")
        chart_icon.setFixedSize(34, 34)
        chart_icon.setAlignment(Qt.AlignCenter)
        self.chart_title = QLabel(tr("last_7_days"))
        self.chart_title.setObjectName("CardHeader")
        chart_header.addWidget(chart_icon)
        chart_header.addWidget(self.chart_title)
        chart_header.addStretch(1)
        cc_lay.addLayout(chart_header)

        self.bar_chart = BarChartWidget()
        cc_lay.addWidget(self.bar_chart, 1)
        self.chart_period = QComboBox()
        self.chart_period.setObjectName("UnitDrop")
        self.chart_period.addItems(["Day", "Week", "Month"])
        self.chart_period.currentIndexChanged.connect(lambda _i: self.refresh())
        chart_header.addWidget(self.chart_period)

        # Extra stats card
        extra_card = Card()
        extra_card.setObjectName("ConfigCard")
        add_shadow(extra_card, blur=26, y=10, alpha=110)
        ec_lay = QVBoxLayout(extra_card)
        ec_lay.setContentsMargins(20, 18, 20, 18)
        ec_lay.setSpacing(12)

        extra_header = QHBoxLayout()
        extra_header.setSpacing(10)
        extra_icon = QLabel("⚡")
        extra_icon.setObjectName("HeaderIcon")
        extra_icon.setFixedSize(34, 34)
        extra_icon.setAlignment(Qt.AlignCenter)
        self.extra_title = QLabel(tr("milestones"))
        self.extra_title.setObjectName("CardHeader")
        extra_header.addWidget(extra_icon)
        extra_header.addWidget(self.extra_title)
        extra_header.addStretch(1)
        ec_lay.addLayout(extra_header)

        inner = Card(radius=16)
        inner.setObjectName("InnerPanel")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(14, 14, 14, 14)
        inner_lay.setSpacing(10)

        self.lbl_sessions = QLabel("Total Sessions:  0")
        self.lbl_sessions.setObjectName("StatLine")
        self.lbl_avg = QLabel("Avg Clicks/Session:  0")
        self.lbl_avg.setObjectName("StatLine")
        self.lbl_best_day = QLabel("Best Day:  N/A")
        self.lbl_best_day.setObjectName("StatLine")
        self.lbl_total_time = QLabel("Total Active Time:  0s")
        self.lbl_total_time.setObjectName("StatLine")
        self.lbl_since = QLabel("Tracking Since:  —")
        self.lbl_since.setObjectName("StatLine")
        self.lbl_peak = QLabel("Peak Hour:  N/A")
        self.lbl_peak.setObjectName("StatLine")

        for w in (self.lbl_sessions, self.lbl_avg, self.lbl_best_day, self.lbl_total_time, self.lbl_since, self.lbl_peak):
            inner_lay.addWidget(w)
        inner_lay.addStretch(1)
        ec_lay.addWidget(inner, 1)

        bottom_row.addWidget(chart_card, 3)
        bottom_row.addWidget(extra_card, 2)

        # Heatmap card
        heatmap_card = Card()
        heatmap_card.setObjectName("ConfigCard")
        add_shadow(heatmap_card, blur=26, y=10, alpha=110)
        hm_lay = QVBoxLayout(heatmap_card)
        hm_lay.setContentsMargins(20, 18, 20, 18)
        hm_lay.setSpacing(12)

        hm_header = QHBoxLayout()
        hm_header.setSpacing(10)
        hm_icon = QLabel("🔥")
        hm_icon.setObjectName("HeaderIcon")
        hm_icon.setFixedSize(34, 34)
        hm_icon.setAlignment(Qt.AlignCenter)
        self.hm_title = QLabel(tr("click_heatmap"))
        self.hm_title.setObjectName("CardHeader")
        hm_header.addWidget(hm_icon)
        hm_header.addWidget(self.hm_title)
        hm_header.addStretch(1)
        hm_lay.addLayout(hm_header)

        self.heatmap = HeatmapWidget()
        self.heatmap.setMinimumHeight(220)
        hm_lay.addWidget(self.heatmap, 1)

        # Performance card
        perf_card = Card()
        perf_card.setObjectName("ConfigCard")
        add_shadow(perf_card, blur=26, y=10, alpha=110)
        pf_lay = QVBoxLayout(perf_card)
        pf_lay.setContentsMargins(20, 18, 20, 18)
        pf_lay.setSpacing(12)

        pf_header = QHBoxLayout()
        pf_header.setSpacing(10)
        pf_icon = QLabel("🖥")
        pf_icon.setObjectName("HeaderIcon")
        pf_icon.setFixedSize(34, 34)
        pf_icon.setAlignment(Qt.AlignCenter)
        self.pf_title = QLabel(tr("cpu_perf"))
        self.pf_title.setObjectName("CardHeader")
        pf_header.addWidget(pf_icon)
        pf_header.addWidget(self.pf_title)
        pf_header.addStretch(1)
        pf_lay.addLayout(pf_header)

        pf_inner = Card(radius=16)
        pf_inner.setObjectName("InnerPanel")
        pfi_lay = QHBoxLayout(pf_inner)
        pfi_lay.setContentsMargins(14, 14, 14, 14)
        pfi_lay.setSpacing(24)

        self.lbl_cpu = QLabel("CPU:  — %")
        self.lbl_cpu.setObjectName("StatLine")
        self.lbl_latency = QLabel("Click Latency:  — ms")
        self.lbl_latency.setObjectName("StatLine")
        self.lbl_mem = QLabel("Memory:  — MB")
        self.lbl_mem.setObjectName("StatLine")
        pfi_lay.addWidget(self.lbl_cpu)
        pfi_lay.addWidget(self.lbl_latency)
        pfi_lay.addWidget(self.lbl_mem)
        pfi_lay.addStretch(1)
        pf_lay.addWidget(pf_inner)

        self._perf_timer = QTimer(self)
        self._perf_timer.timeout.connect(self._update_perf)
        self._perf_timer.start(2000)
        self._last_click_time = 0.0
        self.apply_theme(get_theme().get("palette", {}))

        lay.addWidget(hero)
        lay.addLayout(stats_row)
        lay.addLayout(bottom_row)
        lay.addWidget(heatmap_card)
        lay.addWidget(perf_card)
        lay.addStretch(1)

    def _make_stat_card(self, icon: str, title: str, value: str):
        card = Card()
        card.setObjectName("ConfigCard")
        add_shadow(card, blur=22, y=8, alpha=100)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("HeaderIcon")
        icon_lbl.setFixedSize(34, 34)
        icon_lbl.setAlignment(Qt.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("TimeUnit")

        value_lbl = QLabel(value)
        value_lbl.setObjectName("StatValue")

        cl.addWidget(icon_lbl)
        cl.addWidget(title_lbl)
        cl.addWidget(value_lbl)
        cl.addStretch(1)
        return card, value_lbl, title_lbl

    @staticmethod
    def _fmt(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:,.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:,.1f}K"
        return f"{n:,}"
    def _chart_data_for_period(self) -> list[tuple[str, int]]:
        period = self.chart_period.currentText().lower()
        t = self.tracker
        if period == "day":
            hourly = t._data.get("hourly", {})
            return [(f"{h}", int(hourly.get(f"{h:02d}", 0))) for h in range(0, 24, 3)]
        if period == "month":
            daily = t._data.get("daily", {})
            now = datetime.now()
            vals: list[tuple[str, int]] = []
            for i in range(3, -1, -1):
                m = (now.month - i - 1) % 12 + 1
                y = now.year if now.month - i > 0 else now.year - 1
                prefix = f"{y:04d}-{m:02d}"
                total = sum(v for k, v in daily.items() if str(k).startswith(prefix))
                vals.append((f"{m:02d}", total))
            return vals
        return t.last_7_days()

    def _update_daily_challenge(self):
        goal = 2000
        done = self.tracker.clicks_today()
        pct = int((done / max(goal, 1)) * 100)
        status = "completed" if done >= goal else "in progress"
        self.lbl_challenge.setText(
            f"Goal: {goal:,} clicks today | Progress: {done:,} ({pct}%) | Status: {status}"
        )

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        if seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"

    def record_click_time(self):
        """Called each click to update latency display."""
        import time as _time
        now = _time.time()
        if self._last_click_time > 0:
            delta = (now - self._last_click_time) * 1000
            self.lbl_latency.setText(f"Click Latency:  {delta:.1f} ms")
        self._last_click_time = now

    def _update_perf(self):
        try:
            psutil_mod = importlib.import_module("psutil")
            self.lbl_cpu.setText(f"CPU:  {psutil_mod.cpu_percent(interval=0):.0f} %")
            mem = psutil_mod.Process().memory_info().rss / (1024 * 1024)
            self.lbl_mem.setText(f"Memory:  {mem:.1f} MB")
        except Exception:
            self.lbl_cpu.setText("CPU:  N/A")
            self.lbl_mem.setText("Memory:  N/A")

    def refresh(self):
        """Re-read all stats from tracker and update UI."""
        t = self.tracker
        self.card_total[1].setText(self._fmt(t.total_clicks))
        self.card_today[1].setText(self._fmt(t.clicks_today()))
        self.card_week[1].setText(self._fmt(t.clicks_this_week()))
        self.card_month[1].setText(self._fmt(t.clicks_this_month()))

        self.bar_chart.set_data(self._chart_data_for_period())

        self.lbl_sessions.setText(f"Total Sessions:  {t.total_sessions:,}")
        avg = t.avg_clicks_per_session()
        self.lbl_avg.setText(f"Avg Clicks/Session:  {self._fmt(int(avg))}")
        best_date, best_val = t.best_day()
        self.lbl_best_day.setText(f"Best Day:  {best_date}  ({self._fmt(best_val)} clicks)")
        self.lbl_total_time.setText(f"Total Active Time:  {self._fmt_time(t.total_session_time)}")
        try:
            d = datetime.fromisoformat(t.install_date).strftime("%b %d, %Y")
        except Exception:
            d = "Unknown"
        self.lbl_since.setText(f"Tracking Since:  {d}")
        self.lbl_peak.setText(f"Peak Hour:  {t.peak_hour()}")

        # Update heatmap
        points = t.heatmap_points()
        self.heatmap.set_data(points)
        if hasattr(self, "lbl_challenge"):
            self._update_daily_challenge()

    def apply_theme(self, palette: dict | None = None):
        """Update custom-painted widgets that are not covered by app stylesheet."""
        p = palette or get_theme().get("palette", {})
        self.bar_chart.set_palette(p)
        self.heatmap.set_palette(p)

    def retranslateUi(self):
        """Update all translatable text."""
        self.hero_title.setText(tr("click_analytics"))
        self.hero_sub.setText(tr("analytics_sub"))
        self.card_total[2].setText(tr("all_time"))
        self.card_today[2].setText(tr("today"))
        self.card_week[2].setText(tr("this_week"))
        self.card_month[2].setText(tr("this_month"))
        self.chart_title.setText(tr("last_7_days"))
        self.extra_title.setText(tr("milestones"))
        self.hm_title.setText(tr("click_heatmap"))
        self.pf_title.setText(tr("cpu_perf"))
