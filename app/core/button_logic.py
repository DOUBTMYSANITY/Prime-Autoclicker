# Buttonlogic.py
from PyQt5 import QtCore, QtGui, QtWidgets
from app.core.single_clicker import SingleClickerLogic
import os


class ButtonLogic(QtCore.QObject):
    def __init__(self, grid_layout: QtWidgets.QGridLayout, on_back=None, parent=None):
        super().__init__(parent)
        self.grid = grid_layout
        self.on_back = on_back
        self.state = {
            "h": 0, "m": 0, "s": 0, "ms": 10,
            "mouse_button": "Left",
            "click_type": "Single",
            "repeat_mode": "until_stopped",
            "repeat_times": 1,
            "cursor_mode": "current",
            "x": 0, "y": 0,
        }
        self._single_logic = None
        self._is_running = False
        self._listener = None

    # ---------- required by your main window ----------
    def clear_grid(self):
        while self.grid.count():
            it = self.grid.takeAt(0)
            if (w := it.widget()) is not None:
                w.setParent(None); w.deleteLater()
            if (lay := it.layout()) is not None:
                self._clear_layout(lay)

    def _clear_layout(self, layout: QtWidgets.QLayout):
        while layout.count():
            it = layout.takeAt(0)
            if (w := it.widget()) is not None:
                w.setParent(None); w.deleteLater()
            if (lay := it.layout()) is not None:
                self._clear_layout(lay)

    # ---------- router from your grid cards ----------
    def show_feature(self, key: str, title: str):
        if key == "single":
            self._show_single_clicker(title)
        else:
            self._show_generic(title, key)

    def _show_generic(self, title: str, key: str):
        self.clear_grid()
        page = QtWidgets.QFrame()
        v = QtWidgets.QVBoxLayout(page); v.setContentsMargins(24, 24, 24, 24); v.setSpacing(16)
        v.addLayout(self._header(title))
        body = self._card()
        inner = QtWidgets.QVBoxLayout(body); inner.setContentsMargins(24, 24, 24, 24)
        inner.addWidget(self._label_dim(f"{title} (key: {key})"))
        inner.addStretch(1)
        v.addWidget(body, 1)
        self.grid.addWidget(page, 0, 0, 1, 3)

    # ---------- Single Clicker page ----------
    def _show_single_clicker(self, title: str):
        self.clear_grid()

        if self._single_logic is None:
            self._single_logic = SingleClickerLogic()
            self._single_logic.started.connect(lambda: self._set_running(True))
            self._single_logic.stopped.connect(lambda: self._set_running(False))
            # NEW: auto-fill X/Y after user presses F in the pick popup
            self._single_logic.positionPicked.connect(self._on_position_picked)

        page = QtWidgets.QFrame(); page.setObjectName("singlePage")
        page.setStyleSheet(
            "QLabel, QRadioButton { color:#e7edff; } "
            "QComboBox, QLineEdit { color:#e7edff; }"
        )
        root = QtWidgets.QVBoxLayout(page); root.setContentsMargins(24, 24, 24, 24); root.setSpacing(12)
        root.addLayout(self._header(title))

        # --- Click interval ---
        sec1, body1 = self._section("Click interval")
        gi = QtWidgets.QGridLayout(body1); gi.setContentsMargins(12,10,12,12); gi.setHorizontalSpacing(10); gi.setVerticalSpacing(8)
        for c in range(8): gi.setColumnStretch(c, 0)

        self.ed_h  = self._num_edit(70, self.state["h"])
        self.ed_m  = self._num_edit(70, self.state["m"], 0, 59)
        self.ed_s  = self._num_edit(70, self.state["s"], 0, 59)
        self.ed_ms = self._num_edit(90, self.state["ms"], 0, 999)

        gi.addWidget(self._boxed(self.ed_h), 0, 0);  gi.addWidget(self._label_dim("hours"),        0, 1)
        gi.addWidget(self._boxed(self.ed_m), 0, 2);  gi.addWidget(self._label_dim("mins"),         0, 3)
        gi.addWidget(self._boxed(self.ed_s), 0, 4);  gi.addWidget(self._label_dim("secs"),         0, 5)
        gi.addWidget(self._boxed(self.ed_ms),0, 6);  gi.addWidget(self._label_dim("milliseconds"), 0, 7)

        for key, ed in (("h", self.ed_h), ("m", self.ed_m), ("s", self.ed_s), ("ms", self.ed_ms)):
            self._bind_commit(ed, key, after=self._push_interval)

        # --- Click options + repeat ---
        row2 = QtWidgets.QHBoxLayout(); row2.setSpacing(12)

        sec2, body2 = self._section("Click options")
        fo = QtWidgets.QFormLayout(body2); fo.setContentsMargins(12,10,12,12); fo.setHorizontalSpacing(14); fo.setVerticalSpacing(10)
        self.cb_button = self._combo(["Left", "Right", "Middle"], self.state["mouse_button"])
        self.cb_type   = self._combo(["Single", "Double"],        self.state["click_type"])
        self.cb_button.currentTextChanged.connect(lambda v: (self._save("mouse_button", v), self._single_logic.set_mouse_button(v)))
        self.cb_type.currentTextChanged.connect(  lambda v: (self._save("click_type",   v), self._single_logic.set_click_type(v)))
        fo.addRow(self._label_dim("Mouse button:"), self._boxed(self.cb_button, fixed_w=140))
        fo.addRow(self._label_dim("Click type:"),   self._boxed(self.cb_type,   fixed_w=140))

        sec3, body3 = self._section("Click repeat")
        vr = QtWidgets.QGridLayout(body3); vr.setContentsMargins(12,10,12,12); vr.setHorizontalSpacing(10); vr.setVerticalSpacing(10)
        self.chip_repeat = self._chip("Repeat"); self.chip_until  = self._chip("Repeat until stopped")
        grp_rep = QtWidgets.QButtonGroup(body3); grp_rep.setExclusive(True)
        grp_rep.addButton(self.chip_repeat); grp_rep.addButton(self.chip_until)
        if self.state["repeat_mode"] == "times": self.chip_repeat.setChecked(True)
        else: self.chip_until.setChecked(True)

        def _push_repeat_mode():
            mode = "times" if self.chip_repeat.isChecked() else "until_stopped"
            self._save("repeat_mode", mode)
            self._single_logic.set_repeat_mode(mode)
            self.ed_times.setEnabled(mode == "times")

        self.chip_repeat.toggled.connect(lambda _on: _push_repeat_mode())
        self.chip_until.toggled.connect(lambda _on: _push_repeat_mode())

        self.ed_times = self._num_edit(90, self.state["repeat_times"], 1, 999999)
        self._bind_commit(self.ed_times, "repeat_times",
                          after=lambda: self._single_logic.set_repeat_times(int(self.ed_times.text() or "1")))
        self.ed_times.setEnabled(self.chip_repeat.isChecked())

        vr.addWidget(self.chip_repeat, 0, 0, 1, 2)
        vr.addWidget(self._boxed(self.ed_times, fixed_w=94), 0, 2)
        vr.addWidget(self._label_dim("times"), 0, 3)
        vr.addWidget(self.chip_until,  1, 0, 1, 4)

        row2.addWidget(sec2, 1); row2.addWidget(sec3, 1)

        # --- Cursor position ---
        sec4, body4 = self._section("Cursor position")
        gp = QtWidgets.QGridLayout(body4); gp.setContentsMargins(12,10,12,12); gp.setHorizontalSpacing(10); gp.setVerticalSpacing(10)

        self.chip_current = self._chip("Current location")
        self.chip_pick    = self._chip("Pick location")
        grp_cur = QtWidgets.QButtonGroup(body4); grp_cur.setExclusive(True)
        grp_cur.addButton(self.chip_current); grp_cur.addButton(self.chip_pick)
        if self.state["cursor_mode"] == "current": self.chip_current.setChecked(True)
        else: self.chip_pick.setChecked(True)

        # REPLACED: wire picker + mode switch
        self.chip_current.toggled.connect(lambda on: (self._set_coord_active(False),
                                                      self._single_logic.set_cursor_mode("current")) if on else None)

        self.chip_pick.toggled.connect(lambda on: (self._set_coord_active(True),
                                                   self._single_logic.set_cursor_mode("pick"),
                                                   self._single_logic.start_pick_position()) if on else None)

        self.le_x = self._coord_input(94); self.le_y = self._coord_input(94)
        self.le_x.setText(str(self.state["x"])); self.le_y.setText(str(self.state["y"]))
        self._bind_commit(self.le_x, "x", is_coord=True, after=self._push_xy)
        self._bind_commit(self.le_y, "y", is_coord=True, after=self._push_xy)
        self._set_coord_active(self.chip_pick.isChecked())

        gp.addWidget(self.chip_current, 0, 0, 1, 2)
        gp.addWidget(self.chip_pick,    0, 2, 1, 2)
        gp.addWidget(self._label_dim("X"), 0, 4); gp.addWidget(self._boxed(self.le_x, fixed_w=94), 0, 5)
        gp.addWidget(self._label_dim("Y"), 0, 6); gp.addWidget(self._boxed(self.le_y, fixed_w=94), 0, 7)

        # --- Bottom: Start/Stop (X) ---
        bottom = QtWidgets.QHBoxLayout(); bottom.setSpacing(12)
        self.btn_start = self._glass_button("Start (X)")
        self.btn_stop  = self._glass_button("Stop (X)")
        bottom.addWidget(self.btn_start); bottom.addWidget(self.btn_stop)
        # Both buttons use the same toggle so they mirror the hotkey
        self.btn_start.clicked.connect(self._toggle_run)
        self.btn_stop.clicked.connect(self._toggle_run)

        root.addWidget(sec1); root.addLayout(row2); root.addWidget(sec4); root.addLayout(bottom)

        # Push current state to logic
        self._push_interval()
        self._single_logic.set_mouse_button(self.state["mouse_button"])
        self._single_logic.set_click_type(self.state["click_type"])
        self._single_logic.set_repeat_mode(self.state["repeat_mode"])
        self._single_logic.set_repeat_times(self.state["repeat_times"])
        self._single_logic.set_cursor_mode(self.state["cursor_mode"])
        self._push_xy()

        self.grid.addWidget(page, 0, 0, 1, 3)

    @QtCore.pyqtSlot()
    def _toggle_run(self):
        # Ensure we have an engine to toggle (works even from the dashboard)
        if getattr(self, "_single_logic", None) is None:
            try:
                self._single_logic = SingleClickerLogic()
                self._single_logic.started.connect(lambda: self._set_running(True))
                self._single_logic.stopped.connect(lambda: self._set_running(False))
                self._single_logic.positionPicked.connect(self._on_position_picked)
            except Exception:
                return

        if self._is_running:
            print("[AutoClicker] stopping…")
            # if your engine exposes stop_blocking, prefer it:
            try:
                self._single_logic.stop_blocking(1500)
            except Exception:
                self._single_logic.stop()
            self._is_running = False
        else:
            print("[AutoClicker] starting…")
            self._single_logic.start()
            self._is_running = True

    def _on_position_picked(self, x: int, y: int):
        # update state + UI + engine when user picks coords (presses F)
        self.state["x"], self.state["y"] = int(x), int(y)
        if hasattr(self, "le_x"): self.le_x.setText(str(x))
        if hasattr(self, "le_y"): self.le_y.setText(str(y))
        try:
            self._single_logic.set_target_xy(int(x), int(y))
        except Exception:
            pass

    def _set_running(self, running: bool):
        self._is_running = running
        if hasattr(self, "btn_start") and hasattr(self, "btn_stop"):
            self.btn_start.setEnabled(not running)
            self.btn_stop.setEnabled(running)

    # ---------- small helpers / styling ----------
    def _push_interval(self):
        h = int(self.ed_h.text() or 0)
        m = int(self.ed_m.text() or 0)
        s = int(self.ed_s.text() or 0)
        ms = int(self.ed_ms.text() or 0)
        self._single_logic.set_interval(h, m, s, ms)

    def _push_xy(self):
        x = int(self.le_x.text() or "0")
        y = int(self.le_y.text() or "0")
        self._single_logic.set_target_xy(x, y)

    def _header(self, title_text: str) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel(title_text); title.setStyleSheet("font-size:18pt; font-weight:700; color:#e8ecff;")
        back = QtWidgets.QPushButton("← Back"); back.setCursor(QtCore.Qt.PointingHandCursor)
        back.clicked.connect(lambda: self.on_back() if callable(self.on_back) else None)
        back.setStyleSheet(
            "padding:8px 12px; border-radius:10px; color:#e7edff; "
            "background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.10);"
        )
        row.addWidget(title, 1); row.addWidget(back, 0, QtCore.Qt.AlignRight)
        return row

    def _card(self) -> QtWidgets.QFrame:
        f = QtWidgets.QFrame(); f.setObjectName("featureBody")
        f.setStyleSheet(
            "QFrame#featureBody{border-radius:18px; background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(34,28,72,235), stop:0.5 rgba(76,38,128,240), stop:1 rgba(22,28,60,235));"
            "border:1px solid rgba(255,255,255,0.08);}"
        )
        eff = QtWidgets.QGraphicsDropShadowEffect(f); eff.setBlurRadius(40); eff.setOffset(0, 14); eff.setColor(QtGui.QColor(90,120,255,120))
        f.setGraphicsEffect(eff)
        return f

    def _section(self, title: str):
        frame = self._card()
        wrap = QtWidgets.QVBoxLayout(frame); wrap.setContentsMargins(12, 12, 12, 12); wrap.setSpacing(8)
        header = QtWidgets.QLabel(title); header.setStyleSheet("font-weight:700; color:#e8ecff;")
        body = QtWidgets.QFrame(); body.setStyleSheet("background: rgba(255,255,255,0.04); border-radius:10px; border:1px solid rgba(255,255,255,0.06);")
        wrap.addWidget(header); wrap.addWidget(body)
        return frame, body

    def _label_dim(self, text: str) -> QtWidgets.QLabel:
        l = QtWidgets.QLabel(text); l.setStyleSheet("color: rgba(230,236,255,0.90);")
        return l

    def _boxed(self, w: QtWidgets.QWidget, fixed_w: int = None) -> QtWidgets.QFrame:
        box = QtWidgets.QFrame()
        box.setStyleSheet("QFrame{border:1px solid rgba(255,255,255,0.10); background: rgba(255,255,255,0.06); border-radius:8px;}")
        if fixed_w: box.setFixedWidth(fixed_w)
        lay = QtWidgets.QHBoxLayout(box); lay.setContentsMargins(6, 2, 6, 2); lay.addWidget(w)
        return box

    def _num_edit(self, width: int, initial: int, mn: int = None, mx: int = None) -> QtWidgets.QLineEdit:
        le = QtWidgets.QLineEdit(); le.setFixedWidth(width); le.setAlignment(QtCore.Qt.AlignRight)
        if mn is None: mn = -999999999
        if mx is None: mx =  999999999
        le.setValidator(QtGui.QIntValidator(mn, mx)); le.setText(str(initial))
        le.setStyleSheet("QLineEdit{border:none; background:transparent; padding:4px 2px;}")
        return le

    def _coord_input(self, width: int) -> QtWidgets.QLineEdit:
        le = QtWidgets.QLineEdit(); le.setObjectName("coord"); le.setValidator(QtGui.QIntValidator(-999999, 999999))
        le.setFixedWidth(width); le.setProperty("active", False); le.setAlignment(QtCore.Qt.AlignRight)
        le.setStyleSheet(
            "QLineEdit#coord[active=\"false\"]{background:#0b0e1a; color:#6f7899; border:1px solid #1a2140; border-radius:6px; padding:6px 8px;}"
            "QLineEdit#coord[active=\"true\"]{background:rgba(255,255,255,0.06); color:#e7edff; border:1px solid rgba(255,255,255,0.10); border-radius:6px; padding:6px 8px;}"
        )
        return le

    def _combo(self, items, current) -> QtWidgets.QComboBox:
        cb = QtWidgets.QComboBox(); cb.addItems(items); cb.setCurrentText(current)
        cb.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        cb.setStyleSheet(
            "QComboBox{border:none; background:transparent;}"
            "QComboBox QAbstractItemView{background:#222a55; color:#e7edff; border:1px solid rgba(255,255,255,0.10);}"
        )
        return cb

    def _chip(self, text: str) -> QtWidgets.QPushButton:
        b = QtWidgets.QPushButton(text); b.setCheckable(True); b.setMinimumHeight(34); b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setStyleSheet(
            "QPushButton{border-radius:8px; padding:6px 10px; border:1px solid rgba(255,255,255,0.14); background:rgba(255,255,255,0.08); color:#e7edff;}"
            "QPushButton:hover{background:rgba(255,255,255,0.14);}"
            "QPushButton:checked{border:1px solid #8aa4ff; background:#4156b9;}"
        )
        return b

    def _glass_button(self, text: str) -> QtWidgets.QPushButton:
        b = QtWidgets.QPushButton(text); b.setMinimumHeight(46)
        b.setStyleSheet(
            "QPushButton{color:#e7edff; border-radius:10px; padding:10px 14px; background: rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.12);}"
            "QPushButton:hover{background: rgba(255,255,255,0.14);}"
        )
        return b

    # commit helper
    def _bind_commit(self, line: QtWidgets.QLineEdit, key: str, is_coord: bool = False, after=None):
        def commit():
            txt = line.text().strip()
            if txt in ("", "-", "+"):
                return
            try:
                val = int(txt)
            except ValueError:
                return
            self._save(key, val)
            if after:
                after()
            w = line.window()
            if w:
                w.setFocus()
            else:
                line.clearFocus()
        line.editingFinished.connect(commit)

    def _set_coord_active(self, on: bool):
        self.state["cursor_mode"] = "pick" if on else "current"
        for le in (self.le_x, self.le_y):
            le.setProperty("active", on); le.setEnabled(on)
            le.style().unpolish(le); le.style().polish(le); le.update()

    def _save(self, key: str, value):
        self.state[key] = value
