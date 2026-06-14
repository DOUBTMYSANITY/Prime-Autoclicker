"""Field guide — equipment, cursed possessions, and contract reference (original summaries)."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

CURSED_POSSESSIONS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "Haunted Mirror",
        "Tracking",
        "Right-click to activate; shows a sweep of the ghost's favourite room.",
        (
            "Drains 7.5% sanity per second while active (minimum 20% per use).",
            "All players see a faint glow over the area shown in the mirror.",
            "Breaking at 0% sanity triggers a cursed hunt.",
            "Usable only inside the investigation zone.",
        ),
    ),
    (
        "Music Box",
        "Lure",
        "Right-click to play; ghost sings along within 20m.",
        (
            "Within 5m: triggers a ghost event — ghost walks toward the box.",
            "If the ghost reaches the box or spends 5s walking toward it → cursed hunt.",
            "Throwing while active → cursed hunt. One use per box.",
            "2.5%/s sanity drain within 2.5m for all players (75% if full song).",
        ),
    ),
    (
        "Ouija Board",
        "Communication",
        "Left-click on board or right-click while holding to activate.",
        (
            "Where are you? → 50% sanity loss.",
            "Where is the bone? / Are you close? / Do you respond to everyone? → 20%.",
            "How old are you? / What is my sanity? / others → 5%.",
            "Hide and seek → instant cursed hunt.",
            "Walking away or insufficient sanity → board breaks + cursed hunt.",
        ),
    ),
    (
        "Summoning Circle",
        "Ritual",
        "Light all five candles with a lighter (16% sanity each, 80% total).",
        (
            "Ghost materializes in the circle for 5 seconds, then cursed hunt.",
            "Below 16% sanity on last candle → skips event, instant cursed hunt.",
            "One use per circle per contract.",
        ),
    ),
    (
        "Tarot Cards",
        "Random",
        "10 random cards per deck; draw inside the investigation zone.",
        (
            "The Tower (20%): interaction + doubled activity 20s.",
            "Wheel of Fortune (20%): ±25% sanity (green/red burn).",
            "The Fool (17%): disguised card, no effect.",
            "The Devil (10%): ghost event. Death (10%): cursed hunt.",
            "The Hermit (10%): traps ghost in favourite room 60s.",
            "The Sun (5%): sanity to 100%. The Moon (5%): sanity to 0%.",
            "High Priestess (2%): revives random dead player.",
            "The Hanged Man (1%): instant player death.",
        ),
    ),
    (
        "Voodoo Doll",
        "Provoke",
        "Each pin pushed causes an interaction (−5% sanity).",
        (
            "Heart pin → cursed hunt and −10% sanity.",
            "If sanity is too low for the pin cost, all pins push in → cursed hunt.",
        ),
    ),
    (
        "Monkey Paw",
        "Wishes",
        "3–5 wishes per contract depending on difficulty; no repeats.",
        (
            "I wish to be sane → all players set to 50%; permanent +50% sanity drain.",
            "I wish to be safe → nearest hide unblocked; ghost hears voice/electronics globally.",
            "I wish to leave → all doors unlock; 5s slow + reduced vision.",
            "I wish to see the ghost → ghost spawns 5s near you, then cursed hunt.",
            "I wish for activity → 2 min doubled activity; breaker breaks, exit locked 2 min.",
            "I wish to trap the ghost → ghost trapped 60s; you trapped 60s + cursed hunt.",
            "I wish for life → revive teammate; 50% chance wish-maker dies.",
            "I wish for knowledge → cross out wrong journal evidence; cursed hunt + debuffs.",
        ),
    ),
)

EQUIPMENT_GUIDE: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "EMF Reader",
        (
            "EMF 2: interaction within ~3m.",
            "EMF 5: ghost ability or one of three evidences.",
            "Use near breaker after Jinn sanity drops to catch EMF 2 on fuse box.",
        ),
    ),
    (
        "UV Light",
        (
            "Fingerprints on interactable surfaces (doors, switches, keyboards).",
            "Footprints in salt piles (except Wraith).",
            "Obake: 6-finger prints, double switch prints, 20s fade.",
        ),
    ),
    (
        "Spirit Box",
        ("Ask questions within ~3m with lights off for best results.", "Responses drain sanity; Moroi curses on response."),
    ),
    (
        "Ghost Writing Book",
        ("Place in favourite room; writing confirms evidence.", "Shade rarely interacts when players are present."),
    ),
    (
        "DOTS Projector",
        (
            "Silhouette passing through beam = evidence.",
            "Goryo: only visible through video camera, never naked eye.",
        ),
    ),
    (
        "Thermometer",
        (
            "Freezing: below 1°C / 33.8°F in ghost room.",
            "Track Hantu speed by comparing room temperatures during hunts.",
        ),
    ),
    (
        "Video / Photo Camera",
        (
            "Ghost orbs only visible on camera feed.",
            "Phantom vanishes instantly when photographed.",
            "Photos and videos earn money — check star ratings on truck computer.",
        ),
    ),
    (
        "Crucifix / Smudge / Incense",
        (
            "Crucifix: stops hunt within tier range (3m / 4m / 5m Demon).",
            "Smudge: 90s anti-hunt (180s Spirit, 60s Demon).",
            "Incense: blinds ghost during hunt; traps Yurei in room 90s.",
        ),
    ),
)

DIFFICULTY_PRESETS: tuple[tuple[str, int, str], ...] = (
    ("Amateur", 3, "All 3 evidence types available in journal."),
    ("Intermediate", 3, "Same evidence count; higher sanity drain and longer hunts."),
    ("Nightmare", 2, "One evidence type is forced hidden per contract."),
    ("Insanity", 1, "Two evidence types hidden — behaviour identification required."),
    ("Apocalypse / Custom 0", 0, "No journal evidence — use tells, speed, and sanity only."),
)


class _GuideCard(QFrame):
    def __init__(self, title: str, tag: str, body: str, bullets: tuple[str, ...], parent=None):
        super().__init__(parent)
        self.setObjectName("GuideCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        head = QHBoxLayout()
        name = QLabel(title)
        name.setObjectName("GuideCardTitle")
        chip = QLabel(tag)
        chip.setObjectName("GuideCardTag")
        head.addWidget(name, 1)
        head.addWidget(chip)
        lay.addLayout(head)
        if body:
            intro = QLabel(body)
            intro.setWordWrap(True)
            intro.setObjectName("GuideCardBody")
            lay.addWidget(intro)
        for line in bullets:
            row = QLabel(f"• {line}")
            row.setWordWrap(True)
            row.setObjectName("GuideCardBullet")
            lay.addWidget(row)


class FieldGuidePage(QWidget):
    """Equipment + cursed possession reference (inspired by community cheat sheets)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PhasmoFieldGuidePage")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("PhasmoSearch")
        self.search.setPlaceholderText("Search equipment and cursed items…")
        self.search.textChanged.connect(self._filter)
        search_row.addWidget(self.search, 1)
        root.addLayout(search_row)

        self.stack = QStackedWidget()
        self._cursed_page = self._build_scroll_page(CURSED_POSSESSIONS, cursed=True)
        self._equip_page = self._build_scroll_page(EQUIPMENT_GUIDE, cursed=False)
        self._diff_page = self._build_difficulty_page()
        self.stack.addWidget(self._cursed_page)
        self.stack.addWidget(self._equip_page)
        self.stack.addWidget(self._diff_page)
        root.addWidget(self.stack, 1)

        tabs = QHBoxLayout()
        self._tab_buttons: list[QPushButton] = []
        for label, index in (("Cursed Items", 0), ("Equipment", 1), ("Difficulty", 2)):
            btn = QPushButton(label)
            btn.setObjectName("GuideTab")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked, i=index: self._switch_tab(i))
            tabs.addWidget(btn)
            self._tab_buttons.append(btn)
        tabs.addStretch(1)
        root.addLayout(tabs)
        self._switch_tab(0)

    def _switch_tab(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._tab_buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _build_scroll_page(self, items, cursed: bool) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setSpacing(10)
        self._cards: list[_GuideCard] = getattr(self, "_cards", [])
        for entry in items:
            if cursed:
                title, tag, body, bullets = entry
            else:
                title, bullets = entry
                tag, body = "Gear", ""
            card = _GuideCard(title, tag, body, bullets)
            card.setProperty("searchText", f"{title} {tag} {body} {' '.join(bullets)}".lower())
            inner_lay.addWidget(card)
            self._cards.append(card)
        inner_lay.addStretch(1)
        scroll.setWidget(inner)
        lay.addWidget(scroll)
        return page

    def _build_difficulty_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        for name, evidence, note in DIFFICULTY_PRESETS:
            card = _GuideCard(name, f"{evidence} evidence", note, ())
            inner_lay.addWidget(card)
        hint = QLabel(
            "Use the evidence slot selector on the Ghost Type filters tab to match your contract. "
            "On Nightmare and above, forced hidden evidence is applied automatically when all slots are filled."
        )
        hint.setWordWrap(True)
        hint.setObjectName("GuideCardBody")
        inner_lay.addWidget(hint)
        inner_lay.addStretch(1)
        scroll.setWidget(inner)
        lay.addWidget(scroll)
        return page

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for card in getattr(self, "_cards", []):
            hay = card.property("searchText") or ""
            card.setVisible(not needle or needle in hay)
