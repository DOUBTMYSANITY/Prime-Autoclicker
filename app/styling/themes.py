"""
Theme definitions for Prime Autoclicker.
Each theme has:
  - id: unique key
  - name: display name
  - icon: emoji
  - gradient: 3-stop gradient colours for the background
  - unlock: achievement requirement (None = default/always unlocked)
  - unlock_desc: human-readable unlock condition
  - palette: dict of colour tokens consumed by _apply_styles()
"""
from __future__ import annotations

import json
import os
import re

THEME_FILE = os.path.join(os.path.expanduser("~"), ".mtautoclicker_themes.json")


def _p(
    *,
    base: str,
    sidebar: str,
    topbar: str,
    hero: str,
    config_card: str,
    inner_panel: str,
    card_border: str = "rgba(255,255,255,0.06)",
    text_primary: str = "#E9EDFF",
    text_secondary: str = "rgba(233,237,255,0.75)",
    accent: str = "rgba(78,141,255,{a})",
    accent_solid: str = "#4E8DFF",
    logo_bg: str = "rgba(105,63,255,0.20)",
    logo_border: str = "rgba(131,93,255,0.35)",
    pill_bg: str = "rgba(255,255,255,0.05)",
    pill_border: str = "rgba(255,255,255,0.06)",
    pill_active_bg: str = "rgba(78,141,255,0.18)",
    pill_active_border: str = "rgba(78,141,255,0.28)",
    input_bg: str = "rgba(0,0,0,0.22)",
    input_border: str = "rgba(255,255,255,0.08)",
    combo_bg: str = "#161E36",
    combo_border: str = "#1F2944",
    combo_list_bg: str = "#0E1628",
    combo_sel_bg: str = "#1C2F58",
    toggle_bg: str = "#161E36",
    toggle_border: str = "#1F2944",
    toggle_active_bg: str = "#1C2F58",
    toggle_active_border: str = "#2E4A80",
    slider_groove: str = "rgba(255,255,255,0.10)",
    slider_handle: str = "#4E8DFF",
    slider_sub: str = "rgba(78,141,255,0.45)",
    checkbox_bg: str = "#0F1829",
    checkbox_border: str = "#2A3350",
    checkbox_checked: str = "#2E5599",
    checkbox_checked_border: str = "#3D6AB3",
    badge_bg: str = "rgba(255,255,255,0.08)",
    badge_border: str = "rgba(255,255,255,0.10)",
    start_btn_bg: str = "rgba(78,141,255,0.18)",
    start_btn_border: str = "rgba(78,141,255,0.28)",
    stop_btn_bg: str = "rgba(255,90,90,0.18)",
    stop_btn_border: str = "rgba(255,90,90,0.35)",
    running_color: str = "#9CFFB2",
    stopped_color: str = "#FF9C9C",
) -> dict:
    return {k: v for k, v in locals().items()}


# ─── 10 Themes ───────────────────────────────────────────────

THEMES: list[dict] = [
    # 0 — Default (Deep Space) – always unlocked
    {
        "id": "default",
        "name": "Deep Space",
        "icon": "🌌",
        "gradient": ["#0B1630", "#0B1B3A", "#7A2CFF"],
        "unlock": None,
        "unlock_desc": "Default theme",
        "palette": _p(
            base="rgba(16,28,56,0.55)",
            sidebar="rgba(10,18,40,0.70)",
            topbar="rgba(12,21,45,0.72)",
            hero="rgba(14,24,52,0.65)",
            config_card="rgba(12,20,44,0.70)",
            inner_panel="rgba(255,255,255,0.06)",
        ),
    },
    # 1 — Obsidian Glass – 1,000,000 clicks  🖤
    {
        "id": "obsidian_glass",
        "name": "Obsidian Glass",
        "icon": "🖤",
        "gradient": ["#0A0A0A", "#111111", "#1A1A2E"],
        "unlock": ("total_clicks", 1_000_000),
        "unlock_desc": "Reach 1,000,000 total clicks",
        "palette": _p(
            base="rgba(18,18,18,0.80)",
            sidebar="rgba(8,8,8,0.85)",
            topbar="rgba(14,14,14,0.88)",
            hero="rgba(20,20,20,0.75)",
            config_card="rgba(16,16,16,0.82)",
            inner_panel="rgba(255,255,255,0.04)",
            card_border="rgba(255,255,255,0.08)",
            text_primary="#E0E0E0",
            text_secondary="rgba(200,200,200,0.65)",
            accent="rgba(180,180,200,{a})",
            accent_solid="#B4B4C8",
            logo_bg="rgba(40,40,40,0.50)",
            logo_border="rgba(80,80,80,0.40)",
            pill_bg="rgba(255,255,255,0.04)",
            pill_border="rgba(255,255,255,0.06)",
            pill_active_bg="rgba(180,180,200,0.15)",
            pill_active_border="rgba(180,180,200,0.25)",
            input_bg="rgba(0,0,0,0.35)",
            input_border="rgba(255,255,255,0.08)",
            combo_bg="#141414",
            combo_border="#222222",
            combo_list_bg="#0E0E0E",
            combo_sel_bg="#2A2A2A",
            toggle_bg="#141414",
            toggle_border="#222222",
            toggle_active_bg="#2A2A2A",
            toggle_active_border="#3A3A3A",
            slider_groove="rgba(255,255,255,0.08)",
            slider_handle="#888899",
            slider_sub="rgba(180,180,200,0.35)",
            checkbox_bg="#0E0E0E",
            checkbox_border="#2A2A2A",
            checkbox_checked="#555566",
            checkbox_checked_border="#666677",
            badge_bg="rgba(255,255,255,0.06)",
            badge_border="rgba(255,255,255,0.08)",
            start_btn_bg="rgba(180,180,200,0.15)",
            start_btn_border="rgba(180,180,200,0.25)",
            stop_btn_bg="rgba(255,70,70,0.18)",
            stop_btn_border="rgba(255,70,70,0.30)",
            running_color="#AAFFBB",
            stopped_color="#FF9999",
        ),
    },
    # 2 — Cyber Neon – 10,000 clicks
    {
        "id": "cyber_neon",
        "name": "Cyber Neon",
        "icon": "💜",
        "gradient": ["#0D001A", "#1A0033", "#FF00FF"],
        "unlock": ("total_clicks", 10_000),
        "unlock_desc": "Reach 10,000 total clicks",
        "palette": _p(
            base="rgba(20,0,40,0.65)",
            sidebar="rgba(12,0,28,0.78)",
            topbar="rgba(18,0,36,0.75)",
            hero="rgba(22,0,44,0.60)",
            config_card="rgba(18,0,38,0.72)",
            inner_panel="rgba(255,0,255,0.05)",
            card_border="rgba(255,0,255,0.12)",
            accent="rgba(255,0,255,{a})",
            accent_solid="#FF00FF",
            logo_bg="rgba(255,0,255,0.15)",
            logo_border="rgba(255,0,255,0.30)",
            pill_active_bg="rgba(255,0,255,0.15)",
            pill_active_border="rgba(255,0,255,0.25)",
            slider_handle="#FF00FF",
            slider_sub="rgba(255,0,255,0.40)",
            checkbox_checked="#7700AA",
            checkbox_checked_border="#9900CC",
            start_btn_bg="rgba(255,0,255,0.18)",
            start_btn_border="rgba(255,0,255,0.30)",
        ),
    },
    # 3 — Ocean Breeze – 100 clicks
    {
        "id": "ocean_breeze",
        "name": "Ocean Breeze",
        "icon": "🌊",
        "gradient": ["#001B2E", "#003355", "#00BFFF"],
        "unlock": ("total_clicks", 100),
        "unlock_desc": "Reach 100 total clicks",
        "palette": _p(
            base="rgba(0,30,55,0.60)",
            sidebar="rgba(0,20,42,0.75)",
            topbar="rgba(0,26,50,0.72)",
            hero="rgba(0,34,62,0.58)",
            config_card="rgba(0,28,52,0.68)",
            inner_panel="rgba(0,191,255,0.05)",
            card_border="rgba(0,191,255,0.10)",
            accent="rgba(0,191,255,{a})",
            accent_solid="#00BFFF",
            logo_bg="rgba(0,191,255,0.15)",
            logo_border="rgba(0,191,255,0.30)",
            pill_active_bg="rgba(0,191,255,0.18)",
            pill_active_border="rgba(0,191,255,0.28)",
            slider_handle="#00BFFF",
            slider_sub="rgba(0,191,255,0.45)",
            checkbox_checked="#0077AA",
            checkbox_checked_border="#0099CC",
            start_btn_bg="rgba(0,191,255,0.18)",
            start_btn_border="rgba(0,191,255,0.28)",
            running_color="#80FFD0",
        ),
    },
    # 4 — Crimson Flame – 100,000 clicks
    {
        "id": "crimson_flame",
        "name": "Crimson Flame",
        "icon": "🔥",
        "gradient": ["#1A0000", "#330A0A", "#FF2020"],
        "unlock": ("total_clicks", 100_000),
        "unlock_desc": "Reach 100,000 total clicks",
        "palette": _p(
            base="rgba(40,8,8,0.60)",
            sidebar="rgba(28,4,4,0.75)",
            topbar="rgba(35,6,6,0.72)",
            hero="rgba(45,10,10,0.58)",
            config_card="rgba(38,8,8,0.68)",
            inner_panel="rgba(255,40,40,0.05)",
            card_border="rgba(255,40,40,0.10)",
            accent="rgba(255,60,60,{a})",
            accent_solid="#FF3C3C",
            logo_bg="rgba(255,40,40,0.15)",
            logo_border="rgba(255,40,40,0.30)",
            pill_active_bg="rgba(255,60,60,0.18)",
            pill_active_border="rgba(255,60,60,0.28)",
            slider_handle="#FF3C3C",
            slider_sub="rgba(255,60,60,0.45)",
            checkbox_checked="#992020",
            checkbox_checked_border="#BB3030",
            start_btn_bg="rgba(255,60,60,0.18)",
            start_btn_border="rgba(255,60,60,0.28)",
            running_color="#FFCC80",
            stopped_color="#FF6666",
        ),
    },
    # 5 — Emerald Forest – 1,000 clicks
    {
        "id": "emerald_forest",
        "name": "Emerald Forest",
        "icon": "🌿",
        "gradient": ["#001A0D", "#003320", "#00CC66"],
        "unlock": ("total_clicks", 1_000),
        "unlock_desc": "Reach 1,000 total clicks",
        "palette": _p(
            base="rgba(0,30,16,0.60)",
            sidebar="rgba(0,22,10,0.75)",
            topbar="rgba(0,26,14,0.72)",
            hero="rgba(0,36,20,0.58)",
            config_card="rgba(0,28,16,0.68)",
            inner_panel="rgba(0,204,102,0.05)",
            card_border="rgba(0,204,102,0.10)",
            accent="rgba(0,204,102,{a})",
            accent_solid="#00CC66",
            logo_bg="rgba(0,204,102,0.15)",
            logo_border="rgba(0,204,102,0.30)",
            pill_active_bg="rgba(0,204,102,0.18)",
            pill_active_border="rgba(0,204,102,0.28)",
            slider_handle="#00CC66",
            slider_sub="rgba(0,204,102,0.45)",
            checkbox_checked="#007744",
            checkbox_checked_border="#009955",
            start_btn_bg="rgba(0,204,102,0.18)",
            start_btn_border="rgba(0,204,102,0.28)",
            running_color="#80FFB0",
            stopped_color="#FF8888",
        ),
    },
    # 6 — Golden Hour – 50 sessions
    {
        "id": "golden_hour",
        "name": "Golden Hour",
        "icon": "🌅",
        "gradient": ["#1A0F00", "#332200", "#FFAA00"],
        "unlock": ("total_sessions", 50),
        "unlock_desc": "Complete 50 sessions",
        "palette": _p(
            base="rgba(40,24,0,0.60)",
            sidebar="rgba(28,16,0,0.75)",
            topbar="rgba(35,20,0,0.72)",
            hero="rgba(48,28,0,0.58)",
            config_card="rgba(38,22,0,0.68)",
            inner_panel="rgba(255,170,0,0.05)",
            card_border="rgba(255,170,0,0.10)",
            accent="rgba(255,170,0,{a})",
            accent_solid="#FFAA00",
            logo_bg="rgba(255,170,0,0.15)",
            logo_border="rgba(255,170,0,0.30)",
            pill_active_bg="rgba(255,170,0,0.18)",
            pill_active_border="rgba(255,170,0,0.28)",
            slider_handle="#FFAA00",
            slider_sub="rgba(255,170,0,0.45)",
            checkbox_checked="#997700",
            checkbox_checked_border="#BB9900",
            start_btn_bg="rgba(255,170,0,0.18)",
            start_btn_border="rgba(255,170,0,0.28)",
            running_color="#FFEE88",
            stopped_color="#FF8888",
        ),
    },
    # 7 — Arctic Frost – 1 hour active time
    {
        "id": "arctic_frost",
        "name": "Arctic Frost",
        "icon": "❄️",
        "gradient": ["#0A1628", "#152844", "#88CCFF"],
        "unlock": ("total_session_time", 3600),
        "unlock_desc": "Spend 1 hour of active time",
        "palette": _p(
            base="rgba(16,30,60,0.55)",
            sidebar="rgba(10,20,48,0.72)",
            topbar="rgba(14,26,56,0.70)",
            hero="rgba(18,34,68,0.55)",
            config_card="rgba(14,28,56,0.65)",
            inner_panel="rgba(136,204,255,0.05)",
            card_border="rgba(136,204,255,0.10)",
            accent="rgba(136,204,255,{a})",
            accent_solid="#88CCFF",
            logo_bg="rgba(136,204,255,0.15)",
            logo_border="rgba(136,204,255,0.30)",
            pill_active_bg="rgba(136,204,255,0.18)",
            pill_active_border="rgba(136,204,255,0.28)",
            slider_handle="#88CCFF",
            slider_sub="rgba(136,204,255,0.45)",
            checkbox_checked="#4488AA",
            checkbox_checked_border="#55AACC",
            start_btn_bg="rgba(136,204,255,0.18)",
            start_btn_border="rgba(136,204,255,0.28)",
            running_color="#BBFFEE",
            stopped_color="#FFAAAA",
        ),
    },
    # 8 — Sunset Blaze – 7-day streak
    {
        "id": "sunset_blaze",
        "name": "Sunset Blaze",
        "icon": "🌇",
        "gradient": ["#1A0A1A", "#4A1040", "#FF6633"],
        "unlock": ("day_streak", 7),
        "unlock_desc": "Achieve a 7-day streak",
        "palette": _p(
            base="rgba(40,14,40,0.60)",
            sidebar="rgba(28,8,28,0.75)",
            topbar="rgba(35,12,35,0.72)",
            hero="rgba(50,16,50,0.55)",
            config_card="rgba(40,12,40,0.68)",
            inner_panel="rgba(255,102,51,0.05)",
            card_border="rgba(255,102,51,0.10)",
            accent="rgba(255,102,51,{a})",
            accent_solid="#FF6633",
            logo_bg="rgba(255,102,51,0.15)",
            logo_border="rgba(255,102,51,0.30)",
            pill_active_bg="rgba(255,102,51,0.18)",
            pill_active_border="rgba(255,102,51,0.28)",
            slider_handle="#FF6633",
            slider_sub="rgba(255,102,51,0.45)",
            checkbox_checked="#AA4422",
            checkbox_checked_border="#CC5533",
            start_btn_bg="rgba(255,102,51,0.18)",
            start_btn_border="rgba(255,102,51,0.28)",
            running_color="#FFDD88",
            stopped_color="#FF7777",
        ),
    },
    # 9 — Royal Amethyst – 10 hours active
    {
        "id": "royal_amethyst",
        "name": "Royal Amethyst",
        "icon": "💎",
        "gradient": ["#10001A", "#220044", "#9933FF"],
        "unlock": ("total_session_time", 36_000),
        "unlock_desc": "Spend 10 hours of active time",
        "palette": _p(
            base="rgba(24,0,44,0.60)",
            sidebar="rgba(16,0,30,0.75)",
            topbar="rgba(20,0,38,0.72)",
            hero="rgba(28,0,50,0.58)",
            config_card="rgba(22,0,42,0.68)",
            inner_panel="rgba(153,51,255,0.05)",
            card_border="rgba(153,51,255,0.10)",
            accent="rgba(153,51,255,{a})",
            accent_solid="#9933FF",
            logo_bg="rgba(153,51,255,0.15)",
            logo_border="rgba(153,51,255,0.30)",
            pill_active_bg="rgba(153,51,255,0.18)",
            pill_active_border="rgba(153,51,255,0.28)",
            slider_handle="#9933FF",
            slider_sub="rgba(153,51,255,0.45)",
            checkbox_checked="#6622AA",
            checkbox_checked_border="#7733CC",
            start_btn_bg="rgba(153,51,255,0.18)",
            start_btn_border="rgba(153,51,255,0.28)",
            running_color="#CCBBFF",
            stopped_color="#FFAAAA",
        ),
    },
    # 10 — Admin Override – admin panel only 🛡️
    {
        "id": "admin_override",
        "name": "Admin Override",
        "icon": "🛡️",
        "gradient": ["#0D0D0D", "#1A0A00", "#FF6600"],
        "unlock": ("admin_only", True),
        "unlock_desc": "Admin panel exclusive",
        "palette": _p(
            base="rgba(20,12,4,0.72)",
            sidebar="rgba(12,6,0,0.82)",
            topbar="rgba(16,10,2,0.80)",
            hero="rgba(24,14,4,0.65)",
            config_card="rgba(18,10,2,0.75)",
            inner_panel="rgba(255,102,0,0.06)",
            card_border="rgba(255,102,0,0.14)",
            text_primary="#FFE0C0",
            text_secondary="rgba(255,200,160,0.70)",
            accent="rgba(255,102,0,{a})",
            accent_solid="#FF6600",
            logo_bg="rgba(255,102,0,0.20)",
            logo_border="rgba(255,102,0,0.35)",
            pill_bg="rgba(255,102,0,0.06)",
            pill_border="rgba(255,102,0,0.10)",
            pill_active_bg="rgba(255,102,0,0.22)",
            pill_active_border="rgba(255,102,0,0.35)",
            input_bg="rgba(0,0,0,0.35)",
            input_border="rgba(255,102,0,0.12)",
            combo_bg="#1A0E02",
            combo_border="#2E1A08",
            combo_list_bg="#120A00",
            combo_sel_bg="#3A2010",
            toggle_bg="#1A0E02",
            toggle_border="#2E1A08",
            toggle_active_bg="#3A2010",
            toggle_active_border="#553018",
            slider_groove="rgba(255,102,0,0.12)",
            slider_handle="#FF6600",
            slider_sub="rgba(255,102,0,0.50)",
            checkbox_bg="#120A00",
            checkbox_border="#3A2010",
            checkbox_checked="#CC5500",
            checkbox_checked_border="#FF6600",
            badge_bg="rgba(255,102,0,0.10)",
            badge_border="rgba(255,102,0,0.18)",
            start_btn_bg="rgba(255,102,0,0.22)",
            start_btn_border="rgba(255,102,0,0.35)",
            stop_btn_bg="rgba(255,50,50,0.22)",
            stop_btn_border="rgba(255,50,50,0.35)",
            running_color="#FFCC66",
            stopped_color="#FF8866",
        ),
    },
    # 11 — Aurora Mint – 250,000 clicks
    {
        "id": "aurora_mint",
        "name": "Aurora Mint",
        "icon": "🧊",
        "gradient": ["#081A1A", "#0F2E2E", "#33FFCC"],
        "unlock": ("total_clicks", 250_000),
        "unlock_desc": "Reach 250,000 total clicks",
        "palette": _p(
            base="rgba(8,32,32,0.62)",
            sidebar="rgba(6,22,22,0.78)",
            topbar="rgba(8,28,28,0.74)",
            hero="rgba(10,36,36,0.58)",
            config_card="rgba(8,30,30,0.70)",
            inner_panel="rgba(51,255,204,0.06)",
            card_border="rgba(51,255,204,0.12)",
            accent="rgba(51,255,204,{a})",
            accent_solid="#33FFCC",
            logo_bg="rgba(51,255,204,0.18)",
            logo_border="rgba(51,255,204,0.32)",
            pill_active_bg="rgba(51,255,204,0.20)",
            pill_active_border="rgba(51,255,204,0.32)",
            slider_handle="#33FFCC",
            slider_sub="rgba(51,255,204,0.48)",
            checkbox_checked="#1CA88A",
            checkbox_checked_border="#28D6B0",
            start_btn_bg="rgba(51,255,204,0.22)",
            start_btn_border="rgba(51,255,204,0.35)",
            running_color="#A6FFE8",
            stopped_color="#FF9C9C",
        ),
    },
    # 12 — Desert Dune – 150 sessions
    {
        "id": "desert_dune",
        "name": "Desert Dune",
        "icon": "🏜️",
        "gradient": ["#1A1308", "#3A2A14", "#D9A35A"],
        "unlock": ("total_sessions", 150),
        "unlock_desc": "Complete 150 sessions",
        "palette": _p(
            base="rgba(42,30,14,0.62)",
            sidebar="rgba(30,20,8,0.78)",
            topbar="rgba(36,24,10,0.74)",
            hero="rgba(46,32,14,0.58)",
            config_card="rgba(40,28,12,0.70)",
            inner_panel="rgba(217,163,90,0.06)",
            card_border="rgba(217,163,90,0.12)",
            accent="rgba(217,163,90,{a})",
            accent_solid="#D9A35A",
            logo_bg="rgba(217,163,90,0.18)",
            logo_border="rgba(217,163,90,0.32)",
            pill_active_bg="rgba(217,163,90,0.20)",
            pill_active_border="rgba(217,163,90,0.32)",
            slider_handle="#D9A35A",
            slider_sub="rgba(217,163,90,0.48)",
            checkbox_checked="#9A6C2E",
            checkbox_checked_border="#BE8840",
            start_btn_bg="rgba(217,163,90,0.22)",
            start_btn_border="rgba(217,163,90,0.35)",
            running_color="#FFE0A8",
            stopped_color="#FF9C9C",
        ),
    },
    # 13 — Neon Lime – 14-day streak
    {
        "id": "neon_lime",
        "name": "Neon Lime",
        "icon": "🟢",
        "gradient": ["#0A1A06", "#13330C", "#9DFF00"],
        "unlock": ("day_streak", 14),
        "unlock_desc": "Achieve a 14-day streak",
        "palette": _p(
            base="rgba(16,38,10,0.62)",
            sidebar="rgba(10,26,6,0.78)",
            topbar="rgba(14,32,8,0.74)",
            hero="rgba(18,42,10,0.58)",
            config_card="rgba(14,34,8,0.70)",
            inner_panel="rgba(157,255,0,0.06)",
            card_border="rgba(157,255,0,0.12)",
            accent="rgba(157,255,0,{a})",
            accent_solid="#9DFF00",
            logo_bg="rgba(157,255,0,0.18)",
            logo_border="rgba(157,255,0,0.32)",
            pill_active_bg="rgba(157,255,0,0.20)",
            pill_active_border="rgba(157,255,0,0.32)",
            slider_handle="#9DFF00",
            slider_sub="rgba(157,255,0,0.48)",
            checkbox_checked="#6FAF00",
            checkbox_checked_border="#88D000",
            start_btn_bg="rgba(157,255,0,0.22)",
            start_btn_border="rgba(157,255,0,0.35)",
            running_color="#DEFFAA",
            stopped_color="#FF9C9C",
        ),
    },
    # 14 — Rose Quartz – 500,000 clicks
    {
        "id": "rose_quartz",
        "name": "Rose Quartz",
        "icon": "🌸",
        "gradient": ["#1A0C14", "#351628", "#FF7AB5"],
        "unlock": ("total_clicks", 500_000),
        "unlock_desc": "Reach 500,000 total clicks",
        "palette": _p(
            base="rgba(42,18,32,0.62)",
            sidebar="rgba(30,10,22,0.78)",
            topbar="rgba(36,14,26,0.74)",
            hero="rgba(46,18,34,0.58)",
            config_card="rgba(40,16,30,0.70)",
            inner_panel="rgba(255,122,181,0.06)",
            card_border="rgba(255,122,181,0.12)",
            accent="rgba(255,122,181,{a})",
            accent_solid="#FF7AB5",
            logo_bg="rgba(255,122,181,0.18)",
            logo_border="rgba(255,122,181,0.32)",
            pill_active_bg="rgba(255,122,181,0.20)",
            pill_active_border="rgba(255,122,181,0.32)",
            slider_handle="#FF7AB5",
            slider_sub="rgba(255,122,181,0.48)",
            checkbox_checked="#B84C80",
            checkbox_checked_border="#D86698",
            start_btn_bg="rgba(255,122,181,0.22)",
            start_btn_border="rgba(255,122,181,0.35)",
            running_color="#FFD1E6",
            stopped_color="#FF9C9C",
        ),
    },
    # 15 — Steel Night – 25 hours active
    {
        "id": "steel_night",
        "name": "Steel Night",
        "icon": "⚙️",
        "gradient": ["#0D121A", "#1A2433", "#5D7696"],
        "unlock": ("total_session_time", 90_000),
        "unlock_desc": "Spend 25 hours of active time",
        "palette": _p(
            base="rgba(20,28,40,0.62)",
            sidebar="rgba(14,20,30,0.78)",
            topbar="rgba(18,24,36,0.74)",
            hero="rgba(24,32,46,0.58)",
            config_card="rgba(20,28,42,0.70)",
            inner_panel="rgba(93,118,150,0.06)",
            card_border="rgba(93,118,150,0.12)",
            accent="rgba(93,118,150,{a})",
            accent_solid="#5D7696",
            logo_bg="rgba(93,118,150,0.18)",
            logo_border="rgba(93,118,150,0.32)",
            pill_active_bg="rgba(93,118,150,0.20)",
            pill_active_border="rgba(93,118,150,0.32)",
            slider_handle="#5D7696",
            slider_sub="rgba(93,118,150,0.48)",
            checkbox_checked="#49607A",
            checkbox_checked_border="#607E9F",
            start_btn_bg="rgba(93,118,150,0.22)",
            start_btn_border="rgba(93,118,150,0.35)",
            running_color="#D2E2F2",
            stopped_color="#FF9C9C",
        ),
    },
    # 16 — Liquid Glass – always unlocked
    {
        "id": "liquid_glass",
        "name": "Liquid Glass",
        "icon": "🫧",
        "gradient": ["#48DCE7F5", "#40C8D8ED", "#38BFD2EA"],
        "unlock": None,
        "unlock_desc": "Default unlocked",
        "palette": _p(
            base="rgba(248,252,255,0.36)",
            sidebar="rgba(238,246,255,0.44)",
            topbar="rgba(244,250,255,0.48)",
            hero="rgba(243,249,255,0.40)",
            config_card="rgba(246,251,255,0.42)",
            inner_panel="rgba(255,255,255,0.30)",
            card_border="rgba(255,255,255,0.66)",
            text_primary="#1F2A3A",
            text_secondary="rgba(31,42,58,0.72)",
            accent="rgba(64,132,214,{a})",
            accent_solid="#4084D6",
            logo_bg="rgba(255,255,255,0.46)",
            logo_border="rgba(255,255,255,0.72)",
            pill_bg="rgba(255,255,255,0.34)",
            pill_border="rgba(255,255,255,0.64)",
            pill_active_bg="rgba(86,150,230,0.22)",
            pill_active_border="rgba(86,150,230,0.42)",
            input_bg="rgba(255,255,255,0.40)",
            input_border="rgba(190,211,236,0.72)",
            combo_bg="#F5FAFF",
            combo_border="#C2D8F0",
            combo_list_bg="#EEF6FF",
            combo_sel_bg="#D9E9FB",
            toggle_bg="#F3F9FF",
            toggle_border="#C2D8F0",
            toggle_active_bg="#DEEDFF",
            toggle_active_border="#9CC3ED",
            slider_groove="rgba(96,132,176,0.24)",
            slider_handle="#4F8FD8",
            slider_sub="rgba(79,143,216,0.38)",
            checkbox_bg="#F2F8FF",
            checkbox_border="#BFD7F2",
            checkbox_checked="#5B9BE0",
            checkbox_checked_border="#3E7FC6",
            badge_bg="rgba(255,255,255,0.36)",
            badge_border="rgba(188,210,236,0.74)",
            start_btn_bg="rgba(79,143,216,0.20)",
            start_btn_border="rgba(79,143,216,0.35)",
            stop_btn_bg="rgba(235,110,110,0.18)",
            stop_btn_border="rgba(215,80,80,0.30)",
            running_color="#2F8A56",
            stopped_color="#C85050",
        ),
    },
]

# ─── Prime Autoclicker bonus themes ─────────────────────────
# Unlocked via Prime Autoclicker stats and achievements.

PRIME_BONUS_THEMES: list[dict] = [
    # Prime-1 — Emerald Field – 250 sessions
    {
        "id": "emerald_field",
        "name": "Emerald Field",
        "icon": "🌿",
        "gradient": ["#00180A", "#003015", "#00A84A"],
        "unlock": ("total_sessions", 250),
        "unlock_desc": "Complete 250 sessions in Prime Autoclicker",
        "palette": _p(
            base="rgba(0,28,12,0.62)",
            sidebar="rgba(0,18,8,0.78)",
            topbar="rgba(0,24,10,0.74)",
            hero="rgba(0,34,16,0.58)",
            config_card="rgba(0,26,12,0.70)",
            inner_panel="rgba(0,168,74,0.06)",
            card_border="rgba(0,168,74,0.12)",
            accent="rgba(0,200,90,{a})",
            accent_solid="#00C85A",
            logo_bg="rgba(0,168,74,0.18)",
            logo_border="rgba(0,168,74,0.32)",
            pill_active_bg="rgba(0,168,74,0.20)",
            pill_active_border="rgba(0,168,74,0.32)",
            slider_handle="#00A84A",
            slider_sub="rgba(0,168,74,0.48)",
            checkbox_checked="#006B2E",
            checkbox_checked_border="#009940",
            start_btn_bg="rgba(0,168,74,0.22)",
            start_btn_border="rgba(0,168,74,0.35)",
            running_color="#7DEFA1",
            stopped_color="#FF8888",
        ),
    },
    # Prime-2 — Crimson Harvest – 2,500,000 clicks
    {
        "id": "crimson_harvest",
        "name": "Crimson Harvest",
        "icon": "🍎",
        "gradient": ["#1A0005", "#350010", "#CC1040"],
        "unlock": ("total_clicks", 2_500_000),
        "unlock_desc": "Reach 2,500,000 total clicks in Prime Autoclicker",
        "palette": _p(
            base="rgba(36,4,10,0.62)",
            sidebar="rgba(24,2,6,0.78)",
            topbar="rgba(32,4,10,0.74)",
            hero="rgba(42,6,14,0.58)",
            config_card="rgba(34,4,10,0.70)",
            inner_panel="rgba(204,16,64,0.06)",
            card_border="rgba(204,16,64,0.12)",
            accent="rgba(210,30,70,{a})",
            accent_solid="#D21E46",
            logo_bg="rgba(204,16,64,0.18)",
            logo_border="rgba(204,16,64,0.32)",
            pill_active_bg="rgba(204,16,64,0.20)",
            pill_active_border="rgba(204,16,64,0.32)",
            slider_handle="#CC1040",
            slider_sub="rgba(204,16,64,0.48)",
            checkbox_checked="#8A0022",
            checkbox_checked_border="#BB0032",
            start_btn_bg="rgba(204,16,64,0.22)",
            start_btn_border="rgba(204,16,64,0.35)",
            running_color="#FFAACC",
            stopped_color="#FF6666",
        ),
    },
    # Prime-3 — Midnight Field – 24 hours active
    {
        "id": "midnight_field",
        "name": "Midnight Field",
        "icon": "🌙",
        "gradient": ["#020510", "#060C22", "#2A3480"],
        "unlock": ("total_session_time", 86_400),
        "unlock_desc": "Spend 24 hours clicking in Prime Autoclicker",
        "palette": _p(
            base="rgba(8,12,36,0.62)",
            sidebar="rgba(4,8,24,0.78)",
            topbar="rgba(6,10,30,0.74)",
            hero="rgba(10,16,44,0.58)",
            config_card="rgba(8,12,36,0.70)",
            inner_panel="rgba(42,52,128,0.06)",
            card_border="rgba(42,52,128,0.12)",
            accent="rgba(80,100,220,{a})",
            accent_solid="#5064DC",
            logo_bg="rgba(42,52,128,0.18)",
            logo_border="rgba(42,52,128,0.32)",
            pill_active_bg="rgba(42,52,128,0.20)",
            pill_active_border="rgba(42,52,128,0.32)",
            slider_handle="#2A3480",
            slider_sub="rgba(42,52,128,0.48)",
            checkbox_checked="#1A2260",
            checkbox_checked_border="#283088",
            start_btn_bg="rgba(42,52,128,0.22)",
            start_btn_border="rgba(42,52,128,0.35)",
            running_color="#AABBFF",
            stopped_color="#FFAAAA",
        ),
    },
    # Prime-4 — Rainbow Harvest – 100-day streak
    {
        "id": "rainbow_harvest",
        "name": "Rainbow Harvest",
        "icon": "🌈",
        "gradient": ["#100018", "#1A0028", "#9933CC"],
        "unlock": ("day_streak", 100),
        "unlock_desc": "Maintain a 100-day click streak in Prime Autoclicker",
        "palette": _p(
            base="rgba(22,4,40,0.62)",
            sidebar="rgba(14,2,28,0.78)",
            topbar="rgba(18,4,34,0.74)",
            hero="rgba(28,6,50,0.58)",
            config_card="rgba(20,4,38,0.70)",
            inner_panel="rgba(153,51,204,0.06)",
            card_border="rgba(153,51,204,0.12)",
            accent="rgba(170,60,220,{a})",
            accent_solid="#AA3CDC",
            logo_bg="rgba(153,51,204,0.18)",
            logo_border="rgba(153,51,204,0.32)",
            pill_active_bg="rgba(153,51,204,0.20)",
            pill_active_border="rgba(153,51,204,0.32)",
            slider_handle="#9933CC",
            slider_sub="rgba(153,51,204,0.48)",
            checkbox_checked="#661488",
            checkbox_checked_border="#8820AA",
            start_btn_bg="rgba(153,51,204,0.22)",
            start_btn_border="rgba(153,51,204,0.35)",
            running_color="#DDAAFF",
            stopped_color="#FFAAAA",
        ),
    },
    # Prime-5 — Royal Hyperion – 75+ achievements
    {
        "id": "royal_hyperion",
        "name": "Royal Hyperion",
        "icon": "👑",
        "gradient": ["#0C0800", "#1E1600", "#CCAA00"],
        "unlock": ("achievements_unlocked", 75),
        "unlock_desc": "Unlock 75+ Prime Autoclicker achievements",
        "palette": _p(
            base="rgba(30,22,0,0.62)",
            sidebar="rgba(20,14,0,0.78)",
            topbar="rgba(26,18,0,0.74)",
            hero="rgba(36,26,0,0.58)",
            config_card="rgba(28,20,0,0.70)",
            inner_panel="rgba(204,170,0,0.06)",
            card_border="rgba(204,170,0,0.12)",
            text_primary="#FFF0B0",
            text_secondary="rgba(255,230,150,0.72)",
            accent="rgba(220,185,0,{a})",
            accent_solid="#DCB900",
            logo_bg="rgba(204,170,0,0.20)",
            logo_border="rgba(204,170,0,0.36)",
            pill_active_bg="rgba(204,170,0,0.22)",
            pill_active_border="rgba(204,170,0,0.36)",
            slider_handle="#CCAA00",
            slider_sub="rgba(204,170,0,0.50)",
            checkbox_checked="#886600",
            checkbox_checked_border="#AA8800",
            start_btn_bg="rgba(204,170,0,0.24)",
            start_btn_border="rgba(204,170,0,0.40)",
            running_color="#FFEE66",
            stopped_color="#FF8866",
        ),
    },
]

THEMES.extend(PRIME_BONUS_THEMES)

THEME_MAP: dict[str, dict] = {t["id"]: t for t in THEMES}

# Per-theme typography profiles.
THEME_FONT_MAP: dict[str, str] = {
    "default": "'Segoe UI', 'Trebuchet MS', sans-serif",
    "obsidian_glass": "Consolas, 'Segoe UI', monospace",
    "cyber_neon": "Bahnschrift, 'Segoe UI', sans-serif",
    "ocean_breeze": "'Trebuchet MS', 'Segoe UI', sans-serif",
    "crimson_flame": "'Franklin Gothic Medium', 'Segoe UI', sans-serif",
    "emerald_forest": "Candara, 'Segoe UI', sans-serif",
    "golden_hour": "Georgia, 'Times New Roman', serif",
    "arctic_frost": "Calibri, 'Segoe UI', sans-serif",
    "sunset_blaze": "Verdana, 'Segoe UI', sans-serif",
    "royal_amethyst": "'Palatino Linotype', 'Segoe UI', serif",
    "admin_override": "'Arial Black', 'Segoe UI', sans-serif",
    "aurora_mint": "Corbel, 'Segoe UI', sans-serif",
    "desert_dune": "'Book Antiqua', Georgia, serif",
    "neon_lime": "Bahnschrift, 'Segoe UI', sans-serif",
    "rose_quartz": "Cambria, 'Segoe UI', serif",
    "steel_night": "'Segoe UI Semibold', 'Segoe UI', sans-serif",
    "liquid_glass": "'Segoe UI Variable Text', 'Segoe UI', sans-serif",
    "emerald_field": "Candara, 'Segoe UI', sans-serif",
    "crimson_harvest": "'Franklin Gothic Book', 'Segoe UI', sans-serif",
    "midnight_field": "Consolas, 'Segoe UI', monospace",
    "rainbow_harvest": "'Century Gothic', 'Segoe UI', sans-serif",
    "royal_hyperion": "Garamond, Georgia, serif",
}


# ─── Persistence ──────────────────────────────────────────────

_THEME_PREFS_CACHE: dict | None = None

def _load_theme_prefs() -> dict:
    global _THEME_PREFS_CACHE
    if _THEME_PREFS_CACHE is not None:
        return dict(_THEME_PREFS_CACHE)
    try:
        with open(THEME_FILE, "r") as f:
            data = json.load(f)
            _THEME_PREFS_CACHE = dict(data)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        _THEME_PREFS_CACHE = {}
        return {}


def _save_theme_prefs(data: dict):
    global _THEME_PREFS_CACHE
    try:
        with open(THEME_FILE, "w") as f:
            json.dump(data, f, indent=2)
        _THEME_PREFS_CACHE = dict(data)
    except Exception:
        pass


def get_selected_theme_id() -> str:
    return _load_theme_prefs().get("selected", "default")


def set_selected_theme_id(theme_id: str):
    d = _load_theme_prefs()
    d["selected"] = theme_id
    _save_theme_prefs(d)


def get_unlocked_ids() -> set[str]:
    """Return the set of explicitly unlocked theme IDs (default is always included)."""
    d = _load_theme_prefs()
    unlocked = set(d.get("unlocked", []))
    unlocked.add("default")
    return unlocked


def mark_unlocked(theme_id: str):
    d = _load_theme_prefs()
    unlocked = set(d.get("unlocked", []))
    unlocked.add(theme_id)
    d["unlocked"] = list(unlocked)
    _save_theme_prefs(d)


def is_theme_unlocked(theme_id: str, stats) -> bool:
    """Check if a theme is unlocked either via persistence or live stats."""
    if theme_id == "default":
        return True
    # Already explicitly unlocked
    if theme_id in get_unlocked_ids():
        return True
    # Check live stats
    theme = THEME_MAP.get(theme_id)
    if not theme or theme["unlock"] is None:
        return True
    req_type, req_val = theme["unlock"]
    if req_type == "total_clicks":
        return stats.total_clicks >= req_val
    if req_type == "total_sessions":
        return stats.total_sessions >= req_val
    if req_type == "total_session_time":
        return stats.total_session_time >= req_val
    if req_type == "day_streak":
        daily = stats._data.get("daily", {})
        return stats._has_day_streak(daily, req_val)
    if req_type == "achievements_unlocked":
        earned = sum(1 for _icon, _name, unlocked in stats.get_achievements() if unlocked)
        return earned >= req_val
    if req_type == "admin_only":
        return False
    return False


def check_and_unlock_all(stats) -> list[str]:
    """Check all themes against stats and unlock any newly earned.
    Returns list of newly unlocked theme IDs."""
    newly = []
    already = get_unlocked_ids()
    for t in THEMES:
        tid = t["id"]
        if tid in already:
            continue
        if is_theme_unlocked(tid, stats):
            mark_unlocked(tid)
            newly.append(tid)
    return newly


def get_theme(theme_id: str | None = None) -> dict:
    """Return the full theme dict. Falls back to default."""
    if theme_id is None:
        theme_id = get_selected_theme_id()
    return THEME_MAP.get(theme_id, THEMES[0])


def get_theme_font(theme_id: str | None = None) -> str:
    """Return the preferred font stack for the theme ID."""
    if theme_id is None:
        theme_id = get_selected_theme_id()
    return THEME_FONT_MAP.get(theme_id, THEME_FONT_MAP["default"])


# ─── Dialog / popup stylesheet helpers ─────────────────────────
def _accent_with_alpha(accent_tpl: str, alpha: float) -> str:
    """Fill the ``{a}`` placeholder in an accent template like ``rgba(78,141,255,{a})``."""
    return accent_tpl.replace("{a}", f"{alpha:.2f}")


def _ensure_css_alpha(color: str, min_alpha: float) -> str:
    """Ensure a CSS colour has at least *min_alpha* opacity.

    Supports ``rgba(...)``, ``#RRGGBB``, and ``#AARRGGBB``.
    """
    c = (color or "").strip()
    if not c:
        return color
    m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)", c, flags=re.I)
    if m:
        r, g, b = m.group(1), m.group(2), m.group(3)
        a = max(float(m.group(4)), float(min_alpha))
        return f"rgba({r},{g},{b},{a:.2f})"
    if c.startswith("#") and len(c) == 9:
        try:
            a = int(c[1:3], 16) / 255.0
            if a >= min_alpha:
                return c
            new_a = int(round(min(1.0, max(min_alpha, 0.0)) * 255))
            return f"#{new_a:02X}{c[3:]}"
        except Exception:
            return c
    if c.startswith("#") and len(c) == 7:
        try:
            r = int(c[1:3], 16)
            g = int(c[3:5], 16)
            b = int(c[5:7], 16)
            return f"rgba({r},{g},{b},{min_alpha:.2f})"
        except Exception:
            return c
    return c


def get_dialog_stylesheet(theme: dict | None = None, *, warning: bool = False) -> str:
    """Return a stylesheet for a themed popup dialog.

    Parameters
    ----------
    theme : dict or None
        A theme dict (from *get_theme()*).  ``None`` → current theme.
    warning : bool
        When True the accent colours are swapped for red/warning tones.
    """
    if theme is None:
        theme = get_theme()
    p = theme["palette"]
    g = theme["gradient"]

    bg = _ensure_css_alpha(p.get("config_card", g[0]), 0.88)
    text = p["text_primary"]
    text_sec = p["text_secondary"]
    inp_bg = _ensure_css_alpha(p["input_bg"], 0.72)
    inp_bdr = p["input_border"]
    card_bdr = p["card_border"]

    if warning:
        btn_bg = p["stop_btn_bg"]
        btn_bdr = p["stop_btn_border"]
        acc_focus = p.get("stopped_color", "#FF9C9C")
        acc_solid = p.get("stopped_color", "#FF9C9C")
    else:
        btn_bg = p["start_btn_bg"]
        btn_bdr = p["start_btn_border"]
        acc_focus = _accent_with_alpha(p["accent"], 0.50)
        acc_solid = p["accent_solid"]

    cancel_bg = _ensure_css_alpha(p["pill_bg"], 0.70)
    cancel_bdr = p["pill_border"]

    return (
        f"QDialog {{ background: {bg}; border: 1px solid {card_bdr}; border-radius: 14px; }}"
        f"QLabel {{ color: {text}; font-size: 13px; background: transparent; }}"
        f"QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{"
        f"  background: {inp_bg}; border: 1px solid {inp_bdr};"
        f"  border-radius: 10px; padding: 8px 12px; color: {text}; font-size: 13px; }}"
        f"QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {acc_focus}; }}"
        f"QPushButton {{"
        f"  background: {btn_bg}; border: 1px solid {btn_bdr};"
        f"  border-radius: 10px; padding: 8px 18px; color: {text};"
        f"  font-weight: 700; font-size: 13px; }}"
        f"QPushButton:hover {{ background: {btn_bdr}; }}"
        f"QPushButton#CancelBtn {{ background: {cancel_bg}; border: 1px solid {cancel_bdr}; }}"
        f"QPushButton#CancelBtn:hover {{ background: {cancel_bdr}; }}"
        f"QCheckBox {{ color: {text}; }}"
        f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;"
        f"  background: {p['checkbox_bg']}; border: 1px solid {p['checkbox_border']}; }}"
        f"QCheckBox::indicator:checked {{ background: {p['checkbox_checked']};"
        f"  border: 1px solid {p['checkbox_checked_border']}; }}"
    )


def get_glass_dialog_stylesheet(theme: dict | None = None) -> str:
    """Return a stylesheet for the GlassDialog base (sidebar Settings/Logs).

    Uses the theme gradient for the glass card instead of hardcoded purple.
    """
    if theme is None:
        theme = get_theme()
    p = theme["palette"]
    g = theme["gradient"]

    text = p["text_primary"]
    inp_bg = p["input_bg"]
    inp_bdr = p["input_border"]
    card_bdr = p["card_border"]
    pill_bg = p["pill_bg"]
    pill_bdr = p["pill_border"]

    return (
        f"QFrame#glassCard{{"
        f"  border-radius:18px;"
        f"  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
        f"    stop:0 {g[0]}, stop:0.5 {g[2]}, stop:1 {g[1]});"
        f"  border:1px solid {card_bdr};"
        f"}}"
        f"QLabel, QCheckBox, QRadioButton {{ color:{text}; }}"
        f"QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{"
        f"  color:{text}; background:{inp_bg};"
        f"  border:1px solid {inp_bdr}; border-radius:8px; padding:6px 8px;"
        f"}}"
        f"QPushButton{{"
        f"  color:{text}; border-radius:10px; padding:8px 12px;"
        f"  background:{pill_bg}; border:1px solid {pill_bdr};"
        f"}}"
        f"QPushButton:hover{{ background:{p['pill_active_bg']}; }}"
        f"QGroupBox{{ color:{text}; border:1px solid {card_bdr};"
        f"  border-radius:12px; margin-top:12px; }}"
        f"QGroupBox::title{{ subcontrol-origin:margin; left:12px; padding:0 4px; }}"
        f"QTabWidget::pane{{"
        f"  border:1px solid {card_bdr}; border-radius:12px;"
        f"  background:{pill_bg};"
        f"}}"
        f"QTabBar::tab{{"
        f"  color:{text}; padding:6px 12px; margin:3px;"
        f"  border:1px solid {card_bdr}; border-radius:8px;"
        f"  background:{pill_bg};"
        f"}}"
        f"QTabBar::tab:selected{{ background:{p['pill_active_bg']}; }}"
    )


def get_pick_dialog_stylesheet(theme: dict | None = None) -> str:
    """Stylesheet for the small frameless position-picker popup."""
    if theme is None:
        theme = get_theme()
    p = theme["palette"]
    g = theme["gradient"]
    text = p["text_primary"]
    return (
        f"QFrame{{border-radius:12px; background:{g[0]};"
        f"border:1px solid {p['card_border']};}}"
        f"QLabel{{color:{text};}}"
    )
