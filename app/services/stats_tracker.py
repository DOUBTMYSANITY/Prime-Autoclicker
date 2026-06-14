from __future__ import annotations

import json
import math
import os
import threading
import queue
from datetime import datetime, timedelta

STATS_FILE = os.path.join(os.path.expanduser("~"), ".mtautoclicker_stats.json")


# ── XP / Leveling constants ────────────────────────────
_MAX_LEVEL = 100
_MAX_XP = 1_000_000
_XP_CURVE = 2.2


def xp_for_level(level: int) -> int:
    """Total cumulative XP required to reach *level*."""
    if level <= 1:
        return 0
    if level >= _MAX_LEVEL:
        return _MAX_XP
    t = (level - 1) / float(_MAX_LEVEL - 1)
    return int(round(_MAX_XP * (t ** _XP_CURVE)))


def level_from_xp(xp: int) -> int:
    """Return the current level for a given total XP."""
    if xp >= _MAX_XP:
        return _MAX_LEVEL
    lv = 1
    while lv < _MAX_LEVEL and xp_for_level(lv + 1) <= xp:
        lv += 1
    return lv


_SECRET_KEYS = [
    "konami_code",
    "speedrunner",
    "patience",
    "lucky_seven",
    "page_turner",
    "click_frenzy",
]


class StatsTracker:
    """Persists click statistics to a JSON file."""

    def __init__(self):
        self._lock = threading.RLock()
        self._data = self._load()
        # Ensure secrets dict exists for older save files
        if "secrets" not in self._data:
            self._data["secrets"] = {}

    @staticmethod
    def _default_data() -> dict:
        return {
            "install_date": datetime.now().isoformat(),
            "total_clicks": 0,
            "total_sessions": 0,
            "total_session_seconds": 0.0,
            "daily": {},
            "heatmap": [],
            "hourly": {},
            "secrets": {},
        }

    @staticmethod
    def _load_file_payload() -> dict:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load(self) -> dict:
        result_q: "queue.Queue[tuple[bool, dict | Exception]]" = queue.Queue(maxsize=1)

        def _reader():
            try:
                result_q.put((True, self._load_file_payload()))
            except Exception as ex:
                result_q.put((False, ex))

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        try:
            ok, payload = result_q.get(timeout=1.0)
            if ok and isinstance(payload, dict):
                return payload
            return self._default_data()
        except queue.Empty:
            try:
                payload = self._load_file_payload()
                if isinstance(payload, dict):
                    return payload
            except Exception:
                pass
            return self._default_data()

    # ── Secrets helpers ─────────────────────────────────
    def unlock_secret(self, key: str):
        """Mark a secret as unlocked. Does nothing if already unlocked."""
        if key in _SECRET_KEYS:
            with self._lock:
                self._data.setdefault("secrets", {})[key] = True
            self._save()

    def is_secret_unlocked(self, key: str) -> bool:
        with self._lock:
            return self._data.get("secrets", {}).get(key, False)

    def _save(self):
        try:
            with self._lock:
                payload = dict(self._data)
            with open(STATS_FILE, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def _grant_xp(self, amount: int):
        current = int(self._data.get("xp", 0))
        self._data["xp"] = min(_MAX_XP, max(0, current + int(amount)))

    def record_click(self):
        self.record_click_batch(1)

    def record_click_batch(self, count: int = 1) -> tuple[int, int]:
        n = max(1, int(count))
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        hour = now.strftime("%H")
        with self._lock:
            old_total = int(self._data.get("total_clicks", 0))
            new_total = old_total + n
            self._data["total_clicks"] = new_total
            daily = self._data.setdefault("daily", {})
            daily[today] = daily.get(today, 0) + n
            hourly = self._data.setdefault("hourly", {})
            hourly[hour] = hourly.get(hour, 0) + n
            # +1 XP per click
            self._grant_xp(n)
            return old_total, new_total

    def record_click_position(self, x: int, y: int):
        with self._lock:
            hm = self._data.setdefault("heatmap", [])
            hm.append([x, y])
            # Keep only last 500 points to avoid huge JSON
            if len(hm) > 500:
                self._data["heatmap"] = hm[-500:]

    def record_session(self, duration_s: float):
        with self._lock:
            self._data["total_sessions"] = int(self._data.get("total_sessions", 0)) + 1
            self._data["total_session_seconds"] = float(self._data.get("total_session_seconds", 0.0)) + duration_s
            # +25 XP per session + 1 XP per 10s of active time
            bonus = 25 + int(duration_s / 10)
            self._grant_xp(bonus)
        self._save()

    # ── XP helpers ─────────────────────────────────────
    @property
    def xp(self) -> int:
        with self._lock:
            return min(_MAX_XP, max(0, int(self._data.get("xp", 0))))

    @property
    def level(self) -> int:
        return level_from_xp(self.xp)

    def xp_progress(self) -> tuple[int, int, int]:
        """Return (current_xp_in_level, xp_needed_for_next, level)."""
        lv = self.level
        if lv >= _MAX_LEVEL:
            return (_MAX_XP, _MAX_XP, _MAX_LEVEL)
        current_floor = xp_for_level(lv)
        next_ceil = xp_for_level(lv + 1)
        return (self.xp - current_floor, next_ceil - current_floor, lv)

    def add_xp(self, amount: int):
        with self._lock:
            self._grant_xp(amount)
        self._save()

    def save(self):
        self._save()

    @property
    def total_clicks(self) -> int:
        with self._lock:
            return self._data.get("total_clicks", 0)

    @property
    def total_sessions(self) -> int:
        with self._lock:
            return self._data.get("total_sessions", 0)

    @property
    def total_session_time(self) -> float:
        with self._lock:
            return self._data.get("total_session_seconds", 0.0)

    @property
    def install_date(self) -> str:
        with self._lock:
            return self._data.get("install_date", datetime.now().isoformat())

    def clicks_today(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            return self._data.get("daily", {}).get(today, 0)

    def clicks_this_week(self) -> int:
        now = datetime.now()
        start = now - timedelta(days=now.weekday())
        total = 0
        with self._lock:
            daily = dict(self._data.get("daily", {}))
        for i in range(7):
            day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            total += daily.get(day, 0)
        return total

    def clicks_this_month(self) -> int:
        prefix = datetime.now().strftime("%Y-%m")
        with self._lock:
            daily = dict(self._data.get("daily", {}))
        return sum(v for k, v in daily.items() if k.startswith(prefix))

    def last_7_days(self) -> list[tuple[str, int]]:
        """Return [(day_label, clicks), ...] for the last 7 days."""
        result = []
        now = datetime.now()
        with self._lock:
            daily = dict(self._data.get("daily", {}))
        for i in range(6, -1, -1):
            d = now - timedelta(days=i)
            key = d.strftime("%Y-%m-%d")
            label = d.strftime("%a")  # Mon, Tue, ...
            result.append((label, daily.get(key, 0)))
        return result

    def best_day(self) -> tuple[str, int]:
        with self._lock:
            daily = dict(self._data.get("daily", {}))
        if not daily:
            return ("N/A", 0)
        best_key = max(daily, key=daily.get)
        return (best_key, daily[best_key])

    def avg_clicks_per_session(self) -> float:
        with self._lock:
            s = self._data.get("total_sessions", 0)
            total_clicks = self._data.get("total_clicks", 0)
        if s == 0:
            return 0.0
        return total_clicks / s

    def heatmap_points(self) -> list[tuple[int, int]]:
        with self._lock:
            heatmap = list(self._data.get("heatmap", []))
        return [(p[0], p[1]) for p in heatmap if len(p) >= 2]

    def peak_hour(self) -> str:
        with self._lock:
            hourly = dict(self._data.get("hourly", {}))
        if not hourly:
            return "N/A"
        best = max(hourly, key=hourly.get)
        return f"{best}:00"

    def get_achievements(self) -> list[tuple[str, str, bool]]:
        """Legacy flat list – kept for backward compat."""
        flat = []
        for cat in self.get_categorized_achievements():
            flat.extend(cat["achievements"])
        return [(icon, name, earned) for icon, name, _desc, earned in flat]

    def get_categorized_achievements(self) -> list[dict]:
        """Return achievements grouped by category, each with a description.

        Returns a list of dicts:
            {
                "category": str,
                "icon": str,
                "stat_label": str,          # e.g. "1,234 Total Clicks"
                "achievements": [(icon, name, description, earned), ...]
            }
        """
        tc = self.total_clicks
        ts = self.total_sessions
        tt = self.total_session_time
        with self._lock:
            hourly = dict(self._data.get("hourly", {}))
            daily = dict(self._data.get("daily", {}))
            heatmap = list(self._data.get("heatmap", []))
        best_date, best_val = self.best_day()
        days_used = len(daily)
        unique_hours = len([h for h, v in hourly.items() if v > 0])
        avg = self.avg_clicks_per_session()

        def _fmt(n: int | float) -> str:
            if isinstance(n, float):
                return f"{n:,.1f}"
            return f"{n:,}"

        def _fmt_time(secs: float) -> str:
            if secs < 60:
                return f"{secs:.0f}s"
            if secs < 3600:
                return f"{secs / 60:.1f}min"
            return f"{secs / 3600:.1f}h"

        session_achievements = [
            ("\U0001f3af", "First Session", "Complete your first autoclicker session.", ts >= 1),
            ("\U0001f4ca", "10 Sessions", "Run 10 separate sessions.", ts >= 10),
            ("\U0001f5d3", "50 Sessions", "50 sessions - you are a regular.", ts >= 50),
            ("\U0001f451", "100 Sessions", "100 sessions - crowned veteran.", ts >= 100),
            ("\U0001f9e0", "500 Sessions", "500 sessions. Big brain energy.", ts >= 500),
            ("\U0001f3ed", "1,000 Sessions", "1K sessions - industrial scale.", ts >= 1_000),
        ]
        session_achievements.extend([
            ("\U0001f6a8", "2,500 Sessions", "Push beyond 2.5K sessions.", ts >= 2_500),
            ("\U0001f680", "5,000 Sessions", "Reach 5K sessions total.", ts >= 5_000),
            ("\U0001f9f1", "10,000 Sessions", "Hit 10K sessions.", ts >= 10_000),
            ("\U0001f30c", "25,000 Sessions", "Complete 25K sessions.", ts >= 25_000),
        ])

        daily_achievements = [
            ("\U0001f4a5", "10K in One Day", "Click 10,000 times in a single day.", best_val >= 10_000),
            ("\U0001f308", "50K in One Day", "Reach 50K clicks in one day.", best_val >= 50_000),
            ("\U0001f4a8", "100K in One Day", "An incredible 100K day.", best_val >= 100_000),
        ]
        daily_achievements.extend([
            ("\U0001f31f", "250K in One Day", "Reach 250K clicks in one day.", best_val >= 250_000),
            ("\U0001f525", "500K in One Day", "Break 500K clicks in one day.", best_val >= 500_000),
        ])

        streak_achievements = [
            ("\U0001f4c5", "7-Day Streak", "Use the clicker 7 days in a row.", self._has_day_streak(daily, 7)),
            ("\U0001f5d3\ufe0f", "14-Day Streak", "Keep it up for 14 consecutive days.", self._has_day_streak(daily, 14)),
            ("\U0001f525\ufe0f", "30-Day Streak", "A full month streak - unstoppable.", self._has_day_streak(daily, 30)),
            ("\U0001f4c6", "Active 30 Days", "Use the app on 30 different days.", days_used >= 30),
            ("\U0001f30f", "Active 100 Days", "100 unique days of clicking.", days_used >= 100),
            ("\U0001f389", "Active 365 Days", "One full year of dedication.", days_used >= 365),
        ]
        streak_achievements.extend([
            ("\U0001f4aa", "60-Day Streak", "Keep a 60-day daily streak.", self._has_day_streak(daily, 60)),
            ("\U0001f31e", "90-Day Streak", "Hold a 90-day streak.", self._has_day_streak(daily, 90)),
            ("\U0001f984", "180-Day Streak", "Maintain a 180-day streak.", self._has_day_streak(daily, 180)),
            ("\U0001f451", "365-Day Streak", "Complete a full-year streak.", self._has_day_streak(daily, 365)),
        ])

        return [
            # ── Clicks ──────────────────────────────────
            {
                "category": "Clicks",
                "icon": "🖱",
                "stat_label": f"{_fmt(tc)} Total Clicks",
                "achievements": [
                    ("\U0001f5b1", "First Click", "Perform your very first click.", tc >= 1),
                    ("\U0001f4af", "100 Clicks", "Reach 100 total clicks.", tc >= 100),
                    ("\U0001f525", "1,000 Clicks", "Click your way to a thousand.", tc >= 1_000),
                    ("\u26a1", "10,000 Clicks", "Hit 10K – you're getting serious.", tc >= 10_000),
                    ("\U0001f3c6", "100,000 Clicks", "100K clicks. That's dedication.", tc >= 100_000),
                    ("\U0001f680", "Speed Demon", "Reach 500K total clicks.", tc >= 500_000),
                    ("\U0001f48e", "1,000,000 Clicks", "One million clicks. Legendary.", tc >= 1_000_000),
                    ("\U0001f30d", "5,000,000 Clicks", "Five million – world-class clicker.", tc >= 5_000_000),
                    ("\U0001f30c", "10,000,000 Clicks", "10M clicks. Are you even human?", tc >= 10_000_000),
                    ("\u2b50", "50,000,000 Clicks", "50 million. Absolute legend.", tc >= 50_000_000),
                ],
            },
            # ── Sessions ────────────────────────────────
            {
                "category": "Sessions",
                "icon": "🎯",
                "stat_label": f"{_fmt(ts)} Total Sessions",
                "achievements": session_achievements,
            },
            # ── Active Time ─────────────────────────────
            {
                "category": "Active Time",
                "icon": "⏱",
                "stat_label": f"{_fmt_time(tt)} Total Active",
                "achievements": [
                    ("\u23f1", "1 Minute Active", "Spend 1 minute of active clicking.", tt >= 60),
                    ("\u23f0", "1 Hour Active", "One full hour of active time.", tt >= 3600),
                    ("\u231b", "10 Hours Active", "10 hours – serious commitment.", tt >= 36_000),
                    ("\U0001f3c5", "24 Hours Active", "A full day's worth of clicking.", tt >= 86_400),
                    ("\U0001f4ab", "100 Hours Active", "100 hours. Truly unstoppable.", tt >= 360_000),
                ],
            },
            # ── Daily Records ───────────────────────────
            {
                "category": "Daily Records",
                "icon": "💥",
                "stat_label": f"Best Day: {_fmt(best_val)} clicks",
                "achievements": daily_achievements,
            },
            # ── Streaks & Consistency ───────────────────
            {
                "category": "Streaks & Consistency",
                "icon": "📅",
                "stat_label": f"{days_used} Days Used",
                "achievements": streak_achievements,
            },
            # ── Time of Day ─────────────────────────────
            {
                "category": "Time of Day",
                "icon": "🌙",
                "stat_label": f"{unique_hours}/24 Hours Covered",
                "achievements": [
                    ("\U0001f319", "Night Owl", "Click between midnight and 3 AM.", hourly.get("00", 0) > 0 or hourly.get("01", 0) > 0 or hourly.get("02", 0) > 0),
                    ("\U0001f305", "Early Bird", "Click between 5 and 7 AM.", hourly.get("05", 0) > 0 or hourly.get("06", 0) > 0),
                    ("\u2600\ufe0f", "High Noon", "Click at noon.", hourly.get("12", 0) > 0),
                    ("\U0001f307", "Golden Hour", "Click between 6 and 8 PM.", hourly.get("18", 0) > 0 or hourly.get("19", 0) > 0),
                    ("\U0001f570", "Around the Clock", "Click during all 24 hours of the day.", unique_hours >= 24),
                ],
            },
            # ── Tracking & Precision ────────────────────
            {
                "category": "Tracking & Precision",
                "icon": "📍",
                "stat_label": f"{len(heatmap)} Positions Tracked",
                "achievements": [
                    ("\U0001f4cd", "Position Tracker", "Record 100 click positions on the heatmap.", len(heatmap) >= 100),
                    ("\U0001f5fa", "Cartographer", "Map out 500 positions on the heatmap.", len(heatmap) >= 500),
                ],
            },
            # ── Weekly ──────────────────────────────────
            {
                "category": "Weekly",
                "icon": "📈",
                "stat_label": f"{_fmt(self.clicks_this_week())} Clicks This Week",
                "achievements": [
                    ("\U0001f4c8", "Week Warrior", "Click 5,000 times in one week.", self.clicks_this_week() >= 5_000),
                    ("\U0001f4aa", "Week Champion", "Reach 25K clicks in a single week.", self.clicks_this_week() >= 25_000),
                ],
            },
            # ── Averages ────────────────────────────────
            {
                "category": "Averages",
                "icon": "🧮",
                "stat_label": f"{_fmt(avg)} Avg Clicks/Session",
                "achievements": [
                    ("\U0001f9ee", "Avg 1K/Session", "Average at least 1,000 clicks per session.", avg >= 1_000),
                    ("\U0001f9ea", "Avg 10K/Session", "Average 10,000+ clicks per session.", avg >= 10_000),
                ],
            },
            # ── Secrets (hidden) ────────────────────────
            {
                "category": "Secrets",
                "icon": "🔮",
                "stat_label": "Hidden achievements — discover them yourself!",
                "hidden": True,
                "achievements": [
                    ("\U0001f3ae", "Konami Code", "Enter the classic Konami Code: ↑↑↓↓←→←→BA", self.is_secret_unlocked("konami_code")),
                    ("\u26a1", "Speedrunner", "Set the click interval to exactly 1 ms.", self.is_secret_unlocked("speedrunner")),
                    ("\U0001f9d8", "Patience is a Virtue", "Set the interval to the maximum (24 hours).", self.is_secret_unlocked("patience")),
                    ("\U0001f340", "Lucky Seven", "Reach exactly 777,777 total clicks.", self.is_secret_unlocked("lucky_seven")),
                    ("\U0001f4d6", "Page Turner", "Visit every page in a single app session.", self.is_secret_unlocked("page_turner")),
                    ("\U0001f4a5", "Click Frenzy", "Start & stop the clicker 5 times in 10 seconds.", self.is_secret_unlocked("click_frenzy")),
                ],
            },
        ]

    @staticmethod
    def _has_day_streak(daily: dict, streak: int) -> bool:
        """Check if there are `streak` consecutive days with clicks."""
        if not daily:
            return False
        from datetime import datetime, timedelta
        dates = sorted(daily.keys())
        best = 1
        run = 1
        for i in range(1, len(dates)):
            try:
                prev = datetime.strptime(dates[i - 1], "%Y-%m-%d").date()
                curr = datetime.strptime(dates[i], "%Y-%m-%d").date()
                if (curr - prev) == timedelta(days=1):
                    run += 1
                    best = max(best, run)
                else:
                    run = 1
            except ValueError:
                run = 1
        return best >= streak
