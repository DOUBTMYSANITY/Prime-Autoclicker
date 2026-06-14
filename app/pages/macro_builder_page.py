from __future__ import annotations

import json
import threading
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QComboBox,
    QSpinBox,
)
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController

from app.gui.widgets import Card, add_shadow

_FLOWS_FILE = Path.home() / ".mtautoclicker_macro_flows.json"


class MacroBuilderPage(QWidget):
    """Simple visual macro builder with step list and run/stop controls."""

    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps: list[dict] = []
        self._flows: dict[str, list[dict]] = {}
        self._run_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._mouse = MouseController()
        self._keyboard = KeyboardController()

        self._build_ui()
        self._load_flows_from_disk()
        self._refresh_flow_combo()
        self._refresh_step_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        hero = Card()
        hero.setObjectName("Hero")
        add_shadow(hero, blur=24, y=8, alpha=110)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24, 18, 24, 18)
        hl.setSpacing(6)
        title = QLabel("Macro Builder")
        title.setObjectName("HeroTitle")
        sub = QLabel("Build click/keyboard flows as reusable step sequences.")
        sub.setObjectName("HeroSub")
        hl.addWidget(title)
        hl.addWidget(sub)
        root.addWidget(hero)

        body = Card()
        body.setObjectName("ConfigCard")
        add_shadow(body, blur=22, y=8, alpha=90)
        bl = QVBoxLayout(body)
        bl.setContentsMargins(20, 18, 20, 18)
        bl.setSpacing(12)

        controls = QGridLayout()
        controls.setHorizontalSpacing(10)
        controls.setVerticalSpacing(8)

        self.cmb_action = QComboBox()
        self.cmb_action.setObjectName("UnitDrop")
        self.cmb_action.addItems(["wait_ms", "click_left", "click_right", "key_tap", "scroll"])

        self.spin_value = QSpinBox()
        self.spin_value.setObjectName("TimeSpin")
        self.spin_value.setRange(-100_000, 100_000)
        self.spin_value.setValue(100)

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("key (for key_tap), e.g. a")

        self.btn_add = QPushButton("+ Add Step")
        self.btn_add.setObjectName("ToggleButton")
        self.btn_add.setProperty("active", True)

        controls.addWidget(QLabel("Action"), 0, 0)
        controls.addWidget(self.cmb_action, 0, 1)
        controls.addWidget(QLabel("Value"), 0, 2)
        controls.addWidget(self.spin_value, 0, 3)
        controls.addWidget(self.input_text, 0, 4)
        controls.addWidget(self.btn_add, 0, 5)
        bl.addLayout(controls)

        self.list_steps = QListWidget()
        self.list_steps.setObjectName("PresetList")
        self.list_steps.setMinimumHeight(240)
        bl.addWidget(self.list_steps)

        row_edit = QHBoxLayout()
        row_edit.setSpacing(10)
        self.btn_up = QPushButton("Move Up")
        self.btn_down = QPushButton("Move Down")
        self.btn_remove = QPushButton("Remove")
        self.btn_clear = QPushButton("Clear")
        for btn in (self.btn_up, self.btn_down, self.btn_remove, self.btn_clear):
            btn.setObjectName("ToggleButton")
            btn.setProperty("active", False)
            row_edit.addWidget(btn)
        row_edit.addStretch(1)
        bl.addLayout(row_edit)

        row_store = QHBoxLayout()
        row_store.setSpacing(10)
        self.input_flow_name = QLineEdit()
        self.input_flow_name.setPlaceholderText("Flow name")
        self.cmb_saved_flows = QComboBox()
        self.cmb_saved_flows.setObjectName("UnitDrop")
        self.btn_save_flow = QPushButton("Save Flow")
        self.btn_load_flow = QPushButton("Load Flow")
        for btn in (self.btn_save_flow, self.btn_load_flow):
            btn.setObjectName("ToggleButton")
            btn.setProperty("active", True)
        row_store.addWidget(self.input_flow_name, 1)
        row_store.addWidget(self.btn_save_flow)
        row_store.addSpacing(12)
        row_store.addWidget(self.cmb_saved_flows, 1)
        row_store.addWidget(self.btn_load_flow)
        bl.addLayout(row_store)

        row_run = QHBoxLayout()
        row_run.setSpacing(10)
        self.btn_run = QPushButton("Run Flow")
        self.btn_stop = QPushButton("Stop")
        self.btn_run.setObjectName("StartStopBtn")
        self.btn_stop.setObjectName("ToggleButton")
        self.btn_stop.setProperty("active", False)
        self.lbl_status = QLabel("Status: idle")
        self.lbl_status.setObjectName("StatusLabel")
        row_run.addWidget(self.btn_run)
        row_run.addWidget(self.btn_stop)
        row_run.addWidget(self.lbl_status)
        row_run.addStretch(1)
        bl.addLayout(row_run)

        root.addWidget(body)
        root.addStretch(1)

        self.btn_add.clicked.connect(self._on_add_step)
        self.btn_remove.clicked.connect(self._on_remove_step)
        self.btn_clear.clicked.connect(self._on_clear_steps)
        self.btn_up.clicked.connect(self._on_move_up)
        self.btn_down.clicked.connect(self._on_move_down)
        self.btn_save_flow.clicked.connect(self._on_save_flow)
        self.btn_load_flow.clicked.connect(self._on_load_flow)
        self.btn_run.clicked.connect(self._on_run)
        self.btn_stop.clicked.connect(self._on_stop)
        self.status_changed.connect(self._set_status)

    def _on_add_step(self):
        action = self.cmb_action.currentText()
        step = {
            "action": action,
            "value": int(self.spin_value.value()),
            "text": self.input_text.text().strip(),
        }
        self._steps.append(step)
        self._refresh_step_list()

    def _on_remove_step(self):
        idx = self.list_steps.currentRow()
        if 0 <= idx < len(self._steps):
            self._steps.pop(idx)
            self._refresh_step_list()

    def _on_clear_steps(self):
        self._steps.clear()
        self._refresh_step_list()

    def _on_move_up(self):
        idx = self.list_steps.currentRow()
        if idx > 0:
            self._steps[idx - 1], self._steps[idx] = self._steps[idx], self._steps[idx - 1]
            self._refresh_step_list()
            self.list_steps.setCurrentRow(idx - 1)

    def _on_move_down(self):
        idx = self.list_steps.currentRow()
        if 0 <= idx < len(self._steps) - 1:
            self._steps[idx + 1], self._steps[idx] = self._steps[idx], self._steps[idx + 1]
            self._refresh_step_list()
            self.list_steps.setCurrentRow(idx + 1)

    def _on_save_flow(self):
        name = self.input_flow_name.text().strip()
        if not name:
            self.status_changed.emit("Status: enter flow name first")
            return
        self._flows[name] = [dict(s) for s in self._steps]
        self._save_flows_to_disk()
        self._refresh_flow_combo(selected=name)
        self.status_changed.emit(f"Status: saved flow '{name}'")

    def _on_load_flow(self):
        name = self.cmb_saved_flows.currentText().strip()
        if not name or name not in self._flows:
            self.status_changed.emit("Status: no flow selected")
            return
        self._steps = [dict(s) for s in self._flows[name]]
        self._refresh_step_list()
        self.status_changed.emit(f"Status: loaded flow '{name}'")

    def _on_run(self):
        if self._run_thread and self._run_thread.is_alive():
            self.status_changed.emit("Status: flow already running")
            return
        if not self._steps:
            self.status_changed.emit("Status: add at least one step")
            return
        self._stop_event.clear()
        steps = [dict(s) for s in self._steps]
        self._run_thread = threading.Thread(target=self._run_steps, args=(steps,), daemon=True)
        self._run_thread.start()
        self.status_changed.emit("Status: running")

    def _on_stop(self):
        self._stop_event.set()
        self.status_changed.emit("Status: stopping...")

    def _run_steps(self, steps: list[dict]):
        try:
            for idx, step in enumerate(steps, start=1):
                if self._stop_event.is_set():
                    self.status_changed.emit("Status: stopped")
                    return
                action = step.get("action", "")
                value = int(step.get("value", 0))
                text = str(step.get("text", "")).strip()

                if action == "wait_ms":
                    self._stop_event.wait(max(0, value) / 1000.0)
                elif action == "click_left":
                    self._mouse.click(Button.left, max(1, value if value > 0 else 1))
                elif action == "click_right":
                    self._mouse.click(Button.right, max(1, value if value > 0 else 1))
                elif action == "scroll":
                    self._mouse.scroll(0, value)
                elif action == "key_tap":
                    key_text = text or "a"
                    self._keyboard.press(key_text)
                    self._keyboard.release(key_text)

                self.status_changed.emit(f"Status: step {idx}/{len(steps)} done")
            self.status_changed.emit("Status: finished")
        except Exception as exc:
            self.status_changed.emit(f"Status: error: {exc}")

    def _set_status(self, text: str):
        self.lbl_status.setText(text)

    def _refresh_step_list(self):
        self.list_steps.clear()
        for i, step in enumerate(self._steps, start=1):
            item = QListWidgetItem(
                f"{i:02d}. {step.get('action')} | value={step.get('value')} | text={step.get('text', '')}"
            )
            self.list_steps.addItem(item)

    def _load_flows_from_disk(self):
        try:
            with open(_FLOWS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._flows = {
                    str(name): [dict(step) for step in steps if isinstance(step, dict)]
                    for name, steps in data.items()
                    if isinstance(steps, list)
                }
            else:
                self._flows = {}
        except Exception:
            self._flows = {}

    def _save_flows_to_disk(self):
        try:
            with open(_FLOWS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._flows, f, indent=2)
        except Exception:
            pass

    def _refresh_flow_combo(self, selected: str | None = None):
        self.cmb_saved_flows.clear()
        names = sorted(self._flows.keys())
        self.cmb_saved_flows.addItems(names)
        if selected and selected in names:
            self.cmb_saved_flows.setCurrentText(selected)
