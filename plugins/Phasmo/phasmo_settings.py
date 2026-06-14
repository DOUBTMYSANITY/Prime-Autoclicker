"""Persistent Phasmophobia plugin settings."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parent / "data" / "phasmo_settings.json"

TIMER_STYLE_PRESETS = {
    "Minimal": {"radius": 10, "opacity": 0.88, "font_pt": 20, "border": 2},
    "Bold": {"radius": 14, "opacity": 0.95, "font_pt": 24, "border": 3},
    "Glow": {"radius": 16, "opacity": 0.82, "font_pt": 22, "border": 2},
    "Monospace": {"radius": 8, "opacity": 0.92, "font_pt": 18, "border": 1},
}


@dataclass
class TimerStyleConfig:
    title: str
    color: str
    preset: str = "Minimal"
    radius: int = 10
    opacity: float = 0.88
    font_pt: int = 20
    border: int = 2
    width: int = 168


@dataclass
class PhasmoSettings:
    overlay_smudge: bool = True
    overlay_crucifix: bool = True
    overlay_obambo: bool = True
    overlay_bpm: bool = True
    smudge: TimerStyleConfig = field(
        default_factory=lambda: TimerStyleConfig("Smudge Timer", "#22c55e")
    )
    crucifix: TimerStyleConfig = field(
        default_factory=lambda: TimerStyleConfig("Crucifix Timer", "#ef4444")
    )
    obambo: TimerStyleConfig = field(
        default_factory=lambda: TimerStyleConfig("Obambo Timer", "#eab308", width=180)
    )
    bpm_color: str = "#3b82f6"
    bpm_opacity: float = 0.92
    bpm_radius: int = 10
    compact_radius: int = 16
    forced_evidence_count: int = 3
    nightmare_mode: bool = False
    brightness_enabled: bool = False
    brightness_level: int = 100
    gamma_enabled: bool = False
    gamma_level: int = 60


def _timer_from_dict(data: dict, default: TimerStyleConfig) -> TimerStyleConfig:
    if not isinstance(data, dict):
        return default
    return TimerStyleConfig(
        title=str(data.get("title", default.title)),
        color=str(data.get("color", default.color)),
        preset=str(data.get("preset", default.preset)),
        radius=int(data.get("radius", default.radius)),
        opacity=float(data.get("opacity", default.opacity)),
        font_pt=int(data.get("font_pt", default.font_pt)),
        border=int(data.get("border", default.border)),
        width=int(data.get("width", default.width)),
    )


def load_settings() -> PhasmoSettings:
    defaults = PhasmoSettings()
    if not SETTINGS_PATH.is_file():
        return defaults
    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(raw, dict):
        return defaults
    return PhasmoSettings(
        overlay_smudge=bool(raw.get("overlay_smudge", defaults.overlay_smudge)),
        overlay_crucifix=bool(raw.get("overlay_crucifix", defaults.overlay_crucifix)),
        overlay_obambo=bool(raw.get("overlay_obambo", defaults.overlay_obambo)),
        overlay_bpm=bool(raw.get("overlay_bpm", defaults.overlay_bpm)),
        smudge=_timer_from_dict(raw.get("smudge", {}), defaults.smudge),
        crucifix=_timer_from_dict(raw.get("crucifix", {}), defaults.crucifix),
        obambo=_timer_from_dict(raw.get("obambo", {}), defaults.obambo),
        bpm_color=str(raw.get("bpm_color", defaults.bpm_color)),
        bpm_opacity=float(raw.get("bpm_opacity", defaults.bpm_opacity)),
        bpm_radius=int(raw.get("bpm_radius", defaults.bpm_radius)),
        compact_radius=int(raw.get("compact_radius", defaults.compact_radius)),
        forced_evidence_count=int(raw.get("forced_evidence_count", defaults.forced_evidence_count)),
        nightmare_mode=bool(raw.get("nightmare_mode", defaults.nightmare_mode)),
        brightness_enabled=bool(raw.get("brightness_enabled", defaults.brightness_enabled)),
        brightness_level=int(raw.get("brightness_level", defaults.brightness_level)),
        gamma_enabled=bool(raw.get("gamma_enabled", defaults.gamma_enabled)),
        gamma_level=int(raw.get("gamma_level", defaults.gamma_level)),
    )


def save_settings(settings: PhasmoSettings) -> None:
    SETTINGS_PATH.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
