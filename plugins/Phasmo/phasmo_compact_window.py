"""Compact always-on-top ghost shortlist — styled to match the Phasmo cheat sheet plugin."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

EVIDENCE_NAMES = (
    "EMF 5",
    "Ultraviolet",
    "Writing",
    "Freezing",
    "DOTS",
    "Ghost Orbs",
    "Spirit Box",
)

EVIDENCE_SHORT = {
    "EMF 5": "EMF",
    "Ultraviolet": "UV",
    "Writing": "WRT",
    "Freezing": "FRZ",
    "DOTS": "DOTS",
    "Ghost Orbs": "ORB",
    "Spirit Box": "SB",
}


class PhasmoCompactWindow(QWidget):
    evidence_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Phasmo Compact HUD")
        self.setFixedWidth(340)
        self.setMinimumHeight(480)
        self._radius = 18
        self._drag_pos = None
        self._evidence_checks: dict[str, QCheckBox] = {}
        self._ghost_labels: list[QLabel] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._shell = QFrame()
        self._shell.setObjectName("CompactShell")
        outer.addWidget(self._shell)
        inner = QVBoxLayout(self._shell)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        self._drag_bar = QFrame()
        self._drag_bar.setObjectName("CompactDragBar")
        drag_lay = QHBoxLayout(self._drag_bar)
        drag_lay.setContentsMargins(14, 10, 14, 8)
        mark = QLabel("👻")
        mark.setObjectName("CompactBrand")
        title = QLabel("PHASMO HUD")
        title.setObjectName("CompactTitle")
        self.lbl_count = QLabel("0 ghosts")
        self.lbl_count.setObjectName("CompactCount")
        self.lbl_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        drag_lay.addWidget(mark)
        drag_lay.addWidget(title)
        drag_lay.addStretch(1)
        drag_lay.addWidget(self.lbl_count)
        inner.addWidget(self._drag_bar)

        content = QVBoxLayout()
        content.setContentsMargins(14, 4, 14, 14)
        content.setSpacing(10)

        sub = QLabel("Remaining suspects")
        sub.setObjectName("CompactSub")
        content.addWidget(sub)

        scroll = QScrollArea()
        scroll.setObjectName("CompactGhostScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ghost_host = QWidget()
        ghost_host.setObjectName("CompactGhostHost")
        self._ghost_lay = QVBoxLayout(ghost_host)
        self._ghost_lay.setContentsMargins(0, 0, 0, 0)
        self._ghost_lay.setSpacing(6)
        self._ghost_lay.addStretch(1)
        scroll.setWidget(ghost_host)
        content.addWidget(scroll, 1)

        ev_head = QLabel("Evidence filters")
        ev_head.setObjectName("CompactSub")
        content.addWidget(ev_head)

        grid = QGridLayout()
        grid.setSpacing(6)
        for index, name in enumerate(EVIDENCE_NAMES):
            chk = QCheckBox(EVIDENCE_SHORT.get(name, name))
            chk.setToolTip(name)
            chk.setTristate(True)
            chk.setCheckState(Qt.Unchecked)
            chk.setCursor(Qt.PointingHandCursor)
            chk.stateChanged.connect(lambda _state, n=name: self._emit_evidence(n))
            self._evidence_checks[name] = chk
            grid.addWidget(chk, index // 2, index % 2)
        content.addLayout(grid)

        hint = QLabel("✓ found · strike = ruled out")
        hint.setObjectName("CompactHint")
        content.addWidget(hint)
        inner.addLayout(content)
        self._apply_style()

    def set_corner_radius(self, radius: int) -> None:
        self._radius = max(8, min(28, radius))
        self._apply_style()

    def _apply_style(self) -> None:
        r = self._radius
        self.setStyleSheet(
            f"""
            QFrame#CompactShell {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0a0a0a, stop:0.55 #101018, stop:1 #1a1030);
                border: 1px solid rgba(255, 255, 255, 0.45);
                border-radius: {r}px;
            }}
            QFrame#CompactDragBar {{
                background: rgba(0, 0, 0, 0.45);
                border-top-left-radius: {r}px;
                border-top-right-radius: {r}px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            }}
            QLabel#CompactBrand {{
                font-size: 18px; color: #ffffff;
            }}
            QLabel#CompactTitle {{
                font-size: 14px; font-weight: 900; letter-spacing: 1px;
                color: #ffffff;
                font-family: Impact, 'Arial Narrow', sans-serif;
            }}
            QLabel#CompactCount {{
                font-size: 11px; font-weight: 800; color: #3ddc84;
            }}
            QLabel#CompactSub {{
                font-size: 11px; font-weight: 800; color: #d0d0d0;
                text-transform: uppercase; letter-spacing: 0.5px;
            }}
            QLabel#CompactHint {{
                font-size: 10px; color: #9a9a9a;
            }}
            QLabel#CompactGhostChip {{
                background: #121212;
                border: 1px solid #4b4b4b;
                border-radius: 10px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 800;
                padding: 8px 10px;
                font-family: Impact, 'Arial Narrow', sans-serif;
            }}
            QLabel#CompactGhostChip[match='true'] {{
                border: 1px solid #3ddc84;
                background: #0c1610;
                color: #eafff0;
            }}
            QScrollArea#CompactGhostScroll {{
                background: transparent; border: none;
            }}
            QWidget#CompactGhostHost {{
                background: transparent;
            }}
            QCheckBox {{
                color: #ffffff;
                font-size: 11px;
                font-weight: 700;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 15px; height: 15px;
                border-radius: 4px;
                border: 1px solid #6a6a6a;
                background: #141414;
            }}
            QCheckBox::indicator:checked {{
                background: #ffffff;
                border-color: #ffffff;
            }}
            QCheckBox::indicator:indeterminate {{
                background: #333333;
                border-color: #ffffff;
            }}
            QScrollBar:vertical {{
                background: #111111; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #888888; min-height: 24px; border-radius: 4px;
            }}
            """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_bar.geometry().contains(event.pos()):
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _emit_evidence(self, name: str) -> None:
        chk = self._evidence_checks[name]
        state = chk.checkState()
        if state == Qt.Checked:
            self.evidence_changed.emit(name, "include")
        elif state == Qt.PartiallyChecked:
            self.evidence_changed.emit(name, "exclude")
        else:
            self.evidence_changed.emit(name, "clear")

    def set_evidence_state(self, name: str, state: str) -> None:
        chk = self._evidence_checks.get(name)
        if chk is None:
            return
        chk.blockSignals(True)
        if state == "include":
            chk.setCheckState(Qt.Checked)
        elif state == "exclude":
            chk.setCheckState(Qt.PartiallyChecked)
        else:
            chk.setCheckState(Qt.Unchecked)
        chk.blockSignals(False)

    def set_shortlist(self, names: list[str]) -> None:
        while self._ghost_lay.count() > 1:
            item = self._ghost_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._ghost_labels.clear()
        self.lbl_count.setText(f"{len(names)} ghost{'s' if len(names) != 1 else ''}")
        if not names:
            empty = QLabel("No matches — relax a filter")
            empty.setObjectName("CompactHint")
            empty.setAlignment(Qt.AlignCenter)
            self._ghost_lay.insertWidget(0, empty)
            self._ghost_labels.append(empty)
            return
        for name in names:
            chip = QLabel(name.upper())
            chip.setObjectName("CompactGhostChip")
            chip.setProperty("match", True)
            chip.style().unpolish(chip)
            chip.style().polish(chip)
            font = QFont("Impact", 11)
            font.setBold(True)
            chip.setFont(font)
            self._ghost_lay.insertWidget(self._ghost_lay.count() - 1, chip)
            self._ghost_labels.append(chip)
