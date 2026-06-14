# Single_Clicker_Logic.py — PyAutoGUI backend with robust stop + position picker
# - Click Options: Left/Right/Middle
# - Repeat: exact N times or until stopped
# - Cursor Position:
#     * "current"  -> click at current mouse location
#     * "pick"     -> popup instructs "Press F to pick" (global). Captures coords and emits them.

from dataclasses import dataclass
import time, threading
from PyQt5 import QtCore, QtWidgets, QtGui
from app.styling.themes import get_pick_dialog_stylesheet
import pyautogui

pyautogui.PAUSE = 0
try:
    pyautogui.MINIMUM_DURATION = 0
    pyautogui.MINIMUM_SLEEP = 0
except Exception:
    pass
pyautogui.FAILSAFE = False


@dataclass
class ClickConfig:
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    millis: int = 100
    mouse_button: str = "Left"          # "Left" | "Right" | "Middle"
    click_type: str = "Single"           # "Single" | "Double"
    repeat_mode: str = "until_stopped"   # "times"  | "until_stopped"
    repeat_times: int = 1
    cursor_mode: str = "current"         # "current" | "pick"
    x: int = 0
    y: int = 0


# ---------------- Worker (runs in QThread) ----------------
class ClickWorker(QtCore.QObject):
    started  = QtCore.pyqtSignal()
    stopped  = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int)
    warning  = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.cfg = ClickConfig()
        self._stop_evt = threading.Event()
        self._count = 0

    # thread-safe
    def request_stop(self):
        self._stop_evt.set()

    def set_config(self, cfg: ClickConfig):
        self.cfg = cfg

    def _interval_seconds(self) -> float:
        total_ms = (self.cfg.hours*3600 + self.cfg.minutes*60 + self.cfg.seconds) * 1000 + self.cfg.millis
        return max(total_ms, 0) / 1000.0

    def _click_once(self):
        # Extra stop checks to guarantee we exit even during double/right-clicks
        if self._stop_evt.is_set():
            return

        btn = self.cfg.mouse_button
        double = (self.cfg.click_type == "Double")
        pos = (self.cfg.x, self.cfg.y) if self.cfg.cursor_mode == "pick" else None

        button_name = "left" if btn == "Left" else "right" if btn == "Right" else "middle"

        def do_click():
            if self._stop_evt.is_set():
                return
            if pos is not None:
                pyautogui.click(x=pos[0], y=pos[1], button=button_name)
            else:
                pyautogui.click(button=button_name)

            # Right-click tends to pop context menus that can monopolize the UI loop.
            # Give the system a micro-slice so global hotkeys (X / Shift+Esc) are processed.
            if button_name == "right":
                time.sleep(0.005)  # 5ms; tiny but prevents “can’t stop” feeling

        do_click()
        if double and not self._stop_evt.is_set():
            do_click()


    def _sleep_until(self, target: float):
        while not self._stop_evt.is_set():
            now = time.perf_counter()
            rem = target - now
            if rem <= 0:
                break
            # Sleep in small chunks; yield enough that the keyboard hook never starves
            if rem > 0.01:
                time.sleep(0.005)
            elif rem > 0.002:
                time.sleep(0.001)
            else:
                time.sleep(rem)

    @QtCore.pyqtSlot()
    def run(self):
        if self._stop_evt.is_set():
            self._stop_evt.clear()
        self._count = 0
        try:
            self.started.emit()
        except RuntimeError:
            return

        interval = self._interval_seconds()
        if interval <= 0:
            interval = 0.0005

        target_clicks = self.cfg.repeat_times if self.cfg.repeat_mode == "times" else None
        next_t = time.perf_counter()

        try:
            while not self._stop_evt.is_set():
                self._sleep_until(next_t)
                if self._stop_evt.is_set():
                    break

                self._click_once()
                self._count += 1
                try:
                    self.progress.emit(self._count)
                except RuntimeError:
                    break

                if target_clicks is not None and self._count >= target_clicks:
                    break

                next_t += interval
        finally:
            try:
                self.stopped.emit()
            except RuntimeError:
                pass


# ---------------- Public facade used by your UI ----------------
class SingleClickerLogic(QtCore.QObject):
    # signals for UI
    started  = QtCore.pyqtSignal()
    stopped  = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int)
    warning  = QtCore.pyqtSignal(str)
    positionPicked = QtCore.pyqtSignal(int, int)  # NEW: emit (x, y) when user presses F in pick-mode

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = ClickConfig()
        self._thread = QtCore.QThread(parent)
        self._worker = ClickWorker()
        self._worker.moveToThread(self._thread)
        self._thread.start()

        self._running = False
        self._worker.started.connect(lambda: self._set_running(True))
        self._worker.stopped.connect(lambda: self._set_running(False))
        self._worker.progress.connect(self.progress)
        self._worker.warning.connect(self.warning)

        # elements for pick-position flow
        self._pick_dialog = None
        self._pick_listener = None

    def _set_running(self, v: bool):
        self._running = v
        (self.started if v else self.stopped).emit()

    def is_running(self) -> bool:
        return self._running

    # -------- setters the UI can call --------
    @QtCore.pyqtSlot(int, int, int, int)
    def set_interval(self, h, m, s, ms):
        self._cfg.hours, self._cfg.minutes, self._cfg.seconds, self._cfg.millis = int(h), int(m), int(s), int(ms)

    @QtCore.pyqtSlot(str)
    def set_mouse_button(self, btn):
        if btn not in ("Left", "Right", "Middle"):
            btn = "Left"
        self._cfg.mouse_button = btn

    @QtCore.pyqtSlot(str)
    def set_click_type(self, typ):
        self._cfg.click_type = "Double" if typ == "Double" else "Single"

    @QtCore.pyqtSlot(str)
    def set_repeat_mode(self, mode):
        self._cfg.repeat_mode = "times" if mode == "times" else "until_stopped"

    @QtCore.pyqtSlot(int)
    def set_repeat_times(self, n):
        self._cfg.repeat_times = max(1, int(n))

    @QtCore.pyqtSlot(str)
    def set_cursor_mode(self, mode):
        self._cfg.cursor_mode = "pick" if mode == "pick" else "current"

    @QtCore.pyqtSlot(int, int)
    def set_target_xy(self, x, y):
        self._cfg.x, self._cfg.y = int(x), int(y)

    # -------- control --------
    @QtCore.pyqtSlot()
    def start(self):
        if self._running:
            return
        self._worker.set_config(self._cfg)
        # clear stop flag and kick the loop
        self._worker.request_stop()
        self._worker._stop_evt.clear()
        QtCore.QMetaObject.invokeMethod(self._worker, "run", QtCore.Qt.QueuedConnection)

    @QtCore.pyqtSlot()
    def stop(self):
        self._worker.request_stop()

    def stop_blocking(self, timeout_ms: int = 1500):
        if not self._running:
            return
        self.stop()
        loop = QtCore.QEventLoop()
        def quit_loop():
            if loop.isRunning():
                loop.quit()
        try:
            self.stopped.connect(quit_loop, QtCore.Qt.UniqueConnection)
        except TypeError:
            self.stopped.connect(quit_loop)
        QtCore.QTimer.singleShot(timeout_ms, quit_loop)
        loop.exec_()
        try:
            self.stopped.disconnect(quit_loop)
        except Exception:
            pass

    # -------- pick location flow --------
    def _teardown_picker(self):
        if self._pick_listener is not None:
            try:
                self._pick_listener.stop()
            except Exception:
                pass
            self._pick_listener = None
        if self._pick_dialog is not None:
            try:
                self._pick_dialog.close()
            except Exception:
                pass
            self._pick_dialog = None

    @QtCore.pyqtSlot()
    def start_pick_position(self):
        """Shows a tiny popup and listens globally for F/ESC.
           On F: capture mouse coords, set cursor_mode='pick', update cfg, emit positionPicked(x,y)."""
        self._teardown_picker()

        # 1) Small always-on-top popup
        self._pick_dialog = _PickPositionDialog()
        self._pick_dialog.show()

        # 2) Global listener (so F works anywhere)
        from pynput import keyboard
        done = {"v": False}

        def finish(ok: bool):
            if done["v"]:
                return
            done["v"] = True
            self._teardown_picker()
            if ok:
                x, y = pyautogui.position()
                self._cfg.x, self._cfg.y = int(x), int(y)
                self._cfg.cursor_mode = "pick"
                self.positionPicked.emit(self._cfg.x, self._cfg.y)

        def on_press(key):
            # accept F, cancel ESC
            try:
                ch = (key.char or "").lower()
            except AttributeError:
                ch = ""
            if ch == 'f':
                finish(True)
                return False  # stop listener
            if key == keyboard.Key.esc:
                finish(False)
                return False  # stop listener

        self._pick_listener = keyboard.Listener(on_press=on_press)
        self._pick_listener.daemon = True
        self._pick_listener.start()


# ---------------- Tiny popup dialog used by picker ----------------
class _PickPositionDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.Tool)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setModal(False)

        self._wrap = QtWidgets.QFrame()
        self._wrap.setStyleSheet(get_pick_dialog_stylesheet())
        lay = QtWidgets.QVBoxLayout(self._wrap)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)
        title = QtWidgets.QLabel("Pick position")
        title.setStyleSheet("font-weight:700;")
        info = QtWidgets.QLabel("Press  <b>F</b>  anywhere to set position  •  <b>Esc</b>  to cancel")
        lay.addWidget(title)
        lay.addWidget(info)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._wrap)

        self._reposition()

    def _reposition(self):
        screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos())
        if not screen:
            screen = QtWidgets.QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        sz = self.sizeHint()
        w, h = max(320, sz.width()), max(80, sz.height())
        self.resize(w, h)
        self.move(geo.center() - QtCore.QPoint(w // 2, int(geo.height() * 0.25)))
