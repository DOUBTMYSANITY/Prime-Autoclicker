import sys
import signal
import threading
import traceback
from pathlib import Path

def _install_interrupt_excepthook() -> None:
    """Avoid noisy callback tracebacks when Ctrl+C interrupts Qt internals."""
    _orig = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        if exc_type is KeyboardInterrupt:
            return
        print("Unhandled crash detected:", file=sys.stderr)
        traceback.print_exception(exc_type, exc_value, exc_tb)
        sys.stderr.flush()
        _orig(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook

    def _thread_hook(args):
        if args.exc_type is KeyboardInterrupt:
            return
        print(f"Unhandled thread crash in {args.thread.name}:", file=sys.stderr)
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
        sys.stderr.flush()

    threading.excepthook = _thread_hook

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app import setup_paths

setup_paths()

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, QTimer, QThread, pyqtSignal, Qt
from app.styling.themes import get_theme
from app.gui.widgets import CinematicLoadingScreen

try:
    from PyQt5.QtCore import QCoreApplication
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
except Exception:
    pass


class MainWindowImportWorker(QObject):
    """Loads the heavy GUI module off the main thread."""

    finished = pyqtSignal(object, str)

    def run(self):
        try:
            from app.gui.main_window import MainWindow as ImportedMainWindow
            self.finished.emit(ImportedMainWindow, "")
        except Exception:
            self.finished.emit(None, traceback.format_exc())


class StartupBootstrap(QObject):
    """Coordinates delayed splash display and background UI bootstrapping."""

    def __init__(self, app: QApplication, splash: CinematicLoadingScreen, splash_delay_ms: int = 220):
        super().__init__()
        self._app = app
        self._splash = splash
        self._splash_delay_ms = max(0, int(splash_delay_ms))
        self._main_window = None
        self._main_window_cls = None
        self._main_ready = False
        self._splash_visible = False
        self._import_thread: QThread | None = None
        self._import_worker: MainWindowImportWorker | None = None
        self._app.aboutToQuit.connect(self._shutdown_import_thread)

    def start(self):
        QTimer.singleShot(self._splash_delay_ms, self._show_splash_if_needed)
        self._start_background_import()

    def _start_background_import(self):
        self._import_thread = QThread(self)
        self._import_worker = MainWindowImportWorker()
        self._import_worker.moveToThread(self._import_thread)
        self._import_thread.started.connect(self._import_worker.run)
        self._import_worker.finished.connect(self._on_import_finished)
        self._import_worker.finished.connect(self._import_thread.quit)
        self._import_worker.finished.connect(self._import_worker.deleteLater)
        self._import_thread.finished.connect(self._import_thread.deleteLater)
        self._import_thread.start()

    def _on_import_finished(self, main_window_cls, error_text: str):
        if main_window_cls is None:
            if error_text:
                print(error_text)
            self._shutdown_import_thread()
            self._app.quit()
            return
        self._main_window_cls = main_window_cls
        QTimer.singleShot(0, self._create_main_window)

    def _shutdown_import_thread(self):
        thread = self._import_thread
        if thread is None:
            return
        try:
            running = thread.isRunning()
        except RuntimeError:
            self._import_thread = None
            self._import_worker = None
            return
        if running:
            thread.quit()
            if not thread.wait(2000):
                thread.terminate()
                thread.wait(500)
        self._import_thread = None
        self._import_worker = None

    def _show_splash_if_needed(self):
        if self._main_ready or self._splash_visible:
            return
        screen_rect = self._app.primaryScreen().availableGeometry()
        self._splash.show_animated(screen_rect)
        self._splash_visible = True

    def _create_main_window(self):
        if self._main_window_cls is None:
            return
        self._main_window = self._main_window_cls()
        self._main_ready = True
        self._try_finish_startup()

    def _try_finish_startup(self):
        if not self._main_ready:
            return
        if self._splash_visible:
            self._splash.stop_and_hide()
            QTimer.singleShot(320, self._show_main_window)
            return
        self._show_main_window()

    def _show_main_window(self):
        if self._main_window is None:
            self._app.quit()
            return
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()


def main():
    _install_interrupt_excepthook()
    try:
        app = QApplication(sys.argv)

        def _sigint_handler(*_args):
            app.quit()
        signal.signal(signal.SIGINT, _sigint_handler)

        theme = get_theme()
        theme_colors = theme.get("palette", {})
        cinematic_colors = {
            "bg_start": theme_colors.get("bg_start", "#0B1630"),
            "bg_mid": theme_colors.get("bg_mid", "#0B1B3A"),
            "bg_end": theme_colors.get("bg_end", "#7A2CFF"),
            "primary": theme_colors.get("accent_solid", "#5B73E8"),
            "secondary": theme_colors.get("slider_handle", "#8B5CF6"),
            "accent": theme_colors.get("accent_light", "#00D9FF"),
            "text_primary": theme_colors.get("text_primary", "#E0E0E0"),
        }

        splash = CinematicLoadingScreen(cinematic_colors)
        bootstrap = StartupBootstrap(app, splash, splash_delay_ms=220)
        app._startup_bootstrap = bootstrap
        bootstrap.start()

        try:
            exit_code = app.exec_()
        except KeyboardInterrupt:
            exit_code = 130
        sys.exit(exit_code)
    except Exception:
        print("Fatal startup crash:", file=sys.stderr)
        traceback.print_exc()
        sys.stderr.flush()
        raise


if __name__ == "__main__":
    main()
