# panel.py — main entry point (global hotkeys + robust stop) [DEBUG-SAFE]
# X          = start/stop (debounced; one toggle per key press)
# Shift+Esc  = emergency stop + quit
#
# This version adds:
# - faulthandler (so native crashes print a Python-level stack)
# - Qt message logger
# - clean listener shutdown
# - no os._exit while debugging (so errors can print)
# - extra guardrails + prints

import sys, time
from PyQt5 import QtCore, QtWidgets
from pynput import keyboard
from legacy.main_gui import MainWindow

# ---------- DEBUG INSTRUMENTATION ----------
import faulthandler, traceback
faulthandler.enable()

def _excepthook(exc_type, exc, tb):
    print("\n=== Uncaught exception ===", file=sys.stderr, flush=True)
    traceback.print_exception(exc_type, exc, tb)
sys.excepthook = _excepthook

def _qt_msg(mode, context, message):
    m = {
        QtCore.QtInfoMsg:    "INFO",
        QtCore.QtWarningMsg: "WARNING",
        QtCore.QtCriticalMsg:"CRITICAL",
        QtCore.QtFatalMsg:   "FATAL",
        QtCore.QtDebugMsg:   "DEBUG",
    }.get(mode, str(mode))
    print(f"[Qt{m}] {message}", file=sys.stderr, flush=True)

QtCore.qInstallMessageHandler(_qt_msg)
# ------------------------------------------


class _Relay(QtCore.QObject):
    def __init__(self, win: MainWindow, app: QtWidgets.QApplication, listener: keyboard.Listener):
        super().__init__()
        self.win = win
        self.app = app
        self.listener = listener
        self.engine = None
        self.is_running = False
        self._toggling = False

        # Ensure listener stops *after* Qt quits so threads exit cleanly
        app.aboutToQuit.connect(self._on_about_to_quit)

    @QtCore.pyqtSlot()
    def _on_about_to_quit(self):
        try:
            if self.listener:
                self.listener.stop()
        except Exception as e:
            print(f"[panel] listener.stop() error: {e}", flush=True)

    # keep our engine reference in sync with whatever your GUI is using
    def _ensure_engine(self) -> bool:
        eng = None
        try:
            eng = getattr(self.win, "logic", None)
            eng = getattr(eng, "_single_logic", None)
        except Exception:
            eng = None

        if eng is not None and eng is not self.engine:
            # disconnect old
            if self.engine is not None:
                for sig, slot in ((self.engine.started, self._on_started),
                                  (self.engine.stopped, self._on_stopped)):
                    try: sig.disconnect(slot)
                    except Exception: pass
            self.engine = eng
            # connect new
            try: self.engine.started.connect(self._on_started, QtCore.Qt.UniqueConnection)
            except Exception: 
                try: self.engine.started.connect(self._on_started)
                except Exception: pass
            try: self.engine.stopped.connect(self._on_stopped, QtCore.Qt.UniqueConnection)
            except Exception:
                try: self.engine.stopped.connect(self._on_stopped)
                except Exception: pass

            print("[panel] Engine wired", flush=True)

        return self.engine is not None

    def _on_started(self):
        self.is_running = True
        print("[panel] engine -> started", flush=True)

    def _on_stopped(self):
        self.is_running = False
        print("[panel] engine -> stopped", flush=True)

    # ---- RUNS IN GUI THREAD ----
    @QtCore.pyqtSlot()
    def toggle(self):
        if self._toggling:
            return
        self._toggling = True
        try:
            if not self._ensure_engine():
                print("[panel] toggle ignored: engine not ready", flush=True)
                return

            if self.is_running:
                print("[panel] stopping (blocking)…", flush=True)
                try:
                    # Requires Single_Clicker_Logic.stop_blocking
                    self.engine.stop_blocking(2000)
                except Exception as e:
                    print(f"[panel] stop_blocking error: {e}", flush=True)
            else:
                print("[panel] starting…", flush=True)
                try:
                    self.engine.start()
                except Exception as e:
                    print(f"[panel] start error: {e}", flush=True)
        finally:
            self._toggling = False

    @QtCore.pyqtSlot()
    def panic(self):
        if self._ensure_engine():
            print("[panel] PANIC: stopping (blocking)…", flush=True)
            try:
                self.engine.stop_blocking(1500)
            except Exception as e:
                print(f"[panel] panic stop_blocking error: {e}", flush=True)
        print("[panel] quitting app…", flush=True)
        # Do NOT os._exit while debugging; let Qt tear down cleanly so we can see errors
        self.app.quit()


def main():
    # High DPI must be set before creating the app
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()

    # --- Debounced global hotkeys (runs in non-Qt thread; we hop to GUI thread) ---
    state = {
        "shift_down": False,
        "x_down": False,
        "last_toggle": 0.0,
        "min_toggle_gap": 0.25,
    }

    relay_ref = {}  # will store relay after listener is created

    def on_press(key):
        try:
            ch = (key.char or "").lower()
        except AttributeError:
            ch = ""

        if ch == 'x':
            if not state["x_down"]:
                now = time.perf_counter()
                if now - state["last_toggle"] >= state["min_toggle_gap"]:
                    state["x_down"] = True
                    state["last_toggle"] = now
                    QtCore.QMetaObject.invokeMethod(relay_ref["relay"], "toggle", QtCore.Qt.QueuedConnection)
            return

        if key == keyboard.Key.shift:
            state["shift_down"] = True
        elif key == keyboard.Key.esc and state["shift_down"]:
            QtCore.QMetaObject.invokeMethod(relay_ref["relay"], "panic", QtCore.Qt.QueuedConnection)

    def on_release(key):
        try:
            ch = (key.char or "").lower()
        except AttributeError:
            ch = ""
        if ch == 'x':
            state["x_down"] = False
        elif key == keyboard.Key.shift:
            state["shift_down"] = False

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    relay = _Relay(win, app, listener)
    relay_ref["relay"] = relay

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
