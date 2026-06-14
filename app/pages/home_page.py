from __future__ import annotations

import hmac
import os
import random

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QComboBox, QCheckBox, QScrollArea, QFrame,
    QStackedWidget, QSlider, QLineEdit, QDialog,
)

from app.styling.localization import tr
from app.styling.themes import get_theme, get_dialog_stylesheet
from app.gui.widgets import Card, add_shadow, FocusClearSpinBox, XPBar, CPSSparkline

_SECRET_PASS = (os.getenv("MTA_ADMIN_PASSWORD") or "").strip()


class _GrabDialog(QDialog):
    """Modal dialog that captures the F key and records the cursor position."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grabbed_pos: tuple | None = None
        self.setWindowTitle("\U0001f3af Grab Coordinates")
        self.setFixedSize(340, 120)
        self.setStyleSheet(get_dialog_stylesheet())
        lay = QVBoxLayout(self)
        lbl = QLabel("Move your mouse to the desired position,\nthen press  F  to capture the coordinates.")
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl)

    # -- Qt key capture (no pynput needed) ---------------------------------
    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_F:
            pos = QCursor.pos()
            self.grabbed_pos = (pos.x(), pos.y())
            self.accept()
        elif ev.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(ev)


class HomePage(QWidget):
    admin_activated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stop_mode = "never"
        self.selected_button = "left"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # Hero card
        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=28, y=10, alpha=110)
        hero_l = QHBoxLayout(hero)
        hero_l.setContentsMargins(28, 22, 28, 22)
        hero_l.setSpacing(18)

        self.status_label = QLabel(tr("stopped"))
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setProperty("running", False)

        self.btn_start_stop = QPushButton(tr("start"))
        self.btn_start_stop.setObjectName("StartStopBtn")
        self.btn_start_stop.setCursor(Qt.PointingHandCursor)
        self.btn_start_stop.setFixedHeight(46)
        self.btn_start_stop.setMinimumWidth(180)
        self.btn_start_stop.setProperty("running", False)

        left = QVBoxLayout()
        left.setSpacing(10)
        self.h_title = QLabel(tr("single_target"))
        self.h_title.setObjectName("HeroTitle")
        self.h_sub = QLabel(tr("single_target_sub"))
        self.h_sub.setObjectName("HeroSub")
        left.addWidget(self.h_title)
        left.addWidget(self.h_sub)
        left.addWidget(self.status_label)
        left.addStretch(1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.addWidget(self.btn_start_stop, 0, Qt.AlignRight)
        right_col.addStretch(1)

        hero_l.addLayout(left, 1)
        hero_l.addLayout(right_col, 0)

        # Lower grid
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        # Left card - Event Timing
        card_left = Card()
        card_left.setObjectName("ConfigCard")
        add_shadow(card_left, blur=26, y=10, alpha=110)
        cl = QVBoxLayout(card_left)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(14)

        header_l = QHBoxLayout()
        header_l.setSpacing(10)
        icon_clock = QLabel("⏱")
        icon_clock.setObjectName("HeaderIcon")
        icon_clock.setFixedSize(34, 34)
        icon_clock.setAlignment(Qt.AlignCenter)
        self.lbl_event = QLabel(tr("event_timing"))
        self.lbl_event.setObjectName("CardHeader")
        header_l.addWidget(icon_clock)
        header_l.addWidget(self.lbl_event)
        header_l.addStretch(1)
        cl.addLayout(header_l)

        inner = Card(radius=16)
        inner.setObjectName("InnerPanel")
        in_l = QVBoxLayout(inner)
        in_l.setContentsMargins(14, 14, 14, 14)
        in_l.setSpacing(12)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(10)
        self.btn_never_stop = QPushButton("●   " + tr("never_stop"))
        self.btn_never_stop.setObjectName("ToggleButton")
        self.btn_never_stop.setFlat(True)
        self.btn_never_stop.setProperty("active", True)
        self.btn_never_stop.setCursor(Qt.PointingHandCursor)
        self.btn_never_stop.setFixedHeight(40)
        self.btn_never_stop.clicked.connect(lambda: self._set_stop_mode("never"))
        self.btn_num_cycles = QPushButton("●   " + tr("num_cycles"))
        self.btn_num_cycles.setObjectName("ToggleButton")
        self.btn_num_cycles.setFlat(True)
        self.btn_num_cycles.setProperty("active", False)
        self.btn_num_cycles.setCursor(Qt.PointingHandCursor)
        self.btn_num_cycles.setFixedHeight(40)
        self.btn_num_cycles.clicked.connect(lambda: self._set_stop_mode("cycles"))
        self.btn_time_gated = QPushButton("●   " + tr("time_gated"))
        self.btn_time_gated.setObjectName("ToggleButton")
        self.btn_time_gated.setFlat(True)
        self.btn_time_gated.setProperty("active", False)
        self.btn_time_gated.setCursor(Qt.PointingHandCursor)
        self.btn_time_gated.setFixedHeight(40)
        self.btn_time_gated.clicked.connect(lambda: self._set_stop_mode("timed"))
        toggle_row.addWidget(self.btn_never_stop)
        toggle_row.addWidget(self.btn_num_cycles)
        toggle_row.addWidget(self.btn_time_gated)

        # Stacked content for each mode
        self.mode_stack = QStackedWidget()

        # Page 0 – Never Stop: fun facts
        self._fun_facts = [
            "A group of flamingos is called a 'flamboyance'.",
            "Honey never spoils. Archaeologists found 3000-year-old honey in Egyptian tombs — still edible!",
            "Octopuses have three hearts and blue blood.",
            "Bananas are berries, but strawberries aren't.",
            "A day on Venus is longer than a year on Venus.",
            "Cows have best friends and get stressed when separated.",
            "The inventor of the Pringles can is buried in one.",
            "There are more possible chess games than atoms in the observable universe.",
            "Wombat poop is cube-shaped.",
            "Sea otters hold hands while sleeping so they don't drift apart.",
            "The shortest war in history lasted 38 minutes (Britain vs Zanzibar).",
            "A jiffy is an actual unit of time: 1/100th of a second.",
            "Sloths can hold their breath longer than dolphins — up to 40 minutes!",
            "The dot over the letters 'i' and 'j' is called a tittle.",
        ]
        fun_page = QWidget()
        fun_lay = QVBoxLayout(fun_page)
        fun_lay.setContentsMargins(4, 4, 4, 4)
        fun_lay.setSpacing(8)
        self.fun_fact_label = QLabel(random.choice(self._fun_facts))
        self.fun_fact_label.setObjectName("FunFact")
        self.fun_fact_label.setWordWrap(True)
        self.btn_new_fact = QPushButton(tr("another_fact"))
        self.btn_new_fact.setObjectName("ToggleButton")
        self.btn_new_fact.setFlat(True)
        self.btn_new_fact.setProperty("active", False)
        self.btn_new_fact.setCursor(Qt.PointingHandCursor)
        self.btn_new_fact.setFixedHeight(34)
        self.btn_new_fact.clicked.connect(self._show_new_fact)
        fun_lay.addWidget(self.fun_fact_label)
        fun_lay.addWidget(self.btn_new_fact, 0, Qt.AlignLeft)
        fun_lay.addStretch(1)
        self.mode_stack.addWidget(fun_page)  # index 0

        # Page 1 – Number of Cycles
        cycles_page = QWidget()
        cyc_page_lay = QVBoxLayout(cycles_page)
        cyc_page_lay.setContentsMargins(4, 4, 4, 4)
        cyc_page_lay.setSpacing(8)
        cycles = Card(radius=12)
        cycles.setObjectName("CycleBox")
        cyc_l = QHBoxLayout(cycles)
        cyc_l.setContentsMargins(10, 8, 10, 8)
        cyc_l.setSpacing(10)
        self.spin_cycles = FocusClearSpinBox()
        self.spin_cycles.setObjectName("TimeSpin")
        self.spin_cycles.setRange(1, 999999)
        self.spin_cycles.setValue(100)
        self.spin_cycles.setFixedWidth(80)
        self.spin_cycles.setAlignment(Qt.AlignCenter)
        cyc_lbl = QLabel("Number of cycles")
        cyc_lbl.setObjectName("TimeUnit")
        cyc_l.addWidget(self.spin_cycles)
        cyc_l.addWidget(cyc_lbl)
        cyc_l.addStretch(1)
        cyc_page_lay.addWidget(cycles)
        cyc_page_lay.addStretch(1)
        self.mode_stack.addWidget(cycles_page)  # index 1

        # Page 2 – Time Gated
        time_page = QWidget()
        time_page_lay = QVBoxLayout(time_page)
        time_page_lay.setContentsMargins(4, 4, 4, 4)
        time_page_lay.setSpacing(8)
        time_row = QHBoxLayout()
        time_row.setSpacing(10)
        def time_input_box(label: str, max_val: int = 99):
            w = Card(radius=12)
            w.setObjectName("TimeBox")
            lay2 = QHBoxLayout(w)
            lay2.setContentsMargins(10, 8, 10, 8)
            lay2.setSpacing(10)
            spin = FocusClearSpinBox()
            spin.setObjectName("TimeSpin")
            spin.setRange(0, max_val)
            spin.setValue(0)
            spin.setFixedWidth(50)
            spin.setAlignment(Qt.AlignCenter)
            lbl = QLabel(label)
            lbl.setObjectName("TimeUnit")
            lay2.addWidget(spin)
            lay2.addWidget(lbl)
            return w, spin

        h_box, self.spin_hours = time_input_box("h", 23)
        m_box, self.spin_minutes = time_input_box("m", 59)
        s_box, self.spin_seconds = time_input_box("s", 59)
        ms_box, self.spin_milliseconds = time_input_box("ms", 999)

        for sp in (self.spin_hours, self.spin_minutes, self.spin_seconds, self.spin_milliseconds):
            sp.valueChanged.connect(self._sync_time_to_interval)

        time_row.addWidget(h_box)
        time_row.addWidget(m_box)
        time_row.addWidget(s_box)
        time_row.addWidget(ms_box)
        time_page_lay.addLayout(time_row)
        time_page_lay.addStretch(1)
        self.mode_stack.addWidget(time_page)  # index 2

        in_l.addLayout(toggle_row)
        in_l.addWidget(self.mode_stack)
        cl.addWidget(inner)
        cl.addStretch(1)

        # Right card - Clicking Interval
        card_right = Card()
        card_right.setObjectName("ConfigCard")
        add_shadow(card_right, blur=26, y=10, alpha=110)
        cr = QVBoxLayout(card_right)
        cr.setContentsMargins(20, 18, 20, 18)
        cr.setSpacing(14)

        header_r = QHBoxLayout()
        header_r.setSpacing(10)
        icon_hourglass = QLabel("⌛")
        icon_hourglass.setObjectName("HeaderIcon")
        icon_hourglass.setFixedSize(34, 34)
        icon_hourglass.setAlignment(Qt.AlignCenter)
        self.lbl_int = QLabel(tr("clicking_interval"))
        self.lbl_int.setObjectName("CardHeader")
        header_r.addWidget(icon_hourglass)
        header_r.addWidget(self.lbl_int)
        header_r.addStretch(1)
        cr.addLayout(header_r)

        inner2 = Card(radius=16)
        inner2.setObjectName("InnerPanel")
        in2 = QVBoxLayout(inner2)
        in2.setContentsMargins(14, 14, 14, 14)
        in2.setSpacing(12)
        self.lbl_time_interval = QLabel(tr("time_interval"))
        self.lbl_time_interval.setObjectName("InnerTitle")

        row = QHBoxLayout()
        row.setSpacing(10)
        self.spin_interval = FocusClearSpinBox()
        self.spin_interval.setObjectName("TimeSpin")
        self.spin_interval.setRange(1, 86400000)
        self.spin_interval.setValue(100)
        self.spin_interval.setFixedHeight(40)
        self.spin_interval.secret_code_entered.connect(self._ask_admin_password)
        self.unit_combo = QComboBox()
        self.unit_combo.setObjectName("UnitDrop")
        self.unit_combo.addItems(["Milliseconds", "Seconds", "Minutes", "Hours"])
        self.unit_combo.setFixedHeight(40)
        row.addWidget(self.spin_interval, 1)
        row.addWidget(self.unit_combo, 1)

        self.lbl_warn = QLabel(tr("warn_interval"))
        self.lbl_warn.setObjectName("WarnText")
        in2.addWidget(self.lbl_time_interval)
        in2.addLayout(row)
        in2.addWidget(self.lbl_warn)

        # CPS stabilization toggle
        self.chk_cps_stabilize = QCheckBox("Auto-stabilize CPS")
        self.chk_cps_stabilize.setToolTip(
            "Automatically adjusts click delay to match the target CPS.\n"
            "Compensates for system lag and click overhead."
        )
        self.chk_cps_stabilize.setChecked(True)
        self.chk_cps_stabilize.setEnabled(False)
        self.chk_cps_stabilize.setText("Auto-stabilize CPS (Always On)")
        self.lbl_cps_drift = QLabel("")
        self.lbl_cps_drift.setObjectName("WarnText")
        self.lbl_cps_drift.setWordWrap(True)
        self.lbl_cps_drift.setVisible(False)
        in2.addWidget(self.chk_cps_stabilize)
        in2.addWidget(self.lbl_cps_drift)

        in2.addStretch(1)
        cr.addWidget(inner2)
        cr.addStretch(1)

        # Bottom card - Mouse Button Selector
        card_mouse = Card()
        card_mouse.setObjectName("ConfigCard")
        add_shadow(card_mouse, blur=26, y=10, alpha=110)
        cm = QVBoxLayout(card_mouse)
        cm.setContentsMargins(20, 18, 20, 18)
        cm.setSpacing(14)

        header_m = QHBoxLayout()
        header_m.setSpacing(10)
        icon_mouse = QLabel("🖱")
        icon_mouse.setObjectName("HeaderIcon")
        icon_mouse.setFixedSize(34, 34)
        icon_mouse.setAlignment(Qt.AlignCenter)
        self.lbl_mouse = QLabel(tr("mouse_button"))
        self.lbl_mouse.setObjectName("CardHeader")
        header_m.addWidget(icon_mouse)
        header_m.addWidget(self.lbl_mouse)
        header_m.addStretch(1)
        cm.addLayout(header_m)

        mouse_inner = Card(radius=16)
        mouse_inner.setObjectName("InnerPanel")
        mouse_il = QVBoxLayout(mouse_inner)
        mouse_il.setContentsMargins(14, 14, 14, 14)
        mouse_il.setSpacing(8)

        self.btn_left_click = QPushButton("🖱  " + tr("left_click"))
        self.btn_left_click.setObjectName("ToggleButton")
        self.btn_left_click.setFlat(True)
        self.btn_left_click.setProperty("active", True)
        self.btn_left_click.setCursor(Qt.PointingHandCursor)
        self.btn_left_click.setFixedHeight(38)
        self.btn_left_click.clicked.connect(lambda: self._select_button("left"))

        self.btn_right_click = QPushButton("🖱  " + tr("right_click"))
        self.btn_right_click.setObjectName("ToggleButton")
        self.btn_right_click.setFlat(True)
        self.btn_right_click.setProperty("active", False)
        self.btn_right_click.setCursor(Qt.PointingHandCursor)
        self.btn_right_click.setFixedHeight(38)
        self.btn_right_click.clicked.connect(lambda: self._select_button("right"))

        self.btn_middle_click = QPushButton("🖱  " + tr("middle_click"))
        self.btn_middle_click.setObjectName("ToggleButton")
        self.btn_middle_click.setFlat(True)
        self.btn_middle_click.setProperty("active", False)
        self.btn_middle_click.setCursor(Qt.PointingHandCursor)
        self.btn_middle_click.setFixedHeight(38)
        self.btn_middle_click.clicked.connect(lambda: self._select_button("middle"))

        mouse_il.addWidget(self.btn_left_click)
        mouse_il.addWidget(self.btn_right_click)
        mouse_il.addWidget(self.btn_middle_click)
        cm.addWidget(mouse_inner)
        cm.addStretch(1)

        grid.addWidget(card_left, 0, 0)
        grid.addWidget(card_right, 0, 1)
        grid.addWidget(card_mouse, 1, 0, 1, 2)

        # -- Click Position card --
        card_pos = Card()
        card_pos.setObjectName("ConfigCard")
        add_shadow(card_pos, blur=26, y=10, alpha=110)
        cp = QVBoxLayout(card_pos)
        cp.setContentsMargins(20, 18, 20, 18)
        cp.setSpacing(14)

        header_p = QHBoxLayout()
        header_p.setSpacing(10)
        icon_pos = QLabel("📍")
        icon_pos.setObjectName("HeaderIcon")
        icon_pos.setFixedSize(34, 34)
        icon_pos.setAlignment(Qt.AlignCenter)
        self.lbl_pos = QLabel(tr("click_position"))
        self.lbl_pos.setObjectName("CardHeader")
        header_p.addWidget(icon_pos)
        header_p.addWidget(self.lbl_pos)
        header_p.addStretch(1)
        cp.addLayout(header_p)

        inner_pos = Card(radius=16)
        inner_pos.setObjectName("InnerPanel")
        ip_l = QVBoxLayout(inner_pos)
        ip_l.setContentsMargins(14, 14, 14, 14)
        ip_l.setSpacing(12)

        pos_toggle = QHBoxLayout()
        pos_toggle.setSpacing(10)
        self.btn_follow_mouse = QPushButton("●   " + tr("follow_mouse"))
        self.btn_follow_mouse.setObjectName("ToggleButton")
        self.btn_follow_mouse.setFlat(True)
        self.btn_follow_mouse.setProperty("active", True)
        self.btn_follow_mouse.setCursor(Qt.PointingHandCursor)
        self.btn_follow_mouse.setFixedHeight(38)
        self.btn_follow_mouse.clicked.connect(lambda: self._set_position_mode("follow"))

        self.btn_custom_pos = QPushButton("●   " + tr("custom_position"))
        self.btn_custom_pos.setObjectName("ToggleButton")
        self.btn_custom_pos.setFlat(True)
        self.btn_custom_pos.setProperty("active", False)
        self.btn_custom_pos.setCursor(Qt.PointingHandCursor)
        self.btn_custom_pos.setFixedHeight(38)
        self.btn_custom_pos.clicked.connect(lambda: self._set_position_mode("custom"))

        pos_toggle.addWidget(self.btn_follow_mouse)
        pos_toggle.addWidget(self.btn_custom_pos)
        ip_l.addLayout(pos_toggle)

        # Custom position inputs (hidden by default)
        self.pos_inputs = QWidget()
        pos_in_lay = QHBoxLayout(self.pos_inputs)
        pos_in_lay.setContentsMargins(0, 4, 0, 0)
        pos_in_lay.setSpacing(10)

        x_box = Card(radius=12)
        x_box.setObjectName("TimeBox")
        xb_l = QHBoxLayout(x_box)
        xb_l.setContentsMargins(10, 8, 10, 8)
        xb_l.setSpacing(8)
        self.spin_pos_x = FocusClearSpinBox()
        self.spin_pos_x.setObjectName("TimeSpin")
        self.spin_pos_x.setRange(0, 9999)
        self.spin_pos_x.setValue(960)
        self.spin_pos_x.setFixedWidth(70)
        self.spin_pos_x.setAlignment(Qt.AlignCenter)
        lbl_x = QLabel("X")
        lbl_x.setObjectName("TimeUnit")
        xb_l.addWidget(self.spin_pos_x)
        xb_l.addWidget(lbl_x)

        y_box = Card(radius=12)
        y_box.setObjectName("TimeBox")
        yb_l = QHBoxLayout(y_box)
        yb_l.setContentsMargins(10, 8, 10, 8)
        yb_l.setSpacing(8)
        self.spin_pos_y = FocusClearSpinBox()
        self.spin_pos_y.setObjectName("TimeSpin")
        self.spin_pos_y.setRange(0, 9999)
        self.spin_pos_y.setValue(540)
        self.spin_pos_y.setFixedWidth(70)
        self.spin_pos_y.setAlignment(Qt.AlignCenter)
        lbl_y = QLabel("Y")
        lbl_y.setObjectName("TimeUnit")
        yb_l.addWidget(self.spin_pos_y)
        yb_l.addWidget(lbl_y)

        self.btn_grab_coords = QPushButton("\U0001f3af  Grab")
        self.btn_grab_coords.setObjectName("ToggleButton")
        self.btn_grab_coords.setFlat(True)
        self.btn_grab_coords.setProperty("active", True)
        self.btn_grab_coords.setCursor(Qt.PointingHandCursor)
        self.btn_grab_coords.setFixedHeight(38)
        self.btn_grab_coords.setFixedWidth(90)
        self.btn_grab_coords.clicked.connect(self._start_grab_coords)

        pos_in_lay.addWidget(x_box)
        pos_in_lay.addWidget(y_box)
        pos_in_lay.addWidget(self.btn_grab_coords)
        pos_in_lay.addStretch(1)
        self.pos_inputs.setVisible(False)
        ip_l.addWidget(self.pos_inputs)

        self.pos_hint = QLabel(tr("follow_hint"))
        self.pos_hint.setObjectName("WarnText")
        self.pos_hint.setWordWrap(True)
        ip_l.addWidget(self.pos_hint)
        ip_l.addStretch(1)
        cp.addWidget(inner_pos)
        cp.addStretch(1)

        self.position_mode = "follow"
        grid.addWidget(card_pos, 2, 0, 1, 2)

        # -- Scroll Wheel Automation card --
        card_scroll = Card()
        card_scroll.setObjectName("ConfigCard")
        add_shadow(card_scroll, blur=26, y=10, alpha=110)
        cs_lay = QVBoxLayout(card_scroll)
        cs_lay.setContentsMargins(20, 18, 20, 18)
        cs_lay.setSpacing(14)

        sh_h = QHBoxLayout()
        sh_h.setSpacing(10)
        sh_icon = QLabel("🔄")
        sh_icon.setObjectName("HeaderIcon")
        sh_icon.setFixedSize(34, 34)
        sh_icon.setAlignment(Qt.AlignCenter)
        self.sh_lbl = QLabel(tr("scroll_automation"))
        self.sh_lbl.setObjectName("CardHeader")
        sh_h.addWidget(sh_icon)
        sh_h.addWidget(self.sh_lbl)
        sh_h.addStretch(1)
        cs_lay.addLayout(sh_h)

        inner_sc = Card(radius=16)
        inner_sc.setObjectName("InnerPanel")
        isc_lay = QVBoxLayout(inner_sc)
        isc_lay.setContentsMargins(14, 14, 14, 14)
        isc_lay.setSpacing(10)

        self.chk_scroll = QCheckBox(tr("scroll_enable"))
        isc_lay.addWidget(self.chk_scroll)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(10)
        lbl_dir = QLabel("Direction:")
        lbl_dir.setObjectName("TimeUnit")
        self.combo_scroll_dir = QComboBox()
        self.combo_scroll_dir.setObjectName("UnitDrop")
        self.combo_scroll_dir.addItems(["Up", "Down"])
        self.combo_scroll_dir.setFixedHeight(36)
        dir_row.addWidget(lbl_dir)
        dir_row.addWidget(self.combo_scroll_dir, 1)
        isc_lay.addLayout(dir_row)

        amt_row = QHBoxLayout()
        amt_row.setSpacing(10)
        lbl_amt = QLabel("Amount:")
        lbl_amt.setObjectName("TimeUnit")
        self.spin_scroll_amt = FocusClearSpinBox()
        self.spin_scroll_amt.setObjectName("TimeSpin")
        self.spin_scroll_amt.setRange(1, 100)
        self.spin_scroll_amt.setValue(3)
        self.spin_scroll_amt.setFixedHeight(36)
        amt_row.addWidget(lbl_amt)
        amt_row.addWidget(self.spin_scroll_amt, 1)
        isc_lay.addLayout(amt_row)
        isc_lay.addStretch(1)
        cs_lay.addWidget(inner_sc)
        cs_lay.addStretch(1)

        grid.addWidget(card_scroll, 3, 0)

        # -- Multi-Button Combo card --
        card_combo = Card()
        card_combo.setObjectName("ConfigCard")
        add_shadow(card_combo, blur=26, y=10, alpha=110)
        cb_lay = QVBoxLayout(card_combo)
        cb_lay.setContentsMargins(20, 18, 20, 18)
        cb_lay.setSpacing(14)

        cb_h = QHBoxLayout()
        cb_h.setSpacing(10)
        cb_icon = QLabel("🎮")
        cb_icon.setObjectName("HeaderIcon")
        cb_icon.setFixedSize(34, 34)
        cb_icon.setAlignment(Qt.AlignCenter)
        self.cb_lbl = QLabel(tr("multi_button"))
        self.cb_lbl.setObjectName("CardHeader")
        cb_h.addWidget(cb_icon)
        cb_h.addWidget(self.cb_lbl)
        cb_h.addStretch(1)
        cb_lay.addLayout(cb_h)

        inner_cb = Card(radius=16)
        inner_cb.setObjectName("InnerPanel")
        icb_lay = QVBoxLayout(inner_cb)
        icb_lay.setContentsMargins(14, 14, 14, 14)
        icb_lay.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        lbl_mode = QLabel("Combo Mode:")
        lbl_mode.setObjectName("TimeUnit")
        self.combo_mode_sel = QComboBox()
        self.combo_mode_sel.setObjectName("UnitDrop")
        self.combo_mode_sel.addItems(["Single (normal)", "Alternate (cycle)", "Double (all at once)"])
        self.combo_mode_sel.setFixedHeight(36)
        mode_row.addWidget(lbl_mode)
        mode_row.addWidget(self.combo_mode_sel, 1)
        icb_lay.addLayout(mode_row)

        self.chk_combo_left = QCheckBox("Left")
        self.chk_combo_left.setChecked(True)
        self.chk_combo_right = QCheckBox("Right")
        self.chk_combo_middle = QCheckBox("Middle")
        btn_check_row = QHBoxLayout()
        btn_check_row.setSpacing(14)
        btn_check_row.addWidget(self.chk_combo_left)
        btn_check_row.addWidget(self.chk_combo_right)
        btn_check_row.addWidget(self.chk_combo_middle)
        btn_check_row.addStretch(1)
        icb_lay.addLayout(btn_check_row)

        self.combo_hint = QLabel(tr("combo_hint"))
        self.combo_hint.setObjectName("WarnText")
        self.combo_hint.setWordWrap(True)
        icb_lay.addWidget(self.combo_hint)
        icb_lay.addStretch(1)
        cb_lay.addWidget(inner_cb)
        cb_lay.addStretch(1)

        grid.addWidget(card_combo, 3, 1)

        # -- Position Offset slider card --
        card_offset = Card()
        card_offset.setObjectName("ConfigCard")
        add_shadow(card_offset, blur=26, y=10, alpha=110)
        co_lay = QVBoxLayout(card_offset)
        co_lay.setContentsMargins(20, 18, 20, 18)
        co_lay.setSpacing(14)

        co_h = QHBoxLayout()
        co_h.setSpacing(10)
        co_icon = QLabel("↔")
        co_icon.setObjectName("HeaderIcon")
        co_icon.setFixedSize(34, 34)
        co_icon.setAlignment(Qt.AlignCenter)
        self.co_lbl = QLabel(tr("position_offset"))
        self.co_lbl.setObjectName("CardHeader")
        co_h.addWidget(co_icon)
        co_h.addWidget(self.co_lbl)
        co_h.addStretch(1)
        co_lay.addLayout(co_h)

        inner_co = Card(radius=16)
        inner_co.setObjectName("InnerPanel")
        ico_lay = QHBoxLayout(inner_co)
        ico_lay.setContentsMargins(14, 14, 14, 14)
        ico_lay.setSpacing(12)

        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setObjectName("Slider")
        self.offset_slider.setRange(0, 100)
        self.offset_slider.setValue(0)
        self.lbl_offset_val = QLabel("0 px")
        self.lbl_offset_val.setObjectName("TimeUnit")
        self.lbl_offset_val.setFixedWidth(50)
        self.offset_slider.valueChanged.connect(lambda v: self.lbl_offset_val.setText(f"{v} px"))
        ico_lay.addWidget(QLabel("± Offset"))
        ico_lay.addWidget(self.offset_slider, 1)
        ico_lay.addWidget(self.lbl_offset_val)
        co_lay.addWidget(inner_co)

        self.offset_hint = QLabel(tr("offset_hint"))
        self.offset_hint.setObjectName("WarnText")
        self.offset_hint.setWordWrap(True)
        co_lay.addWidget(self.offset_hint)
        co_lay.addStretch(1)

        grid.addWidget(card_offset, 4, 0, 1, 2)

        lay.addWidget(hero)

        # XP progress bar
        self.xp_bar = XPBar()
        lay.addWidget(self.xp_bar)

        # CPS sparkline
        spark_card = Card()
        spark_card.setObjectName("ConfigCard")
        add_shadow(spark_card, blur=20, y=6, alpha=80)
        spark_lay = QVBoxLayout(spark_card)
        spark_lay.setContentsMargins(16, 12, 16, 12)
        spark_lay.setSpacing(4)
        spark_header = QLabel("⚡  Live CPS")
        spark_header.setObjectName("SparkHeader")
        self.cps_spark = CPSSparkline(max_points=60)
        spark_lay.addWidget(spark_header)
        spark_lay.addWidget(self.cps_spark)
        lay.addWidget(spark_card)

        lay.addLayout(grid)
        lay.addStretch(1)

    def _select_button(self, btn_name: str):
        self.selected_button = btn_name
        for btn, name in [
            (self.btn_left_click, "left"),
            (self.btn_right_click, "right"),
            (self.btn_middle_click, "middle"),
        ]:
            btn.setProperty("active", name == btn_name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def toggle_left_right_button(self):
        """Quick-swap between left and right click buttons."""
        if self.selected_button == "right":
            self._select_button("left")
            return "left"
        else:
            self._select_button("right")
            return "right"

    def toggle_both_buttons_mode(self):
        """Toggle a left+right all-at-once combo mode."""
        is_both_enabled = (
            self.combo_mode_sel.currentIndex() == 2
            and self.chk_combo_left.isChecked()
            and self.chk_combo_right.isChecked()
            and not self.chk_combo_middle.isChecked()
        )
        if is_both_enabled:
            self.combo_mode_sel.setCurrentIndex(0)
            return "Single"
        else:
            self.combo_mode_sel.setCurrentIndex(2)
            self.chk_combo_left.setChecked(True)
            self.chk_combo_right.setChecked(True)
            self.chk_combo_middle.setChecked(False)
            return "Both"

    def _set_position_mode(self, mode: str):
        self.position_mode = mode
        follow = mode == "follow"
        self.btn_follow_mouse.setProperty("active", follow)
        self.btn_custom_pos.setProperty("active", not follow)
        for b in (self.btn_follow_mouse, self.btn_custom_pos):
            b.style().unpolish(b)
            b.style().polish(b)
            b.update()
        self.pos_inputs.setVisible(not follow)

    def _start_grab_coords(self):
        """Show a dialog that captures 'F' key to grab mouse coordinates."""
        dlg = _GrabDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.grabbed_pos is not None:
            self.spin_pos_x.setValue(dlg.grabbed_pos[0])
            self.spin_pos_y.setValue(dlg.grabbed_pos[1])

    def get_position_config(self) -> tuple:
        """Return (use_fixed, x, y)."""
        if self.position_mode == "custom":
            return True, self.spin_pos_x.value(), self.spin_pos_y.value()
        return False, 0, 0

    def get_scroll_config(self) -> tuple:
        """Return (enabled, direction, amount)."""
        enabled = self.chk_scroll.isChecked()
        direction = self.combo_scroll_dir.currentText().lower()
        amount = self.spin_scroll_amt.value()
        return enabled, direction, amount

    def get_combo_config(self) -> tuple:
        """Return (combo_mode, buttons_list)."""
        idx = self.combo_mode_sel.currentIndex()
        mode_map = {0: "single", 1: "alternate", 2: "double"}
        mode = mode_map.get(idx, "single")
        buttons = []
        if self.chk_combo_left.isChecked():
            buttons.append("left")
        if self.chk_combo_right.isChecked():
            buttons.append("right")
        if self.chk_combo_middle.isChecked():
            buttons.append("middle")
        return mode, buttons

    def get_offset_px(self) -> int:
        return self.offset_slider.value()

    def get_cps_stabilize(self) -> bool:
        return True

    def show_cps_drift(self, target_cps: float, actual_cps: float,
                       accuracy: float = 0.0, correction_ms: float = 0.0):
        """Show current CPS drift info from the stabilizer."""
        diff = actual_cps - target_cps
        sign = "+" if diff >= 0 else ""
        palette = get_theme().get("palette", {})
        # Color the accuracy indicator
        if accuracy >= 95:
            acc_color = palette.get("running_color", "#9CFFB2")
        elif accuracy >= 80:
            acc_color = palette.get("accent_solid", palette.get("slider_handle", "#FFE080"))
        else:
            acc_color = palette.get("stopped_color", "#FF9C9C")
        self.lbl_cps_drift.setText(
            f"Target: {target_cps:.1f}  |  Actual: {actual_cps:.1f}  ({sign}{diff:.1f})  "
            f"<span style='color:{acc_color}'>● {accuracy:.0f}%</span>  "
            f"Correction: {correction_ms:+.1f}ms"
        )
        self.lbl_cps_drift.setVisible(True)

    def hide_cps_drift(self):
        self.lbl_cps_drift.setVisible(False)
        self.lbl_cps_drift.setText("")

    def _sync_time_to_interval(self):
        total_ms = (
            self.spin_hours.value() * 3600000
            + self.spin_minutes.value() * 60000
            + self.spin_seconds.value() * 1000
            + self.spin_milliseconds.value()
        )
        if total_ms > 0:
            self.spin_interval.blockSignals(True)
            self.spin_interval.setValue(total_ms)
            self.spin_interval.blockSignals(False)

    def _show_new_fact(self):
        self.fun_fact_label.setText(random.choice(self._fun_facts))

    def _set_stop_mode(self, mode: str):
        if self.stop_mode == mode:
            return
        self.stop_mode = mode
        self._update_toggle_buttons()

    def _update_toggle_buttons(self):
        mode = self.stop_mode
        for btn, m in [
            (self.btn_never_stop, "never"),
            (self.btn_num_cycles, "cycles"),
            (self.btn_time_gated, "timed"),
        ]:
            btn.setProperty("active", m == mode)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

        if mode == "never":
            self.mode_stack.setCurrentIndex(0)
            self._show_new_fact()
        elif mode == "cycles":
            self.mode_stack.setCurrentIndex(1)
        elif mode == "timed":
            self.mode_stack.setCurrentIndex(2)

    def get_click_count(self):
        if self.stop_mode == "never":
            return 0  # infinite
        elif self.stop_mode == "cycles":
            return self.spin_cycles.value()
        else:  # timed
            return 0  # infinite clicks, but time-limited

    def get_time_limit_ms(self):
        """Return time limit in ms (0 = no limit)."""
        if self.stop_mode != "timed":
            return 0
        return (
            self.spin_hours.value() * 3600000
            + self.spin_minutes.value() * 60000
            + self.spin_seconds.value() * 1000
            + self.spin_milliseconds.value()
        )

    def get_interval_ms(self):
        val = self.spin_interval.value()
        unit = self.unit_combo.currentText()
        if unit == "Seconds":
            return val * 1000
        elif unit == "Minutes":
            return val * 60000
        elif unit == "Hours":
            return val * 3600000
        return val  # Milliseconds

    def get_mouse_button(self):
        return self.selected_button

    def set_running_state(self, running: bool):
        if running:
            self.status_label.setText(tr("running"))
            self.status_label.setProperty("running", True)
            self.btn_start_stop.setText(tr("stop"))
            self.btn_start_stop.setProperty("running", True)
        else:
            self.status_label.setText(tr("stopped"))
            self.status_label.setProperty("running", False)
            self.btn_start_stop.setText(tr("start"))
            self.btn_start_stop.setProperty("running", False)
        for w in (self.status_label, self.btn_start_stop):
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def retranslateUi(self):
        """Update all translatable text."""
        self.h_title.setText(tr("single_target"))
        self.h_sub.setText(tr("single_target_sub"))
        # Status + start/stop (preserve current state)
        is_running = self.btn_start_stop.property("running")
        if is_running:
            self.status_label.setText(tr("running"))
            self.btn_start_stop.setText(tr("stop"))
        else:
            self.status_label.setText(tr("stopped"))
            self.btn_start_stop.setText(tr("start"))
        # Card headers
        self.lbl_event.setText(tr("event_timing"))
        self.lbl_int.setText(tr("clicking_interval"))
        self.lbl_time_interval.setText(tr("time_interval"))
        self.lbl_mouse.setText(tr("mouse_button"))
        self.lbl_pos.setText(tr("click_position"))
        self.sh_lbl.setText(tr("scroll_automation"))
        self.cb_lbl.setText(tr("multi_button"))
        self.co_lbl.setText(tr("position_offset"))
        # Toggle buttons
        active_ns = self.btn_never_stop.property("active")
        self.btn_never_stop.setText(("●" if active_ns else "●") + "   " + tr("never_stop"))
        active_nc = self.btn_num_cycles.property("active")
        self.btn_num_cycles.setText(("●" if active_nc else "●") + "   " + tr("num_cycles"))
        active_tg = self.btn_time_gated.property("active")
        self.btn_time_gated.setText(("●" if active_tg else "●") + "   " + tr("time_gated"))
        self.btn_new_fact.setText(tr("another_fact"))
        # Mouse buttons
        self.btn_left_click.setText("\U0001F5B1  " + tr("left_click"))
        self.btn_right_click.setText("\U0001F5B1  " + tr("right_click"))
        self.btn_middle_click.setText("\U0001F5B1  " + tr("middle_click"))
        # Position
        active_fm = self.btn_follow_mouse.property("active")
        self.btn_follow_mouse.setText(("●" if active_fm else "●") + "   " + tr("follow_mouse"))
        active_cp = self.btn_custom_pos.property("active")
        self.btn_custom_pos.setText(("●" if active_cp else "●") + "   " + tr("custom_position"))
        # Hints & warnings
        self.lbl_warn.setText(tr("warn_interval"))
        self.pos_hint.setText(tr("follow_hint"))
        self.combo_hint.setText(tr("combo_hint"))
        self.offset_hint.setText(tr("offset_hint"))
        self.chk_scroll.setText(tr("scroll_enable"))
        # Unit combo
        self.unit_combo.setItemText(0, tr("milliseconds"))
        self.unit_combo.setItemText(1, tr("seconds"))
        self.unit_combo.setItemText(2, tr("minutes"))
        self.unit_combo.setItemText(3, tr("hours"))

    # ── Secret admin password popup ────────────────────────────
    def _ask_admin_password(self):
        dlg = _ThemedPasswordDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            if not _SECRET_PASS:
                _show_themed_warning(self, "Denied", "Admin password is not configured (MTA_ADMIN_PASSWORD).")
            elif hmac.compare_digest(dlg.password, _SECRET_PASS):
                self.admin_activated.emit()
            else:
                _show_themed_warning(self, "Denied", "Wrong password.")


class _ThemedPasswordDialog(QDialog):
    """Password dialog that uses the current app theme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.password = ""
        self.setWindowTitle("\U0001f512 Access Restricted")
        self.setFixedSize(380, 160)
        self.setStyleSheet(get_dialog_stylesheet())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lbl = QLabel("\U0001f512  Enter admin password:")
        lbl.setStyleSheet("font-weight: 600; font-size: 14px;")
        lay.addWidget(lbl)

        self._edit = QLineEdit()
        self._edit.setEchoMode(QLineEdit.Password)
        self._edit.setPlaceholderText("Password...")
        self._edit.returnPressed.connect(self._on_ok)
        lay.addWidget(self._edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("CancelBtn")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("\u2714  Confirm")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

    def _on_ok(self):
        self.password = self._edit.text()
        self.accept()


def _show_themed_warning(parent, title: str, msg: str):
    """Show a themed warning message box."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setFixedSize(320, 120)
    dlg.setStyleSheet(get_dialog_stylesheet(warning=True))
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(14)
    lbl = QLabel(f"\u26a0  {msg}")
    lbl.setAlignment(Qt.AlignCenter)
    lay.addWidget(lbl)
    btn = QPushButton("OK")
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(dlg.accept)
    lay.addWidget(btn, 0, Qt.AlignCenter)
    dlg.exec_()
