"""Canonical Phasmophobia hunt footstep speeds for BPM matching.

Sources: Phasmophobia Wiki (Hunt page), Kinetic Games patch notes, zero-network
cheat sheet BPM buckets. Most variable ghosts use discrete tiers only — wide
min–max strings on ghost cards caused false positives (e.g. Deogen 0.4–3.0
matching 1.7). Thaye and Hantu are exceptions: their hunt speed changes
continuously within a documented range as they age / as room temperature shifts.
"""
from __future__ import annotations

from dataclasses import dataclass

# Standard ghosts: only 1.7 m/s base (no unique speed tier besides LOS boost).
STANDARD_SPEED_GHOSTS: frozenset[str] = frozenset({
    "Banshee",
    "Demon",
    "Goryo",
    "Mare",
    "Myling",
    "Obake",
    "Oni",
    "Onryo",
    "Phantom",
    "Poltergeist",
    "Shade",
    "Spirit",
    "Wraith",
    "Yokai",
    "Yurei",
})

# Measured speed (m/s) -> ghosts that have this as a DISTINCT identifiable tier.
# Ghosts not listed at a speed do not match that speed.
GHOST_SPEEDS: dict[str, tuple[float, ...]] = {
    # Standard 1.7 only
    **{name: (1.7,) for name in STANDARD_SPEED_GHOSTS},
    # Unique / variable profiles (wiki + 2025–2026 guides)
    "Aswang": (1.53, 2.53),  # base 1.53; LOS acceleration up to 2.53 m/s
    "Dayan": (1.2, 1.7, 2.25),  # slows when players still; 1.7 base; 2.25 when moving
    "Deogen": (0.4, 3.0),  # 0.4 within 2.5m; 3.0 beyond 6m — never 1.7
    "Gallu": (1.36, 1.7, 1.96),  # weakened / normal / enraged tiers
    "Jinn": (1.7, 2.5),  # 2.5 with breaker on + LOS + distance >3m
    "Kormos": (1.7, 2.21, 3.65),  # pseudo-LOS tiers; up to ~3.65 m/s when accelerating
    "Moroi": (1.5, 1.575, 1.65, 1.7, 1.725, 1.8, 1.875, 1.95, 2.025, 2.1, 2.175, 2.25, 3.71),
    "Obambo": (1.45, 1.96),  # calm / aggressive (+20% over 1.7 ≈ 1.96)
    "Raiju": (1.7, 2.5),  # 2.5 within 6m of active electronics
    "Revenant": (1.0, 3.0),  # 1.0 idle; 3.0 when chasing — never 1.7
    "The Twins": (1.5, 1.9),  # main 1.5 m/s; decoy 1.9 m/s
    # Mimic copies others — excluded from automatic BPM match
}

# Ghosts whose hunt speed can be any value within [min, max] (not just endpoints).
GHOST_SPEED_RANGES: dict[str, tuple[float, float]] = {
    "Thaye": (1.0, 2.75),  # starts fast when young, slows each age step
    "Hantu": (1.4, 2.7),   # coldest room → warmest room
}

# Speeds shared by many ghosts — matching here is low confidence alone.
BUCKET_STANDARD = 1.7

# Match tolerance in m/s (~±3 BPM at 100% lobby speed).
MATCH_TOLERANCE = 0.07

# Tighter tolerance for unique single-tier speeds.
STRICT_TOLERANCE = 0.055


@dataclass(frozen=True)
class SpeedMatch:
    ghost: str
    speed: float
    distance: float
    is_standard_only: bool
    is_unique_tier: bool
    is_range_match: bool = False


def _speed_in_range(speed_mps: float, lo: float, hi: float) -> bool:
    return (lo - MATCH_TOLERANCE) <= speed_mps <= (hi + MATCH_TOLERANCE)


def _ghost_matches_discrete_tier(ghost: str, speed_mps: float) -> tuple[float, float] | None:
    """Return (matched_tier, distance) if ghost has a discrete tier near speed_mps."""
    speeds = GHOST_SPEEDS.get(ghost, ())
    best_dist = None
    best_tier = None
    for tier in speeds:
        tol = STRICT_TOLERANCE if len(speeds) == 1 else MATCH_TOLERANCE
        dist = abs(tier - speed_mps)
        if dist <= tol and (best_dist is None or dist < best_dist):
            best_dist = dist
            best_tier = tier
    if best_dist is None or best_tier is None:
        return None
    return best_tier, best_dist


def _count_tier_holders(tier: float) -> int:
    count = 0
    for ghost, speeds in GHOST_SPEEDS.items():
        if any(abs(t - tier) <= MATCH_TOLERANCE for t in speeds):
            count += 1
    for ghost, (lo, hi) in GHOST_SPEED_RANGES.items():
        if _speed_in_range(tier, lo, hi):
            count += 1
    return count


def _ghosts_at_speed(speed_mps: float) -> list[SpeedMatch]:
    """Return ghosts whose canonical speed list or range includes speed_mps."""
    results: list[SpeedMatch] = []
    seen: set[str] = set()

    for ghost, speeds in GHOST_SPEEDS.items():
        hit = _ghost_matches_discrete_tier(ghost, speed_mps)
        if hit is None:
            continue
        best_tier, best_dist = hit
        is_std = ghost in STANDARD_SPEED_GHOSTS
        holders = _count_tier_holders(best_tier)
        results.append(
            SpeedMatch(
                ghost=ghost,
                speed=best_tier,
                distance=best_dist,
                is_standard_only=is_std,
                is_unique_tier=holders <= 2 and not is_std,
            )
        )
        seen.add(ghost)

    for ghost, (lo, hi) in GHOST_SPEED_RANGES.items():
        if not _speed_in_range(speed_mps, lo, hi):
            continue
        if ghost in seen:
            # Replace discrete tier hit with continuous range (e.g. Hantu temperature).
            results = [m for m in results if m.ghost != ghost]
            seen.discard(ghost)
        # Interior range speeds are never "unique" — many ghosts can overlap.
        mid = (lo + hi) / 2.0
        dist = min(abs(speed_mps - lo), abs(speed_mps - hi), abs(speed_mps - mid))
        results.append(
            SpeedMatch(
                ghost=ghost,
                speed=speed_mps,
                distance=dist,
                is_standard_only=False,
                is_unique_tier=False,
                is_range_match=True,
            )
        )

    results.sort(key=lambda m: (not m.is_unique_tier, m.is_range_match, m.distance, m.ghost))
    return results


def format_speed_matches(speed_mps: float) -> tuple[str, list[str]]:
    """Build UI label and ghost name list for a measured speed."""
    if speed_mps <= 0:
        return "Tap F on each footstep", []

    matches = _ghosts_at_speed(speed_mps)
    if not matches:
        return f"No ghost tier @ {speed_mps:.2f} m/s", []

    unique = [m for m in matches if m.is_unique_tier]
    standard = [m for m in matches if m.is_standard_only]
    variable = [m for m in matches if not m.is_standard_only and not m.is_unique_tier]

    parts: list[str] = []
    names: list[str] = []

    if unique:
        u_names = [m.ghost for m in unique]
        parts.append(f"Likely: {', '.join(u_names)}")
        names.extend(u_names)

    if abs(speed_mps - BUCKET_STANDARD) <= MATCH_TOLERANCE and standard:
        std_names = sorted(m.ghost for m in standard)
        if not unique:
            parts.append(f"Standard speed ({BUCKET_STANDARD} m/s) — narrow with evidence")
        parts.append(f"Standard ghosts ({len(std_names)}): {', '.join(std_names[:8])}")
        if len(std_names) > 8:
            parts[-1] += f" +{len(std_names) - 8}"
        names.extend(std_names)

    if variable:
        range_names = sorted({m.ghost for m in variable if m.is_range_match})
        tier_names = sorted({m.ghost for m in variable if not m.is_range_match})
        if range_names:
            parts.append(f"Range match: {', '.join(range_names)}")
            names.extend(range_names)
        if tier_names:
            parts.append(f"Also possible: {', '.join(tier_names)}")
            names.extend(tier_names)

    label = " · ".join(parts) if parts else f"Match @ {speed_mps:.2f} m/s"
    return label, list(dict.fromkeys(names))


def ghosts_matching_speed(speed_mps: float, _ghost_entries: list | None = None) -> list[str]:
    """Return ghost names matching measured speed (for filters / shortlist)."""
    _label, names = format_speed_matches(speed_mps)
    return names


def mps_to_bpm(speed_mps: float, multiplier_pct: float = 100.0) -> int:
    if speed_mps <= 0 or multiplier_pct <= 0:
        return 0
    base = speed_mps / (multiplier_pct / 100.0)
    return max(1, round(base * 60.0 / 0.85))
