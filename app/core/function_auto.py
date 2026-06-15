from __future__ import annotations

import copy
import ctypes
import sys
import time
import random
import threading
import collections
from dataclasses import dataclass, field

from PyQt5.QtCore import QObject, pyqtSignal
from pynput.mouse import Controller, Button

_IS_WINDOWS = sys.platform.startswith("win")
_user32 = ctypes.windll.user32 if _IS_WINDOWS else None


@dataclass
class ClickConfig:
    use_cps: bool = True
    cps: float = 10.0
    interval_ms: int = 100

    button: str = "left"      # "left", "right", "middle"
    click_count: int = 0      # 0 = infinite
    random_jitter_ms: int = 0 # 0 = no jitter
    time_limit_ms: int = 0    # 0 = no time limit
    delay_ms: int = 0         # 0 = no delayed start

    use_fixed_position: bool = False
    fixed_x: int = 0
    fixed_y: int = 0

    press_and_hold: bool = False

    # Scroll wheel automation
    scroll_mode: bool = False
    scroll_direction: str = "down"  # "up" or "down"
    scroll_amount: int = 3          # lines per tick

    # Random position offset
    position_offset_px: int = 0  # ±px offset for each click

    # Multi-button combo
    combo_mode: str = "single"  # "single", "alternate", "double"
    combo_buttons: list = field(default_factory=lambda: ["left"])

    # CPS stabilization – auto-adjusts delay to hit target CPS
    cps_stabilize: bool = False
    # Smart stabilization bootstrap from prior successful sessions
    stabilize_bootstrap_ms: float = 0.0
    stabilize_warmup_clicks: int = 3

    # Lag guard – auto-stop if sustained inaccuracy indicates heavy lag
    lag_guard_enabled: bool = False
    lag_guard_min_accuracy: float = 65.0
    lag_guard_consecutive: int = 6

    # Window targeting – only click when this window is in the foreground
    target_hwnd: int = 0  # 0 = click anywhere, >0 = only click when this HWND is foreground

    # Cursor fail-safe stop zones
    edge_stop_enabled: bool = False
    edge_stop_margin_px: int = 6
    corner_stop_enabled: bool = True
    corner_stop_size_px: int = 20

    # Input humanization plugin
    humanization_enabled: bool = False
    humanization_jitter_min_ms: int = 2
    humanization_jitter_max_ms: int = 12
    humanization_micro_pause_every: int = 35
    humanization_micro_pause_ms: int = 45
    humanization_fatigue_curve: str = "soft"

    # Color / pixel trigger — stop when screen pixel matches (optional)
    color_trigger_enabled: bool = False
    color_trigger_x: int = 0
    color_trigger_y: int = 0
    color_trigger_rgb: tuple[int, int, int] = (255, 0, 0)
    color_trigger_tolerance: int = 12


class AutoRunner(QObject):
    started = pyqtSignal()
    stopped = pyqtSignal()
    click_performed = pyqtSignal(int)  # emitted as batched click counts
    click_at_position = pyqtSignal(int, int)  # x, y of each click for heatmap
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    # (target_cps, actual_cps, accuracy_pct, correction_ms)
    cps_adjusted = pyqtSignal(float, float, float, float)

    def __init__(self, config: ClickConfig):
        super().__init__()
        self._config = config
        self._lock = threading.Lock()

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._running = False
        self._paused = False

        self._mouse = Controller()

    def set_config(self, new_config: ClickConfig) -> None:
        with self._lock:
            self._config = new_config

    def is_running(self) -> bool:
        return self._running

    def is_paused(self) -> bool:
        return self._running and self._paused

    def pause(self) -> None:
        if not self._running:
            return
        self._paused = True
        self._pause_event.set()

    def resume(self) -> None:
        if not self._running:
            return
        self._paused = False
        self._pause_event.clear()

    def toggle_pause(self) -> bool:
        if not self._running:
            return False
        if self._paused:
            self.resume()
        else:
            self.pause()
        return self._paused

    def start(self) -> None:
        if self._running:
            return
        self._stop_event.clear()
        self._pause_event.clear()
        self._paused = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._running = True
        self._thread.start()
        self.started.emit()

    def stop(self) -> None:
        if not self._running:
            return
        self._stop_event.set()
        self._pause_event.clear()
        self._paused = False

    def _wait_while_paused(self) -> bool:
        while self._pause_event.is_set() and not self._stop_event.is_set():
            self._stop_event.wait(0.01)
        return self._stop_event.is_set()

    def _get_config_snapshot(self) -> ClickConfig:
        with self._lock:
            snap = copy.copy(self._config)
            snap.combo_buttons = list(snap.combo_buttons)
            return snap

    @staticmethod
    def _btn_from_str(name: str) -> Button:
        if name == "right":
            return Button.right
        if name == "middle":
            return Button.middle
        return Button.left

    def _button_obj(self, cfg: ClickConfig) -> Button:
        return self._btn_from_str(cfg.button)

    def _compute_delay_seconds(self, cfg: ClickConfig, click_index: int = 0) -> float:
        if cfg.use_cps:
            cps = max(0.1, float(cfg.cps))
            base = 1.0 / cps
        else:
            base = max(1, int(cfg.interval_ms)) / 1000.0

        jitter = max(0, int(cfg.random_jitter_ms))
        if jitter > 0:
            base += random.randint(0, jitter) / 1000.0

        if cfg.humanization_enabled and click_index > 0:
            from app.services.input_humanization import HumanizationSettings, extra_delay_seconds

            hs = HumanizationSettings(
                enabled=True,
                jitter_min_ms=cfg.humanization_jitter_min_ms,
                jitter_max_ms=cfg.humanization_jitter_max_ms,
                micro_pause_every=cfg.humanization_micro_pause_every,
                micro_pause_ms=cfg.humanization_micro_pause_ms,
                fatigue_curve=cfg.humanization_fatigue_curve,
            )
            base += extra_delay_seconds(hs, click_index)

        return max(0.0, base)

    @staticmethod
    def _pixel_matches(cfg: ClickConfig) -> bool:
        if not cfg.color_trigger_enabled:
            return False
        try:
            import pyautogui

            r, g, b = pyautogui.pixel(cfg.color_trigger_x, cfg.color_trigger_y)
            tr, tg, tb = cfg.color_trigger_rgb
            tol = max(0, int(cfg.color_trigger_tolerance))
            return (
                abs(int(r) - int(tr)) <= tol
                and abs(int(g) - int(tg)) <= tol
                and abs(int(b) - int(tb)) <= tol
            )
        except Exception:
            return False

    def _precision_sleep(self, seconds: float) -> None:
        """High-precision sleep that works down to sub-millisecond intervals.

        Strategy:
        - If > 20 ms remaining and not stopped: use Event.wait() for the
          coarse portion (leaving ~2 ms for spin-wait).
        - Spin-wait (perf_counter loop) for the final portion to achieve
          microsecond-level accuracy.
        - Checks the stop event between phases so we stay responsive.
        """
        if seconds <= 0 or self._stop_event.is_set():
            return
        deadline = time.perf_counter() + seconds

        # Poll in short chunks so pause/resume stays responsive even for longer sleeps.
        while time.perf_counter() < deadline:
            if self._stop_event.is_set():
                return
            if self._pause_event.is_set():
                if self._wait_while_paused():
                    return
                continue
            remaining = max(0.0, deadline - time.perf_counter())
            if remaining <= 0:
                break
            step = min(0.01, remaining)
            self._stop_event.wait(step)

    def _run_loop(self) -> None:
        try:
            cfg = self._get_config_snapshot()
            btn = self._button_obj(cfg)

            # Delayed start
            delay = max(0, int(cfg.delay_ms))
            if delay > 0:
                self.status.emit(f"Starting in {delay}ms...")
                if self._stop_event.wait(delay / 1000.0):
                    return  # stopped during delay

            self.status.emit("Running")

            if cfg.press_and_hold:
                self._mouse.press(btn)

            performed = 0
            target = max(0, int(cfg.click_count))
            time_limit = max(0, int(cfg.time_limit_ms))
            start_time = time.time()
            combo_idx = 0

            # ── Signal throttling (prevent GUI flood at high CPS) ──
            _SIGNAL_INTERVAL = 0.050   # emit UI signals at most ~20 Hz
            _last_signal_time = 0.0
            _pending_clicks = 0        # clicks accumulated since last signal
            _CONFIG_REFRESH  = 0.100   # re-read config at most ~10 Hz
            _last_cfg_time   = 0.0

            # ── Advanced CPS stabilizer (adaptive PID + spin-wait) ──
            _click_times: collections.deque = collections.deque(maxlen=80)
            _loop_overheads: collections.deque = collections.deque(maxlen=50)
            _pid_integral = 0.0
            _pid_prev_error = 0.0
            _delay_correction = 0.0
            _warmup_clicks = max(0, int(cfg.stabilize_warmup_clicks))
            _stab_tick = 0
            _lag_bad_streak = 0
            _last_click_perf = time.perf_counter()
            _ideal_next = _last_click_perf  # when the next click *should* happen

            # Apply learned correction from previous successful runs.
            if cfg.cps_stabilize and cfg.stabilize_bootstrap_ms:
                _bootstrap = float(cfg.stabilize_bootstrap_ms) / 1000.0
                _base = self._compute_delay_seconds(cfg)
                _delay_correction = max(-_base * 0.98, min(_bootstrap, _base * 0.50))
                _ideal_next += max(0.0, _base - _delay_correction)

            while not self._stop_event.is_set():
                if self._pause_event.is_set():
                    if self._wait_while_paused():
                        break
                    continue

                # Throttle config re-reads to avoid lock contention at high CPS
                _now_cfg = time.perf_counter()
                if _now_cfg - _last_cfg_time >= _CONFIG_REFRESH:
                    cfg = self._get_config_snapshot()
                    btn = self._button_obj(cfg)
                    _last_cfg_time = _now_cfg

                # Window targeting: skip clicking when target window is not foreground
                if cfg.target_hwnd and _user32:
                    try:
                        fg = _user32.GetForegroundWindow()
                        if fg != cfg.target_hwnd:
                            self._stop_event.wait(0.05)
                            continue
                    except Exception:
                        pass

                # Cursor fail-safe: stop if pointer reaches configured edge/corner zones
                if _user32:
                    try:
                        mx, my = self._mouse.position
                        sw = int(_user32.GetSystemMetrics(0))
                        sh = int(_user32.GetSystemMetrics(1))
                        edge_margin = max(1, int(cfg.edge_stop_margin_px))
                        corner_size = max(1, int(cfg.corner_stop_size_px))

                        if cfg.corner_stop_enabled:
                            in_corner = (
                                (mx <= corner_size and my <= corner_size)
                                or (mx >= (sw - 1 - corner_size) and my <= corner_size)
                                or (mx <= corner_size and my >= (sh - 1 - corner_size))
                                or (mx >= (sw - 1 - corner_size) and my >= (sh - 1 - corner_size))
                            )
                            if in_corner:
                                self.status.emit("Auto-stopped: cursor entered corner fail-safe zone")
                                break

                        if cfg.edge_stop_enabled:
                            on_edge = (
                                mx <= edge_margin
                                or my <= edge_margin
                                or mx >= (sw - 1 - edge_margin)
                                or my >= (sh - 1 - edge_margin)
                            )
                            if on_edge:
                                self.status.emit("Auto-stopped: cursor entered edge fail-safe zone")
                                break
                    except Exception:
                        pass

                # Check time limit
                if time_limit > 0 and (time.time() - start_time) * 1000 >= time_limit:
                    break

                # Color trigger — stop when target pixel matches
                if self._pixel_matches(cfg):
                    self.status.emit("Auto-stopped: color trigger matched")
                    break

                if cfg.press_and_hold:
                    if self._stop_event.wait(self._compute_delay_seconds(cfg, performed + 1)):
                        break
                    continue

                # Scroll mode
                if cfg.scroll_mode:
                    amt = cfg.scroll_amount if cfg.scroll_direction == "up" else -cfg.scroll_amount
                    self._mouse.scroll(0, amt)
                    performed += 1
                    self.click_performed.emit(1)
                    pos = self._mouse.position
                    self.click_at_position.emit(pos[0], pos[1])
                    if target > 0 and performed >= target:
                        break
                    self._stop_event.wait(self._compute_delay_seconds(cfg, performed + 1))
                    continue

                # Move to fixed position if configured
                if cfg.use_fixed_position:
                    tx, ty = cfg.fixed_x, cfg.fixed_y
                    # Apply random position offset
                    off = cfg.position_offset_px
                    if off > 0:
                        tx += random.randint(-off, off)
                        ty += random.randint(-off, off)
                    self._mouse.position = (max(0, tx), max(0, ty))
                elif cfg.position_offset_px > 0:
                    # Offset around current position
                    cx, cy = self._mouse.position
                    off = cfg.position_offset_px
                    self._mouse.position = (
                        max(0, cx + random.randint(-off, off)),
                        max(0, cy + random.randint(-off, off)),
                    )

                # Combo mode clicking
                if cfg.combo_mode == "alternate" and len(cfg.combo_buttons) > 1:
                    current_btn = self._btn_from_str(cfg.combo_buttons[combo_idx % len(cfg.combo_buttons)])
                    self._mouse.click(current_btn, 1)
                    combo_idx += 1
                elif cfg.combo_mode == "double" and len(cfg.combo_buttons) > 1:
                    # Send the buttons as distinct clicks with a tiny gap so the OS
                    # reliably sees both the left and right click events.
                    for idx, b_name in enumerate(cfg.combo_buttons):
                        self._mouse.click(self._btn_from_str(b_name), 1)
                        if idx < len(cfg.combo_buttons) - 1:
                            if self._stop_event.wait(0.006):
                                break
                else:
                    self._mouse.click(btn, 1)

                performed += 1
                _pending_clicks += 1

                # Throttle signal emissions so the GUI stays responsive
                _now_sig = time.perf_counter()
                if _now_sig - _last_signal_time >= _SIGNAL_INTERVAL:
                    # Emit one batched signal to avoid flooding the GUI thread.
                    n = _pending_clicks
                    _pending_clicks = 0
                    self.click_performed.emit(n)
                    pos = self._mouse.position
                    self.click_at_position.emit(pos[0], pos[1])
                    _last_signal_time = _now_sig

                if target > 0 and performed >= target:
                    break

                # ── Compute sleep with optional CPS stabilization ──
                base_delay = self._compute_delay_seconds(cfg, performed)
                now_perf = time.perf_counter()
                _click_times.append(now_perf)
                _stab_tick += 1

                # Shared quality metrics used by both stabilizer and lag guard.
                if len(_click_times) >= 2 and _stab_tick % 8 == 0:
                    window_elapsed = _click_times[-1] - _click_times[0]
                    if window_elapsed > 0:
                        actual_cps = (len(_click_times) - 1) / window_elapsed
                    else:
                        actual_cps = 0.0
                    target_cps = 1.0 / base_delay if base_delay > 0 else 1000.0
                    err = abs(target_cps - actual_cps) / max(target_cps, 0.1)
                    accuracy = max(0.0, (1.0 - err) * 100.0)

                    if cfg.cps_stabilize or cfg.lag_guard_enabled:
                        self.cps_adjusted.emit(target_cps, actual_cps, accuracy, _delay_correction * 1000.0)

                    if cfg.lag_guard_enabled:
                        if accuracy < float(cfg.lag_guard_min_accuracy):
                            _lag_bad_streak += 1
                        else:
                            _lag_bad_streak = 0
                        if _lag_bad_streak >= max(1, int(cfg.lag_guard_consecutive)):
                            self.status.emit("Auto-stopped: lag protection triggered")
                            break

                if cfg.cps_stabilize:
                    # Track full loop-iteration overhead (click + bookkeeping)
                    loop_overhead = now_perf - _last_click_perf - (
                        base_delay - _delay_correction if _stab_tick > 1 else 0
                    )
                    if _stab_tick > 1 and loop_overhead > 0:
                        _loop_overheads.append(loop_overhead)
                    avg_overhead = (
                        sum(_loop_overheads) / len(_loop_overheads)
                        if _loop_overheads else 0.0
                    )
                    _last_click_perf = now_perf

                    target_cps = 1.0 / base_delay if base_delay > 0 else 1000.0

                    if len(_click_times) >= 2 and _stab_tick > _warmup_clicks:
                        # Measure actual CPS from the rolling window
                        window_elapsed = _click_times[-1] - _click_times[0]
                        if window_elapsed > 0:
                            actual_cps = (len(_click_times) - 1) / window_elapsed
                        else:
                            actual_cps = target_cps

                        # PID error: positive = too slow, need shorter delay
                        error = (target_cps - actual_cps) / max(target_cps, 0.1)

                        # Adaptive PID gains – much more aggressive at high CPS
                        if base_delay <= 0.005:       # ≤5 ms  (≥200 CPS)
                            Kp, Ki, Kd = 0.85, 0.30, 0.08
                        elif base_delay <= 0.015:     # ≤15 ms (≥67 CPS)
                            Kp, Ki, Kd = 0.70, 0.22, 0.07
                        elif base_delay <= 0.050:     # ≤50 ms (≥20 CPS)
                            Kp, Ki, Kd = 0.55, 0.15, 0.06
                        else:                         # slow clicking
                            Kp, Ki, Kd = 0.35, 0.08, 0.05

                        # Integral with anti-windup clamping
                        _pid_integral += error
                        _pid_integral = max(-3.0, min(3.0, _pid_integral))

                        # Derivative (rate of change of error)
                        derivative = error - _pid_prev_error
                        _pid_prev_error = error

                        # PID output (seconds to subtract from base)
                        correction = (
                            Kp * error
                            + Ki * _pid_integral
                            + Kd * derivative
                        ) * base_delay

                        # Always subtract known overhead
                        correction += avg_overhead

                        # Clamp: allow up to 98% reduction but no more than 50% increase
                        _delay_correction = max(
                            -base_delay * 0.98,
                            min(correction, base_delay * 0.50),
                        )

                        # Report every 8 ticks
                        if _stab_tick % 8 == 0:
                            accuracy = max(0.0, (1.0 - abs(error)) * 100.0)
                            correction_ms = _delay_correction * 1000.0
                            self.cps_adjusted.emit(
                                target_cps, actual_cps, accuracy, correction_ms
                            )
                    else:
                        # Warmup: subtract measured overhead right away
                        _delay_correction = avg_overhead
                        _ideal_next = now_perf + base_delay

                    # Schedule-based timing: where should the next click be?
                    _ideal_next += base_delay
                    actual_remaining = _ideal_next - time.perf_counter()

                    # Catch up if we drifted behind (don't let it accumulate)
                    if actual_remaining < -base_delay * 2:
                        _ideal_next = time.perf_counter() + base_delay * 0.1
                        actual_remaining = base_delay * 0.1

                    final_delay = max(0.0, actual_remaining)

                    # ── Precision sleep: hybrid wait + spin for sub-20ms ──
                    self._precision_sleep(final_delay)
                    continue   # skip the normal Event.wait below
                else:
                    final_delay = base_delay

                self._stop_event.wait(final_delay)

            # Flush any remaining pending click signals
            if _pending_clicks > 0:
                n = _pending_clicks
                _pending_clicks = 0
                self.click_performed.emit(n)
                try:
                    pos = self._mouse.position
                    self.click_at_position.emit(pos[0], pos[1])
                except Exception:
                    pass

        except Exception as e:
            self.error.emit(f"AutoRunner error: {e}")
        finally:
            try:
                cfg_final = self._get_config_snapshot()
                if cfg_final.press_and_hold:
                    self._mouse.release(self._button_obj(cfg_final))
            except Exception:
                pass

            self._running = False
            self.status.emit("Stopped")
            self.stopped.emit()
