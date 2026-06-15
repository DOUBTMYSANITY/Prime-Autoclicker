"""Timing humanization for the click engine (Input Humanization plugin)."""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class HumanizationSettings:
    enabled: bool = False
    jitter_min_ms: int = 2
    jitter_max_ms: int = 12
    micro_pause_every: int = 35
    micro_pause_ms: int = 45
    fatigue_curve: str = "soft"

    @classmethod
    def from_dict(cls, data: dict | None) -> HumanizationSettings:
        data = data or {}
        return cls(
            enabled=bool(data.get("enabled", False)),
            jitter_min_ms=max(0, int(data.get("jitter_min_ms", 2))),
            jitter_max_ms=max(0, int(data.get("jitter_max_ms", 12))),
            micro_pause_every=max(1, int(data.get("micro_pause_every", 35))),
            micro_pause_ms=max(0, int(data.get("micro_pause_ms", 45))),
            fatigue_curve=str(data.get("fatigue_curve", "soft")).strip().lower() or "soft",
        )


def extra_delay_seconds(settings: HumanizationSettings, click_index: int) -> float:
    """Return additional delay (seconds) before the next click."""
    if not settings.enabled or click_index < 1:
        return 0.0

    lo = min(settings.jitter_min_ms, settings.jitter_max_ms)
    hi = max(settings.jitter_min_ms, settings.jitter_max_ms)
    jitter_ms = random.randint(lo, hi) if hi > 0 else 0

    fatigue_factor = 1.0
    if settings.fatigue_curve == "linear":
        fatigue_factor = 1.0 + min(click_index, 500) * 0.001
    elif settings.fatigue_curve == "aggressive":
        fatigue_factor = 1.0 + min(click_index, 300) * 0.003

    pause_ms = 0
    if settings.micro_pause_every > 0 and click_index % settings.micro_pause_every == 0:
        pause_ms = settings.micro_pause_ms

    total_ms = (jitter_ms * fatigue_factor) + pause_ms
    return max(0.0, total_ms / 1000.0)
