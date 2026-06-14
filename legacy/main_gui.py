"""
MT Auto Clicker — Neon Glass UI (PyQt5)
Recreates the look & feel of the provided screenshot:
- Left neon sidebar with icons and section list
- Top glass greeting/search bar with action icons
- 3×3 feature grid of rounded gradient cards with soft glow and subtle hover lift
- Deep blue/purple background with vignette & radial bloom
"""

import sys, os
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parent
# Add repository root (one level up) to sys.path so `import Main.*` works
REPO_ROOT = PROJECT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# page logic for grid swapping
from app.core.button_logic import ButtonLogic


# ------------------------------ Helpers ----------------------------------------
PRIMARY_BG = QtGui.QColor(8, 16, 40)
NEON_PURPLE = QtGui.QColor(138, 61, 255)
NEON_PINK = QtGui.QColor(255, 74, 182)
NEON_BLUE = QtGui.QColor(0, 160, 255)
CARD_DARK = QtGui.QColor(25, 32, 64, 220)
TEXT_DIM = QtGui.QColor(210, 220, 255, 200)


def round_rect_path(rect: QtCore.QRectF, radius: float) -> QtGui.QPainterPath:
    p = QtGui.QPainterPath()
    p.addRoundedRect(rect, radius, radius)
    return p


class GlowShadow(QtWidgets.QGraphicsDropShadowEffect):
    def __init__(self, color: QtGui.QColor, blur=40, offset=(0, 16)):
        super().__init__()
        self.setBlurRadius(blur)
        self.setOffset(*offset)
        self.setColor(color)


# ------------------------------ Feature Card -----------------------------------
class FeatureCard(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal(str, str)  # key, title

    def __init__(self, key: str, title: str, subtitle: str = "", icon: str = "cursor", gradient: str = "purple", parent=None):
        super().__init__(parent)
        self.key = key
        self.title = title
        self.subtitle = subtitle
        self.icon = icon
        self.gradient = gradient
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMinimumSize(220, 130)
        self.setMaximumHeight(150)
        self.setObjectName("featureCard")

        # Neon glow; animate its intensity on hover
        self._shadow = GlowShadow(QtGui.QColor(40, 80, 220, 110), blur=48, offset=(0, 18))
        self.setGraphicsEffect(self._shadow)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 20, 18, 16)
        lay.setSpacing(8)
        self.label = QtWidgets.QLabel(title)
        self.label.setObjectName("cardTitle")
        self.label.setWordWrap(True)
        self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)
        self.sub = QtWidgets.QLabel(subtitle)
        self.sub.setObjectName("cardSub")
        lay.addStretch(1)
        lay.addWidget(self.label)
        lay.addWidget(self.sub)

        self._hover = 0.0
        self._anim = QtCore.QPropertyAnimation(self, b"hover", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    def get_hover(self):
        return self._hover

    def set_hover(self, v):
        self._hover = float(v)
        blur = 48 + 10 * self._hover
        offset = 18 - 6 * self._hover
        alpha = 110 + int(60 * self._hover)
        c = self._shadow.color()
        c.setAlpha(alpha)
        self._shadow.setBlurRadius(blur)
        self._shadow.setOffset(0, offset)
        self._shadow.setColor(c)
        self.update()

    hover = QtCore.pyqtProperty(float, fget=get_hover, fset=set_hover)

    def enterEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(1.0); self._anim.start()
    def leaveEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(self._hover); self._anim.setEndValue(0.0); self._anim.start()
    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.key, self.title)

    def _icon_colors(self):
        if self.gradient == "purple":
            return QtGui.QColor(206, 146, 255), QtGui.QColor(123, 205, 255)
        if self.gradient == "blue":
            return QtGui.QColor(140, 190, 255), QtGui.QColor(170, 120, 255)
        return QtGui.QColor(255, 140, 220), QtGui.QColor(120, 200, 255)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()

        path = round_rect_path(QtCore.QRectF(0, 0, r.width(), r.height()), 20)
        if self.gradient == "purple":
            grad = QtGui.QLinearGradient(0, 0, r.width(), r.height())
            grad.setColorAt(0.0, QtGui.QColor(34, 28, 72, 235))
            grad.setColorAt(0.5, QtGui.QColor(76, 38, 128, 240))
            grad.setColorAt(1.0, QtGui.QColor(22, 28, 60, 235))
        elif self.gradient == "blue":
            grad = QtGui.QLinearGradient(0, 0, r.width(), r.height())
            grad.setColorAt(0.0, QtGui.QColor(22, 48, 92, 235))
            grad.setColorAt(0.6, QtGui.QColor(30, 70, 120, 240))
            grad.setColorAt(1.0, QtGui.QColor(20, 32, 72, 235))
        else:
            grad = QtGui.QLinearGradient(0, 0, r.width(), r.height())
            grad.setColorAt(0.0, QtGui.QColor(52, 20, 68, 235))
            grad.setColorAt(0.6, QtGui.QColor(100, 30, 120, 240))
            grad.setColorAt(1.0, QtGui.QColor(28, 24, 60, 235))
        p.fillPath(path, grad)

        gloss = QtGui.QLinearGradient(0, 0, 0, r.height())
        gloss.setColorAt(0.0, QtGui.QColor(255, 255, 255, int(24 + 36*self._hover)))
        gloss.setColorAt(0.48, QtGui.QColor(255, 255, 255, 0))
        gloss.setColorAt(1.0, QtGui.QColor(255, 255, 255, int(8 + 20*self._hover)))
        p.fillPath(path, gloss)

        c1, c2 = self._icon_colors()
        glow = QtGui.QRadialGradient(QtCore.QPointF(64, 52), 56)
        glow.setColorAt(0.0, QtGui.QColor(c1.red(), c1.green(), c1.blue(), 150))
        glow.setColorAt(1.0, QtGui.QColor(c2.red(), c2.green(), c2.blue(), 0))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QtCore.QPointF(64, 52), 56, 40)

        p.save()
        p.setPen(QtCore.Qt.NoPen)
        icon_c = QtGui.QColor(230, 236, 255)
        icon_c.setAlpha(240)
        p.setBrush(icon_c)
        if self.icon == "cursor":
            poly = QtGui.QPolygonF([
                QtCore.QPointF(12, 8), QtCore.QPointF(74, 32), QtCore.QPointF(52, 42),
                QtCore.QPointF(62, 78), QtCore.QPointF(44, 84), QtCore.QPointF(34, 48),
                QtCore.QPointF(12, 60)
            ])
            p.translate(24, 10)
            p.drawPolygon(poly)
        elif self.icon == "monitor":
            p.translate(26, 12)
            p.drawRoundedRect(8, 8, 76, 48, 8, 8)
            p.drawRect(42, 58, 12, 8)
        elif self.icon == "ahk":
            p.translate(26, 12)
            p.drawRoundedRect(10, 16, 64, 40, 6, 6)
            f = self.font(); f.setBold(True); f.setPointSize(10); p.setFont(f)
            p.setPen(QtGui.QColor(24, 18, 52))
            p.drawText(QtCore.QRect(10, 16, 64, 40), QtCore.Qt.AlignCenter, "AHK")
        p.restore()

        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 35 + int(40*self._hover)))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawPath(path)


# ------------------------------ Sidebar ----------------------------------------
class Sidebar(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setMinimumWidth(220)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 22, 18, 22)
        lay.setSpacing(14)

        # Logo
        logo = QtWidgets.QLabel("<span style='font-size:16pt; font-weight:700;'>MT</span> <span style='color:#7bd1ff;'>AUTO</span><br><span>CLICKER</span>")
        logo.setObjectName("logo")
        lay.addWidget(logo)

        # Nav items
        def nav_item(text, active=False):
            w = QtWidgets.QFrame()
            w.setObjectName("navActive" if active else "nav")
            h = QtWidgets.QHBoxLayout(w)
            h.setContentsMargins(12, 10, 12, 10)
            icon = QtWidgets.QLabel("🏠" if text=="Home" else "⚙️" if text=="Settings" else "🔁" if text=="Preset" else "💳" if text=="Plans & Pricing" else "🔑" if text=="Tokens" else "🔐")
            icon.setFixedWidth(24)
            h.addWidget(icon)
            lbl = QtWidgets.QLabel(text)
            h.addWidget(lbl, 1)
            return w

        lay.addWidget(nav_item("Home", True))
        lay.addWidget(nav_item("Preset"))
        lay.addWidget(nav_item("Settings"))
        lay.addWidget(nav_item("Tokens"))
        lay.addWidget(nav_item("Plans & Pricing"))
        lay.addStretch(1)
        lay.addWidget(nav_item("Log in"))


# ------------------------------ Topbar -----------------------------------------
class Topbar(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("topbar")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        self.greet = QtWidgets.QLabel("Hi, MT Auto Clicker")
        self.greet.setObjectName("greet")
        self.greet.setStyleSheet("font-weight:600;")

        lay.addWidget(self.greet)
        lay.addStretch(1)

        # Right icons
        for sym in ("🔔", "🗂️"):
            b = QtWidgets.QToolButton()
            b.setText(sym)
            b.setObjectName("iconBtn")
            lay.addWidget(b)

        # Search
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search…")
        self.search.setObjectName("search")
        self.search.setFixedWidth(220)
        lay.addWidget(self.search)


# ------------------------------ Main Window ------------------------------------
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MT Auto Clicker — Neon UI")
        self.resize(1060, 720)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        # Right area
        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        root.addLayout(right, 1)

        self.topbar = Topbar()
        right.addWidget(self.topbar)

        # Grid area container (rounded)
        self.gridContainer = QtWidgets.QFrame()
        self.gridContainer.setObjectName("gridContainer")
        right.addWidget(self.gridContainer, 1)

        # Persistent GridLayout the ButtonLogic can clear
        self.gridLay = QtWidgets.QGridLayout(self.gridContainer)
        self.gridLay.setContentsMargins(6, 6, 6, 6)
        self.gridLay.setHorizontalSpacing(16)
        self.gridLay.setVerticalSpacing(16)

        # Page logic helper (operates only on the grid area)
        self.logic = ButtonLogic(self.gridLay, on_back=self.build_grid)

        # initial dashboard
        self.build_grid()
        self._apply_styles()




    def build_grid(self):
        """Rebuild the 3x3 feature dashboard in the grid area."""
        self.logic.clear_grid()
        cards = [
            ("single", "Single Target Clicking", "cursor", "purple"),
            ("multi", "Multi Target Clicking", "cursor", "purple"),
            ("macro", "Macro Recoder", "monitor", "blue"),
            ("scroll", "Auto Scroll", "cursor", "blue"),
            ("hotkey", "Auto Hotkey", "ahk", "purple"),
            ("refresh", "Auto Refresh", "cursor", "blue"),
            ("swipe", "Auto Swipe", "cursor", "purple"),
            ("capture", "Capture Screenshot/Screen Recording", "monitor", "blue"),
            ("hold", "Touch and Hold", "cursor", "purple"),
        ]
        pos = 0
        for r in range(3):
            for c in range(3):
                key, title, ic, g = cards[pos]
                card = FeatureCard(key, title, "", ic, g)
                card.clicked.connect(self.on_card_clicked)
                self.gridLay.addWidget(card, r, c)
                pos += 1

    def on_card_clicked(self, key: str, title: str):
        """When a feature card is clicked, replace only the grid with a new page."""
        self.logic.show_feature(key, title)

    def paintEvent(self, e):
        """Window background with deep gradient + vignette + bloom."""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()

        # Base vertical gradient
        g = QtGui.QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0.0, QtGui.QColor(10, 16, 40))
        g.setColorAt(0.5, QtGui.QColor(12, 20, 52))
        g.setColorAt(1.0, QtGui.QColor(6, 10, 28))
        p.fillRect(r, g)

        # Purple/blue radial glow center
        rad = QtGui.QRadialGradient(r.center(), min(r.width(), r.height()) * 0.6)
        rad.setColorAt(0.0, QtGui.QColor(140, 70, 255, 90))
        rad.setColorAt(0.5, QtGui.QColor(70, 120, 255, 60))
        rad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p.fillRect(r, rad)

        # Vignette
        vign = QtGui.QRadialGradient(r.center(), max(r.width(), r.height()))
        vign.setColorAt(0.7, QtGui.QColor(0, 0, 0, 0))
        vign.setColorAt(1.0, QtGui.QColor(0, 0, 0, 140))
        p.fillRect(r, vign)

    def _apply_styles(self):
        self.setStyleSheet(
            """
            /* Sidebar */
            QFrame#sidebar { border-radius: 18px; background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(18,28,60,220), stop:1 rgba(12,20,48,220)); }
            QLabel#logo { color: #cfe9ff; }
            QFrame#nav, QFrame#navActive { border-radius: 12px; }
            QFrame#nav { background: rgba(255,255,255,0.04); }
            QFrame#nav:hover { background: rgba(255,255,255,0.10); }
            QFrame#navActive { background: rgba(80,140,255,0.18); }

            /* Topbar */
            QFrame#topbar { border-radius: 16px; background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(28,36,84,230), stop:1 rgba(22,28,64,230)); }
            #greet { color: #dce6ff; }
            QLineEdit#search { border-radius: 12px; padding: 8px 12px; color: #e7edff;
                background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10); }
            QToolButton#iconBtn { border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding:6px;
                background: rgba(255,255,255,0.06); color: #e7edff; }
            QToolButton#iconBtn:hover { background: rgba(255,255,255,0.12); }

            /* Grid container (transparent to let background show) */
            QFrame#gridContainer { background: transparent; }

            /* Card texts */
            QLabel#cardTitle { color: #e8ecff; font-weight: 600; }
            QLabel#cardSub { color: rgba(220,230,255,0.75); font-size: 10pt; }
            """
        )


