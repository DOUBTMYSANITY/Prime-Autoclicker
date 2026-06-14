# sidebar.py — Neon glass sidebar + dialogs (clickable using QPushButton)

from PyQt5 import QtCore, QtGui, QtWidgets
from app.styling.themes import get_theme, get_glass_dialog_stylesheet


# ------------------------------ Shared glass base ------------------------------
class GlassDialog(QtWidgets.QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._wrap = QtWidgets.QVBoxLayout(self)
        self._wrap.setContentsMargins(0, 0, 0, 0)

        self._card = QtWidgets.QFrame()
        self._card.setObjectName("glassCard")
        self._apply_theme()

        eff = QtWidgets.QGraphicsDropShadowEffect(self._card)
        theme = get_theme()
        accent = theme["palette"]["accent_solid"]
        _c = QtGui.QColor(accent)
        _c.setAlpha(120)
        eff.setBlurRadius(40); eff.setOffset(0, 14); eff.setColor(_c)
        self._card.setGraphicsEffect(eff)

        self._inner = QtWidgets.QVBoxLayout(self._card)
        self._inner.setContentsMargins(18, 18, 18, 18)
        self._inner.setSpacing(12)

        self._wrap.addWidget(self._card)

        # header row
        hdr = QtWidgets.QHBoxLayout()
        self._title = QtWidgets.QLabel(title)
        self._title.setStyleSheet(f"font-weight:700; font-size:14pt; color:{theme['palette']['text_primary']};")
        self._close = QtWidgets.QToolButton(); self._close.setText("✕")
        self._close.clicked.connect(self.reject)
        self._close.setStyleSheet(
            f"QToolButton{{border:1px solid {theme['palette']['card_border']}; border-radius:8px;"
            f" padding:6px; color:{theme['palette']['text_primary']};"
            f" background:{theme['palette']['pill_bg']};}}"
            f" QToolButton:hover{{background:{theme['palette']['pill_active_bg']};}}"
        )
        hdr.addWidget(self._title, 1); hdr.addWidget(self._close, 0, QtCore.Qt.AlignRight)
        self._inner.addLayout(hdr)

    def _apply_theme(self):
        """Apply the current theme stylesheet to the glass card."""
        self._card.setStyleSheet(get_glass_dialog_stylesheet())

    def refresh_theme(self):
        """Public method to re-apply after a theme change."""
        self._apply_theme()

    def body_layout(self) -> QtWidgets.QVBoxLayout:
        lay = QtWidgets.QVBoxLayout()
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(10)
        self._inner.addLayout(lay, 1)
        return lay

    def paintEvent(self, e):
        # gentle window background (outside the card) for bloom/vignette
        theme = get_theme()
        grad = theme["gradient"]
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()
        g = QtGui.QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0.0, QtGui.QColor(grad[0]))
        g.setColorAt(1.0, QtGui.QColor(grad[1]))
        p.fillRect(r, g)
        accent_c = QtGui.QColor(theme["palette"]["accent_solid"])
        accent_c.setAlpha(50)
        rad = QtGui.QRadialGradient(r.center(), min(r.width(), r.height())*0.6)
        rad.setColorAt(0.0, accent_c)
        rad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.fillRect(r, rad)


# ------------------------------ Settings Dialog --------------------------------
class SettingsDialog(GlassDialog):
    def __init__(self, parent=None):
        super().__init__("Settings", parent)
        self.resize(560, 420)
        body = self.body_layout()

        tabs = QtWidgets.QTabWidget()
        body.addWidget(tabs, 1)

        # General tab
        gen = QtWidgets.QWidget(); gen_l = QtWidgets.QFormLayout(gen)
        gen_l.setContentsMargins(12, 12, 12, 12)
        gen_l.setSpacing(10)

        self.chk_animations = QtWidgets.QCheckBox("Enable subtle animations")
        self.chk_glow       = QtWidgets.QCheckBox("Enable neon glow")
        self.chk_animations.setChecked(True)
        self.chk_glow.setChecked(True)
        gen_l.addRow("Animations:", self.chk_animations)
        gen_l.addRow("Glow:", self.chk_glow)

        # Hotkeys tab
        hk = QtWidgets.QWidget(); hk_l = QtWidgets.QFormLayout(hk)
        hk_l.setContentsMargins(12, 12, 12, 12)
        hk_l.setSpacing(10)

        def key_edit(default_text):
            try:
                w = QtWidgets.QKeySequenceEdit()
                w.setKeySequence(QtGui.QKeySequence(default_text))
                return w, True
            except Exception:
                w = QtWidgets.QLineEdit(default_text)
                return w, False

        self.ed_toggle, self._is_seq_toggle = key_edit("X")
        self.ed_panic,  self._is_seq_panic  = key_edit("Shift+Esc")

        hk_l.addRow("Start/Stop:", self.ed_toggle)
        hk_l.addRow("Emergency Quit:", self.ed_panic)

        tabs.addTab(gen, "General")
        tabs.addTab(hk,  "Hotkeys")

        # footer
        foot = QtWidgets.QHBoxLayout()
        foot.addStretch(1)
        self.btn_ok = QtWidgets.QPushButton("Save")
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        foot.addWidget(self.btn_cancel)
        foot.addWidget(self.btn_ok)
        body.addLayout(foot)

    def values(self):
        def get_seq(widget, is_seq):
            if is_seq:
                seq = widget.keySequence()
                return seq.toString(QtGui.QKeySequence.NativeText)
            return widget.text().strip()
        return {
            "animations": self.chk_animations.isChecked(),
            "glow": self.chk_glow.isChecked(),
            "hotkeys": {
                "toggle": get_seq(self.ed_toggle, self._is_seq_toggle),   # e.g., "X"
                "panic":  get_seq(self.ed_panic,  self._is_seq_panic),    # e.g., "Shift+Esc"
            }
        }


# ------------------------------ Logs Panel -------------------------------------
class LogsPanel(GlassDialog):
    def __init__(self, parent=None):
        super().__init__("Logs", parent)
        self.resize(720, 420)
        body = self.body_layout()

        self.view = QtWidgets.QTextEdit()
        self.view.setReadOnly(True)
        self.view.setPlaceholderText("Logs will appear here…")
        theme = get_theme()
        tp = theme["palette"]
        self.view.setStyleSheet(
            f"QTextEdit{{color:{tp['text_primary']}; background:{tp['input_bg']};"
            f" border:1px solid {tp['input_border']}; border-radius:10px;}}"
        )

        btns = QtWidgets.QHBoxLayout()
        self.btn_copy  = QtWidgets.QPushButton("Copy all")
        self.btn_clear = QtWidgets.QPushButton("Clear")
        btns.addStretch(1); btns.addWidget(self.btn_clear); btns.addWidget(self.btn_copy)

        body.addWidget(self.view, 1)
        body.addLayout(btns)

        self.btn_clear.clicked.connect(self.view.clear)
        self.btn_copy.clicked.connect(self._copy_all)

    def append(self, text: str):
        self.view.append(text)

    def _copy_all(self):
        self.view.selectAll()
        self.view.copy()
        cursor = self.view.textCursor()
        cursor.clearSelection()
        self.view.setTextCursor(cursor)


# ------------------------------ Sidebar (with real buttons) --------------------
class NavButton(QtWidgets.QPushButton):
    def __init__(self, text: str, emoji: str, parent=None):
        super().__init__(f"{emoji}  {text}", parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setFlat(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QPushButton{
                text-align: left; padding:10px 12px;
                color:#e7edff; border-radius:12px; border: none;
                background: rgba(255,255,255,0.04);
            }
            QPushButton:hover{ background: rgba(255,255,255,0.10); }
            QPushButton:pressed{ background: rgba(255,255,255,0.14); }
        """)


class Sidebar(QtWidgets.QFrame):
    # streamlined signals
    sigHome     = QtCore.pyqtSignal()
    sigPresets  = QtCore.pyqtSignal()
    sigSettings = QtCore.pyqtSignal()
    sigLogs     = QtCore.pyqtSignal()
    sigAbout    = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(220)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 22, 18, 22)
        lay.setSpacing(10)

        # Logo
        logo = QtWidgets.QLabel(
            "<span style='font-size:16pt; font-weight:700;'>MT</span> "
            "<span style='color:#7bd1ff;'>AUTO</span><br><span>CLICKER</span>"
        )
        logo.setObjectName("logo")
        logo.setStyleSheet("QLabel{color:#cfe9ff;}")
        lay.addWidget(logo)

        # Buttons — these are REAL clickable buttons
        b = NavButton("Home", "🏠");    b.clicked.connect(self.sigHome);    lay.addWidget(b)
        b = NavButton("Presets", "🔁"); b.clicked.connect(self.sigPresets); lay.addWidget(b)
        b = NavButton("Settings", "⚙️");b.clicked.connect(self.sigSettings);lay.addWidget(b)
        b = NavButton("Logs", "🗂️");   b.clicked.connect(self.sigLogs);    lay.addWidget(b)
        b = NavButton("About", "ℹ️");  b.clicked.connect(self.sigAbout);   lay.addWidget(b)

        lay.addStretch(1)
