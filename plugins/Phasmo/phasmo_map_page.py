"""Tanglewood map viewer for the unofficial Phasmo reference plugin."""
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MAP_HTML = _PROJECT_ROOT / "assets" / "maps" / "tanglewood_map.html"


class PhasmoMapPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        title = QLabel("Tanglewood — Interactive Floor Map")
        title.setObjectName("PhasmoTitle")
        title.setWordWrap(True)
        lay.addWidget(title)

        note = QLabel(
            "Unofficial fan-made schematic map. Not affiliated with Kinetic Games.\n"
            "Opens in your default browser for full interactivity."
        )
        note.setObjectName("PhasmoSub")
        note.setWordWrap(True)
        lay.addWidget(note)

        self._embedded = None
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView

            if _MAP_HTML.is_file():
                self._embedded = QWebEngineView()
                self._embedded.load(QUrl.fromLocalFile(str(_MAP_HTML.resolve())))
                self._embedded.setMinimumHeight(520)
                lay.addWidget(self._embedded, 1)
        except Exception:
            pass

        if self._embedded is None:
            missing = QLabel(
                "Embedded map requires PyQtWebEngine (optional).\n"
                "Use the button below to open the interactive map in your browser."
            )
            missing.setObjectName("PhasmoSupport")
            missing.setWordWrap(True)
            lay.addWidget(missing)

        btn = QPushButton("Open Tanglewood Map in Browser")
        btn.setObjectName("PhasmoReset")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._open_external)
        lay.addWidget(btn)
        lay.addStretch(1)

    def _open_external(self) -> None:
        if _MAP_HTML.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(_MAP_HTML.resolve())))
