"""Ctrl+K global search for ghosts."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QVBoxLayout


class GlobalSearchDialog(QDialog):
    picked = pyqtSignal(str, str)

    _STYLESHEET = """
        QDialog { background: #0A0A0A; border: 1px solid #4D4D4D; }
        QLabel { color: #BDBDBD; font-size: 12px; }
        QLineEdit {
            background: #111111; border: 1px solid #4D4D4D; border-radius: 10px;
            padding: 10px 14px; color: #FFFFFF; font-size: 14px;
        }
        QLineEdit:focus { border: 1px solid #3DDC84; }
        QListWidget {
            background: #0B0B0B; border: 1px solid #3A3A3A; border-radius: 10px;
            color: #FFFFFF; font-size: 13px; padding: 4px;
        }
        QListWidget::item { padding: 8px 10px; border-radius: 6px; }
        QListWidget::item:selected { background: #1A2A1F; color: #3DDC84; }
        QListWidget::item:hover { background: #151515; }
    """

    def __init__(self, items: list[tuple[str, str, str]], parent=None, initial: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Search")
        self.setModal(True)
        self.resize(560, 440)
        self.setStyleSheet(self._STYLESHEET)
        self._items = items
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        hint = QLabel("Ghosts — type to filter, Enter to open")
        lay.addWidget(hint)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Search…")
        self.input.textChanged.connect(self._filter)
        lay.addWidget(self.input)
        self.list = QListWidget()
        self.list.itemActivated.connect(self._activate)
        self.list.itemDoubleClicked.connect(self._activate)
        lay.addWidget(self.list, 1)
        self.input.setText(initial)
        self._filter(initial)

    def showEvent(self, event):
        super().showEvent(event)
        self.input.setFocus()
        self.input.selectAll()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.list.count() > 0:
                self._activate(self.list.item(0))
            return
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        if event.key() == Qt.Key_Down and self.list.count() > 0:
            self.list.setCurrentRow(0)
            self.list.setFocus()
            return
        super().keyPressEvent(event)

    def _filter(self, text: str):
        self.list.clear()
        needle = text.strip().lower()
        for kind, label, target in self._items:
            hay = f"{kind} {label} {target}".lower()
            if not needle or needle in hay:
                self.list.addItem(f"[{kind}] {label}")
                item = self.list.item(self.list.count() - 1)
                item.setData(Qt.UserRole, (kind, target))

    def _activate(self, item):
        if item is None:
            return
        kind, target = item.data(Qt.UserRole)
        self.picked.emit(kind, target)
        self.accept()
