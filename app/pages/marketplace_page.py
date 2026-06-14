from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QPushButton, QLineEdit, QComboBox, QGridLayout, QSizePolicy

from app.gui.widgets import Card, add_shadow


class MarketplacePage(QWidget):
    """Marketplace view backed by locally discovered plugin records."""

    install_requested = pyqtSignal(str)
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=28, y=10, alpha=110)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(16, 12, 16, 12)
        hl.setSpacing(3)

        title = QLabel("Marketplace")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("All discovered plugins in one place with load status and versions.")
        subtitle.setObjectName("HeroSub")
        subtitle.setWordWrap(True)

        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(hero)

        self._summary = QLabel("Plugins: 0")
        self._summary.setObjectName("HeroSub")
        root.addWidget(self._summary)

        search_row = QHBoxLayout()
        search_row.setSpacing(5)
        self.input_search = QLineEdit()
        self.input_search.setObjectName("HotkeyBtn")
        self.input_search.setPlaceholderText("Search plugins, ids, or descriptions...")
        self.cmb_filter = QComboBox()
        self.cmb_filter.setObjectName("DropDown")
        self.cmb_filter.addItems(["All", "Installed", "Not Installed", "Loaded", "Failed"])
        search_row.addWidget(self.input_search, 1)
        search_row.addWidget(self.cmb_filter)
        root.addLayout(search_row)

        controls = QHBoxLayout()
        controls.setSpacing(5)
        self.lbl_market_hint = QLabel("Install from Marketplace, then manage in the Plugins tab.")
        self.lbl_market_hint.setObjectName("WarnText")
        controls.addWidget(self.lbl_market_hint)
        controls.addStretch(1)
        self.btn_refresh = QPushButton("Refresh Marketplace")
        self.btn_refresh.setObjectName("ToggleButton")
        self.btn_refresh.setProperty("active", True)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        controls.addWidget(self.btn_refresh)
        root.addLayout(controls)

        self.input_search.textChanged.connect(self._rerender_cached)
        self.cmb_filter.currentTextChanged.connect(self._rerender_cached)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("MainScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.viewport().installEventFilter(self)
        self._host = QWidget()
        self._host.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._host)
        # Inset grid so card shadows stay inside the scroll viewport.
        self._grid.setContentsMargins(6, 2, 6, 6)
        self._grid.setHorizontalSpacing(6)
        self._grid.setVerticalSpacing(6)
        self._grid.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._host)
        root.addWidget(self._scroll, 1)
        self._cached_records = []
        self._cached_catalog = []
        self._sync_grid_host_width()

    def _sync_grid_host_width(self) -> None:
        viewport = self._scroll.viewport()
        if viewport is None:
            return
        self._host.setFixedWidth(max(0, viewport.width()))

    def eventFilter(self, obj, event):
        if obj is self._scroll.viewport() and event.type() == QEvent.Resize:
            self._sync_grid_host_width()
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_grid_host_width()

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _matches_filter(self, rec, status_filter: str) -> bool:
        state = (status_filter or "All").lower()
        if state == "all":
            return True
        if state == "installed":
            return rec is not None
        if state == "not installed":
            return rec is None
        if state == "loaded":
            return rec is not None and bool(getattr(rec, "loaded", False))
        if state == "failed":
            return rec is not None and not bool(getattr(rec, "loaded", False))
        return True

    def _matches_query(self, rec, item: dict, query: str) -> bool:
        q = (query or "").strip().lower()
        if not q:
            return True
        blob = " ".join([
            str(item.get("id", "")),
            str(item.get("name", "")),
            str(item.get("description", "")),
            str(item.get("version", "")),
            str(getattr(rec, "name", "")),
            str(getattr(rec, "description", "")),
        ]).lower()
        return q in blob

    def _plugin_icon_text(self, plugin_id: str, plugin_name: str) -> str:
        pid = (plugin_id or "").lower()
        pname = (plugin_name or "").lower()
        if "kahoot" in pid or "kahoot" in pname:
            return "K"
        if "input" in pid or "humanization" in pname:
            return "H"
        if "phasmo" in pid or "phasmo" in pname:
            return "P"
        if "route" in pid:
            return "R"
        if "preset" in pid:
            return "B"
        return "?"

    def _compact_desc(self, text: str, limit: int = 84) -> str:
        raw = " ".join(str(text or "").split())
        if len(raw) <= limit:
            return raw
        return raw[: max(0, limit - 1)].rstrip() + "…"

    def _compact_name(self, text: str, limit: int = 28) -> str:
        raw = " ".join(str(text or "").split())
        if len(raw) <= limit:
            return raw
        return raw[: max(0, limit - 1)].rstrip() + "…"

    def _prepare_marketplace_card(self, card: QWidget) -> None:
        card.setMinimumWidth(0)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _prepare_marketplace_label(self, label: QLabel) -> None:
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def _add_card(self, card: QWidget, index: int):
        # Render cards in a 2-column marketplace grid.
        self._prepare_marketplace_card(card)
        row = index // 2
        col = index % 2
        self._grid.addWidget(card, row, col)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)
        self._grid.setColumnMinimumWidth(0, 0)
        self._grid.setColumnMinimumWidth(1, 0)

    def _rerender_cached(self):
        self.refresh_plugins(self._cached_records, self._cached_catalog)

    def refresh_plugins(self, records: list, catalog: list[dict] | None = None):
        self._cached_records = list(records or [])
        self._cached_catalog = list(catalog or [])
        self._clear_grid()

        installed_map = {str(getattr(r, "plugin_id", "")): r for r in records}
        total = len(records)
        loaded = len([r for r in records if getattr(r, "loaded", False)])
        failed = total - loaded
        self._summary.setText(f"Plugins: {total} | Loaded: {loaded} | Failed: {failed}")

        status_filter = self.cmb_filter.currentText()
        query = self.input_search.text()

        shown_ids: set[str] = set()
        added = 0

        for item in (catalog or []):
            pid = str(item.get("id", "")).strip()
            if not pid:
                continue
            shown_ids.add(pid)
            rec = installed_map.get(pid)
            if not self._matches_filter(rec, status_filter):
                continue
            if not self._matches_query(rec, item, query):
                continue
            card = Card()
            card.setObjectName("MarketplaceCard")
            add_shadow(card, blur=16, y=5, alpha=70)
            card.setFixedHeight(148)
            lay = QVBoxLayout(card)
            lay.setContentsMargins(10, 7, 10, 7)
            lay.setSpacing(2)

            top = QHBoxLayout()
            top.setSpacing(6)
            plugin_name = str(item.get("name", getattr(rec, "name", "Unknown Plugin")))
            icon = QLabel(self._plugin_icon_text(pid, plugin_name))
            icon.setObjectName("HeaderIcon")
            icon.setAlignment(Qt.AlignCenter)
            icon.setFixedSize(24, 24)
            name = QLabel(self._compact_name(plugin_name))
            name.setObjectName("CardHeader")
            name.setWordWrap(False)
            self._prepare_marketplace_label(name)
            if rec is None:
                status = "Not Installed"
            else:
                status = "Loaded" if bool(getattr(rec, "loaded", False)) else "Failed"
            status_lbl = QLabel(status)
            status_lbl.setObjectName("WarnText")
            self._prepare_marketplace_label(status_lbl)
            top.addWidget(icon)
            top.addWidget(name, 1)
            top.addWidget(status_lbl)

            meta_panel = Card(radius=14)
            meta_panel.setObjectName("MarketplaceInnerPanel")
            meta_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            meta_panel.setMinimumWidth(0)
            meta_l = QVBoxLayout(meta_panel)
            meta_l.setContentsMargins(8, 5, 8, 5)
            meta_l.setSpacing(1)

            meta = QLabel(
                f"v{item.get('version', getattr(rec, 'version', '-'))}  •  {item.get('author', 'Prime Team')}"
            )
            meta.setObjectName("HeroSub")
            self._prepare_marketplace_label(meta)
            desc = QLabel(self._compact_desc(item.get("description", getattr(rec, "description", "No description."))))
            desc.setObjectName("WarnText")
            desc.setWordWrap(False)
            self._prepare_marketplace_label(desc)

            meta_l.addWidget(meta)
            meta_l.addWidget(desc)

            lay.addLayout(top)
            lay.addWidget(meta_panel, 1)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(2)
            btn_install = QPushButton("Install")
            btn_install.setObjectName("HotkeyBtn")
            btn_install.setCursor(Qt.PointingHandCursor)
            btn_install.setEnabled(rec is None)
            if rec is not None:
                btn_install.setText("Installed")
                btn_install.setToolTip("Manage or remove in Plugins tab")
            btn_install.clicked.connect(lambda _=False, x=pid: self.install_requested.emit(x))
            btn_row.addWidget(btn_install)
            btn_row.addStretch(1)
            lay.addLayout(btn_row)

            err = str(getattr(rec, "error", "")).strip() if rec is not None else ""
            if err:
                card.setFixedHeight(168)
                err_lbl = QLabel(f"Error: {err.splitlines()[0]}")
                err_lbl.setObjectName("WarnText")
                err_lbl.setWordWrap(False)
                self._prepare_marketplace_label(err_lbl)
                lay.addWidget(err_lbl)

            self._add_card(card, added)
            added += 1

        for rec in records:
            pid = str(getattr(rec, "plugin_id", "")).strip()
            if not pid or pid in shown_ids:
                continue
            item = {
                "id": pid,
                "name": getattr(rec, "name", ""),
                "description": getattr(rec, "description", ""),
                "version": getattr(rec, "version", ""),
            }
            if not self._matches_filter(rec, status_filter):
                continue
            if not self._matches_query(rec, item, query):
                continue
            self._add_card(self._build_installed_only_card(rec), added)
            added += 1

        if added == 0:
            empty = QLabel("No plugins match your search/filter.")
            empty.setObjectName("WarnText")
            empty.setAlignment(Qt.AlignCenter)
            self._grid.addWidget(empty, 0, 0, 1, 2)

    def _build_installed_only_card(self, rec) -> QWidget:
        card = Card()
        card.setObjectName("MarketplaceCard")
        add_shadow(card, blur=16, y=5, alpha=70)
        card.setFixedHeight(144)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(6)
        pid = str(getattr(rec, "plugin_id", ""))
        plugin_name = str(getattr(rec, "name", "Unknown Plugin"))
        icon = QLabel(self._plugin_icon_text(pid, plugin_name))
        icon.setObjectName("HeaderIcon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(24, 24)
        name = QLabel(self._compact_name(plugin_name))
        name.setObjectName("CardHeader")
        name.setWordWrap(False)
        self._prepare_marketplace_label(name)
        status = "Loaded" if bool(getattr(rec, "loaded", False)) else "Failed"
        status_lbl = QLabel(status)
        status_lbl.setObjectName("WarnText")
        self._prepare_marketplace_label(status_lbl)
        top.addWidget(icon)
        top.addWidget(name, 1)
        top.addWidget(status_lbl)

        meta_panel = Card(radius=14)
        meta_panel.setObjectName("MarketplaceInnerPanel")
        meta_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        meta_panel.setMinimumWidth(0)
        meta_l = QVBoxLayout(meta_panel)
        meta_l.setContentsMargins(8, 5, 8, 5)
        meta_l.setSpacing(1)

        meta = QLabel(f"v{getattr(rec, 'version', '-')}  •  Prime Team")
        meta.setObjectName("HeroSub")
        self._prepare_marketplace_label(meta)
        desc = QLabel(self._compact_desc(getattr(rec, "description", "No description.")))
        desc.setObjectName("WarnText")
        desc.setWordWrap(False)
        self._prepare_marketplace_label(desc)

        meta_l.addWidget(meta)
        meta_l.addWidget(desc)

        lay.addLayout(top)
        lay.addWidget(meta_panel, 1)

        return card
