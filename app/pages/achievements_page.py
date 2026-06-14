from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
)

from app.styling.localization import tr
from app.styling.themes import get_theme
from app.gui.widgets import Card, add_shadow
from app.services.stats_tracker import StatsTracker


class AchievementsPage(QWidget):
    """Achievements & Badges page – grouped by category with descriptions."""

    def __init__(self, tracker: StatsTracker, parent=None):
        super().__init__(parent)
        self.tracker = tracker

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(16)

        # Hero
        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=28, y=10, alpha=110)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(28, 22, 28, 22)
        hl.setSpacing(8)
        self.hero_title = QLabel("Achievements & Badges")
        self.hero_title.setObjectName("HeroTitle")
        self.hero_sub = QLabel(tr("achievements_sub"))
        self.hero_sub.setObjectName("HeroSub")
        self.lbl_progress = QLabel("")
        self.lbl_progress.setObjectName("HeroSub")
        hl.addWidget(self.hero_title)
        hl.addWidget(self.hero_sub)
        hl.addWidget(self.lbl_progress)
        hl.addStretch(1)
        self._root.addWidget(hero)

        # Container for category cards (rebuilt on refresh)
        self._categories_widget = QWidget()
        self._categories_layout = QVBoxLayout(self._categories_widget)
        self._categories_layout.setContentsMargins(0, 0, 0, 0)
        self._categories_layout.setSpacing(16)
        self._root.addWidget(self._categories_widget)
        self._root.addStretch(1)

        self.refresh()

    def _clear_categories(self):
        """Remove all category cards."""
        while self._categories_layout.count():
            item = self._categories_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def refresh(self, palette: dict | None = None):
        self._clear_categories()
        p = palette or get_theme().get("palette", {})

        categories = self.tracker.get_categorized_achievements()

        # Overall progress
        total_all = 0
        unlocked_all = 0
        for cat in categories:
            for _icon, _name, _desc, earned in cat["achievements"]:
                total_all += 1
                if earned:
                    unlocked_all += 1
        self.lbl_progress.setText(f"{unlocked_all}/{total_all} achievements unlocked")

        for cat in categories:
            achievements = cat["achievements"]
            cat_unlocked = sum(1 for *_, e in achievements if e)
            cat_total = len(achievements)

            card = Card()
            card.setObjectName("ConfigCard")
            add_shadow(card, blur=26, y=10, alpha=110)
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(20, 18, 20, 18)
            card_lay.setSpacing(14)

            # ── Category header ──
            header_row = QHBoxLayout()
            header_row.setSpacing(10)
            cat_icon = QLabel(cat["icon"])
            cat_icon.setObjectName("HeaderIcon")
            cat_icon.setFixedSize(34, 34)
            cat_icon.setAlignment(Qt.AlignCenter)
            cat_title = QLabel(cat["category"])
            cat_title.setObjectName("CardHeader")
            header_row.addWidget(cat_icon)
            header_row.addWidget(cat_title)
            header_row.addStretch(1)

            # Progress pill for this category
            progress_lbl = QLabel(f"{cat_unlocked}/{cat_total}")
            progress_lbl.setFixedHeight(24)
            progress_lbl.setMinimumWidth(40)
            progress_lbl.setAlignment(Qt.AlignCenter)
            if cat_unlocked == cat_total:
                progress_lbl.setStyleSheet(
                    f"background: {p.get('start_btn_bg', 'rgba(100,255,160,0.15)')};"
                    f" border: 1px solid {p.get('start_btn_border', 'rgba(100,255,160,0.30)')};"
                    f" border-radius: 10px; font-size: 11px; font-weight: 700;"
                    f" color: {p.get('running_color', '#9CFFB2')}; padding: 0 8px;"
                )
            else:
                progress_lbl.setStyleSheet(
                    f"background: {p.get('badge_bg', 'rgba(255,255,255,0.06)')};"
                    f" border: 1px solid {p.get('badge_border', 'rgba(255,255,255,0.10)')};"
                    f" border-radius: 10px; font-size: 11px; font-weight: 700;"
                    f" color: {p.get('text_secondary', 'rgba(233,237,255,0.60)')}; padding: 0 8px;"
                )
            header_row.addWidget(progress_lbl)
            card_lay.addLayout(header_row)

            # ── Stat label ──
            stat_lbl = QLabel(cat["stat_label"])
            stat_lbl.setObjectName("HeroSub")
            stat_lbl.setStyleSheet(
                f"font-size: 12px; color: {p.get('text_secondary', 'rgba(233,237,255,0.55)')}; padding-left: 44px;"
            )
            card_lay.addWidget(stat_lbl)

            # ── Achievement grid ──
            grid = QGridLayout()
            grid.setSpacing(10)

            for i, (icon, name, desc, earned) in enumerate(achievements):
                is_hidden = cat.get("hidden", False)
                badge = Card(radius=14)
                badge.setObjectName("InnerPanel")
                bl = QVBoxLayout(badge)
                bl.setContentsMargins(12, 10, 12, 10)
                bl.setSpacing(4)

                # For hidden category: show "?" icon + "???" text when not earned
                display_icon = icon if (earned or not is_hidden) else "❓"
                display_name = name if (earned or not is_hidden) else "?"
                display_desc = desc if (earned or not is_hidden) else "???"

                # Emoji icon
                emoji = QLabel(display_icon)
                emoji.setAlignment(Qt.AlignCenter)
                if earned:
                    emoji.setStyleSheet("font-size: 26px;")
                else:
                    emoji.setStyleSheet(
                        f"font-size: 26px; color: {p.get('text_secondary', 'rgba(233,237,255,0.25)')};"
                    )

                # Name
                name_lbl = QLabel(display_name)
                name_lbl.setAlignment(Qt.AlignCenter)
                name_lbl.setWordWrap(True)
                if earned:
                    name_lbl.setStyleSheet(
                        f"font-size: 11px; font-weight: 700; color: {p.get('running_color', '#9CFFB2')};"
                    )
                else:
                    name_lbl.setStyleSheet(
                        f"font-size: 11px; font-weight: 600; color: {p.get('text_secondary', 'rgba(233,237,255,0.40)')};"
                    )

                # Description
                desc_lbl = QLabel(display_desc)
                desc_lbl.setAlignment(Qt.AlignCenter)
                desc_lbl.setWordWrap(True)
                if earned:
                    desc_lbl.setStyleSheet(
                        f"font-size: 10px; color: {p.get('text_secondary', 'rgba(233,237,255,0.55)')};"
                    )
                else:
                    desc_lbl.setStyleSheet(
                        f"font-size: 10px; color: {p.get('text_secondary', 'rgba(233,237,255,0.25)')};"
                    )

                bl.addWidget(emoji)
                bl.addWidget(name_lbl)
                bl.addWidget(desc_lbl)

                row = i // 5
                col = i % 5
                grid.addWidget(badge, row, col)

            card_lay.addLayout(grid)
            card_lay.addStretch(1)
            self._categories_layout.addWidget(card)

    def retranslateUi(self):
        """Update all translatable text."""
        self.hero_title.setText(tr("achievements"))
        self.hero_sub.setText(tr("achievements_sub"))
        self.refresh()

    def apply_theme(self, palette: dict | None = None):
        """Refresh dynamic badge colors when the active theme changes."""
        self.refresh(palette)
