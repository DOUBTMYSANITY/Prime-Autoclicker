"""Shared Phasmophobia cheat-sheet constants and filter helpers."""
from __future__ import annotations

STANDARD_EVIDENCE_SLOTS = 3
MIMIC_FAKE_EVIDENCE = "Ghost Orbs"

# Evidence that is always shown in the journal and can never be the hidden slot.
FORCED_EVIDENCE: dict[str, str] = {
    "Deogen": "Spirit Box",
    "Moroi": "Spirit Box",
    "Goryo": "DOTS",
    "Hantu": "Freezing",
    "Obake": "Ultraviolet",
    "The Mimic": MIMIC_FAKE_EVIDENCE,
}

ALL_GHOST_NAMES: tuple[str, ...] = (
    "Aswang",
    "Banshee",
    "Dayan",
    "Demon",
    "Deogen",
    "Gallu",
    "Goryo",
    "Hantu",
    "Jinn",
    "Kormos",
    "Mare",
    "Moroi",
    "Myling",
    "Obake",
    "Obambo",
    "Oni",
    "Onryo",
    "Phantom",
    "Poltergeist",
    "Raiju",
    "Revenant",
    "Shade",
    "Spirit",
    "Thaye",
    "The Mimic",
    "The Twins",
    "Wraith",
    "Yokai",
    "Yurei",
)

_ALL = frozenset(ALL_GHOST_NAMES)


def _all_except(*keep: str) -> frozenset[str]:
    return frozenset(name for name in ALL_GHOST_NAMES if name not in keep)


# (label, targets eliminated when CHECKED, optional special key for dynamic matching)
# Checked = behavior observed -> eliminate ghosts in targets (or dynamic rule).
# PartiallyChecked = behavior ruled out -> eliminate ghosts NOT in targets / inverse dynamic rule.
BEHAVIOR_FILTER_SPECS: tuple[tuple[str, frozenset[str] | None, str | None], ...] = (
    ("Male ghost model / male name", frozenset({"Banshee", "Dayan"}), None),
    ("Female-only ghost name / model", frozenset({"Banshee", "Dayan"}), "female_only_seen"),
    ("Ghost mist event (smoke ball) seen", frozenset({"Oni", "Kormos"}), None),
    ("Door only partially opened/closed", frozenset({"Yurei"}), None),
    ("Ghost speeds up near active electronics", _all_except("Raiju"), None),
    ("Salt footprints found in salt pile", frozenset({"Wraith"}), None),
    ("Ghost refused to step on salt", _all_except("Wraith"), None),
    ("Ghost room changed at least once", frozenset({"Goryo"}), None),
    ("Ghost interacted while player in room", frozenset({"Shade"}), None),
    ("No ghost event while player in ghost room", _all_except("Shade"), None),
    ("Hunt started above 70% sanity", None, "hunt_above_70"),
    ("Hunt started above 65% sanity", None, "hunt_above_65"),
    ("Crucifix burned within 3m (standard range)", frozenset({"Demon"}), None),
    ("Crucifix burned at 4–5m (extended range)", _all_except("Demon"), None),
    ("Flame extinguished by ghost", _all_except("Onryo"), None),
    ("No DOTS through video camera", frozenset({"Goryo"}), None),
    ("Hunt ended in official hide spot (player safe)", _all_except("Aswang"), None),
    ("Ghost walked past hidden player (blind hunt)", _all_except("Kormos"), None),
    ("Early hunt after sprinting in ghost room", _all_except("Kormos"), None),
    ("Enraged after salt / smudge / crucifix", _all_except("Gallu"), None),
    ("Banshee shriek on Parabolic Microphone", _all_except("Banshee"), None),
    ("Visible icy breath during hunt (breaker off)", _all_except("Hantu"), None),
    ("Ghost turned fuse box off", frozenset({"Jinn"}), None),
    ("Ghost orbs visible but orbs not in journal evidences", _all_except("The Mimic"), None),
    ("Smudge prevented hunt for ~3 minutes", _all_except("Spirit"), None),
    ("Twin interactions in two locations at once", _all_except("The Twins"), None),
    ("Ouija age response increases over time", _all_except("Thaye"), None),
)


def hidden_evidence_slots(findable_count: int) -> int:
    return max(0, STANDARD_EVIDENCE_SLOTS - max(0, min(3, int(findable_count))))


def slot_evidence(evidence: tuple[str, ...], ghost_name: str) -> set[str]:
    items = set(evidence)
    if ghost_name == "The Mimic":
        items.discard(MIMIC_FAKE_EVIDENCE)
    return items


def _journal_included(selected_evidence: set[str], journal_pool: set[str]) -> set[str]:
    """Confirmed evidences that count toward journal slots for this ghost."""
    return {ev for ev in selected_evidence if ev in journal_pool}


def ghost_matches_evidence(
    ghost_name: str,
    evidence: tuple[str, ...],
    selected_evidence: set[str],
    excluded_evidence: set[str],
    findable_count: int,
) -> bool:
    """Return True when journal / visual evidence selections are compatible with this ghost.

  Phasmophobia journal rules (per difficulty):
  - Amateur/Intermediate/Professional: up to 3 evidences visible in journal
  - Nightmare: 2 visible, 1 forced hidden per ghost
  - Insanity: 1 visible, 2 forced hidden
  - Apocalypse: 0 in journal; only Mimic fake Ghost Orbs can be marked

  Confirmed (included) evidences must ALL belong to the ghost — we never
  intersect away unknown picks. Forced-evidence ghosts always show their
  forced type in the journal when it is one of their three types.
    """
    findable = max(0, min(3, int(findable_count)))
    full_pool = set(evidence)
    journal_pool = slot_evidence(evidence, ghost_name)
    included = set(selected_evidence)
    excluded = set(excluded_evidence)
    forced = FORCED_EVIDENCE.get(ghost_name)

    if not included and not excluded:
        return True

    if findable == 0:
        if MIMIC_FAKE_EVIDENCE in included:
            return ghost_name == "The Mimic"
        return not included

    for ev in included:
        if ev == MIMIC_FAKE_EVIDENCE:
            if ghost_name == "The Mimic":
                continue
            if ev not in full_pool:
                return False
        elif ev not in journal_pool:
            return False

    if excluded.intersection(journal_pool):
        return False
    if ghost_name == "The Mimic" and MIMIC_FAKE_EVIDENCE in excluded:
        return False
    if forced and forced in excluded:
        return False

    journal_included = _journal_included(included, journal_pool)

    if forced and forced in journal_pool:
        if len(journal_included) >= findable and forced not in included:
            return False

    if len(journal_included) < findable:
        return True

    hidden = hidden_evidence_slots(findable)
    unfound = journal_pool - journal_included - excluded
    if forced and forced in journal_pool:
        unfound.discard(forced)
    return len(unfound) <= hidden


def passes_forced_evidence_check(
    ghost_name: str,
    evidence: tuple[str, ...],
    selected_evidence: set[str],
    excluded_evidence: set[str],
    findable_count: int,
) -> bool:
    """Backward-compatible alias for ghost_matches_evidence."""
    return ghost_matches_evidence(
        ghost_name, evidence, selected_evidence, excluded_evidence, findable_count
    )


def forced_evidence_tell_lines(
    ghost_name: str,
    evidence: tuple[str, ...],
    selected_evidence: set[str],
    excluded_evidence: set[str],
    findable_count: int,
) -> list[str]:
    lines: list[str] = []
    pool = slot_evidence(evidence, ghost_name)
    findable = max(0, min(3, int(findable_count)))
    hidden = hidden_evidence_slots(findable)

    forced = FORCED_EVIDENCE.get(ghost_name)
    if ghost_name == "The Mimic":
        lines.append("Always shows fake Ghost Orbs (hidden 4th evidence)")
    elif forced:
        lines.append(f"Forced evidence (never hidden): {forced}")

    if findable >= STANDARD_EVIDENCE_SLOTS:
        return lines

    journal_included = _journal_included(selected_evidence, pool)
    unfound = pool - journal_included - excluded_evidence
    if forced:
        unfound.discard(forced)
    if not unfound:
        return lines

    slots_filled = len(journal_included) >= findable and findable > 0
    label = sorted(unfound)
    if slots_filled:
        if len(unfound) <= hidden:
            lines.append(f"Forced hidden evidence: {', '.join(label)}")
        else:
            lines.append(f"Incompatible hidden evidence: {', '.join(label)}")
    elif hidden > 0:
        lines.append(f"May be forced hidden ({hidden} slot{'s' if hidden != 1 else ''}): {', '.join(label)}")

    return lines


def behavior_filter_match(
    ghost_name: str,
    label: str,
    targets: frozenset[str] | None,
    special: str | None,
    observed: bool,
    hunt_min: int,
    hunt_max: int,
) -> bool:
    """Behavior filter — only applies when observed=True (checkbox checked)."""
    if not observed:
        return True

    if special == "hunt_above_70":
        return hunt_max >= 70

    if special == "hunt_above_65":
        return hunt_max >= 65

    if special == "female_only_seen":
        return ghost_name in {"Banshee", "Dayan"}

    target_set = targets or frozenset()
    # Observed tell → eliminate ghosts listed in targets (they cannot match).
    return ghost_name not in target_set


def ghost_shortlist(
    ghost_entries: list,
    selected_evidence: set[str],
    excluded_evidence: set[str],
    findable_count: int,
    match_fn,
) -> list:
    results = []
    for entry in ghost_entries:
        if match_fn(entry.name, selected_evidence, excluded_evidence, findable_count):
            results.append(entry)
    return results
