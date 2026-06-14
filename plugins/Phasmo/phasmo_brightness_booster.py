"""Hardware backlight + offset gamma boost for Phasmo."""
from __future__ import annotations

import atexit
import ctypes
import sys

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None  # type: ignore

_IS_WINDOWS = sys.platform.startswith("win")
_GammaArray = ctypes.c_ushort * 256 * 3

_hdc: int | None = None
_gamma_ramp_active = False
_saved_backlight: list[int] | None = None
_last_gamma_params: tuple[float, float] | None = None
_last_backlight_target: int | None = None


def _get_hdc() -> int:
    global _hdc
    if _hdc is None and _IS_WINDOWS:
        _hdc = int(ctypes.windll.user32.GetDC(None))
    return _hdc if _hdc is not None else 0


def _release_hdc() -> None:
    global _hdc
    if _hdc is not None and _IS_WINDOWS:
        ctypes.windll.user32.ReleaseDC(None, _hdc)
        _hdc = None


def _level_to_gamma_params(level: int) -> tuple[float, float]:
    """Map slider 0-100 to factor (1.0-1.4) and black-lift offset (0-40)."""
    clamped = max(0, min(100, int(level)))
    factor = 1.0 + (clamped / 100.0) * 0.4
    offset = (clamped / 100.0) * 40.0
    return factor, offset


def _read_monitor_brightness() -> list[int]:
    if sbc is None:
        return []
    values = sbc.get_brightness()
    if isinstance(values, list):
        return [int(v) for v in values]
    return [int(values)]


def _apply_monitor_brightness(values: list[int]) -> None:
    if sbc is None or not values:
        return
    if len(values) == 1:
        sbc.set_brightness(values[0])
    else:
        sbc.set_brightness(values)


def _ensure_backlight_saved() -> None:
    global _saved_backlight
    if _saved_backlight is None and sbc is not None:
        _saved_backlight = _read_monitor_brightness()


def _restore_backlight() -> None:
    global _saved_backlight, _last_backlight_target
    if sbc is None or _saved_backlight is None:
        return
    try:
        _apply_monitor_brightness(_saved_backlight)
    except Exception:
        pass
    _saved_backlight = None
    _last_backlight_target = None


def _sync_backlight(*, gamma_on: bool, monitor_on: bool, monitor_level: int) -> None:
    """Gamma cranks hardware backlight to 100; monitor-only uses the slider."""
    global _last_backlight_target
    if sbc is None:
        return
    if not gamma_on and not monitor_on:
        _restore_backlight()
        _last_backlight_target = None
        return
    target = 100 if gamma_on else max(1, min(100, int(monitor_level)))
    if _last_backlight_target == target:
        return
    _ensure_backlight_saved()
    _apply_monitor_brightness([target])
    _last_backlight_target = target


def _set_gamma_ramp(factor: float, offset: float = 0.0) -> bool:
    if not _IS_WINDOWS:
        return False
    hdc = _get_hdc()
    if hdc == 0:
        return False
    ramp = _GammaArray()
    for i in range(256):
        value = int(i * 256 * factor + offset * 256)
        value = max(0, min(65535, value))
        ramp[0][i] = value
        ramp[1][i] = value
        ramp[2][i] = value
    try:
        return bool(ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp)))
    except Exception:
        return False


def _reset_gamma_ramp() -> None:
    global _gamma_ramp_active, _last_gamma_params
    if not _gamma_ramp_active:
        return
    _set_gamma_ramp(1.0, 0.0)
    _gamma_ramp_active = False
    _last_gamma_params = None


def _reset_on_exit() -> None:
    if _gamma_ramp_active:
        _reset_gamma_ramp()
    _restore_backlight()
    _release_hdc()


class PhasmoBrightnessManager:
    """Hardware backlight + lifted gamma curve (best used together)."""

    _atexit_registered = False

    def __init__(self) -> None:
        self._monitor_enabled = False
        self._monitor_level = 100
        self._gamma_enabled = False
        self._gamma_level = 60
        self._register_atexit_once()

    @classmethod
    def _register_atexit_once(cls) -> None:
        if cls._atexit_registered:
            return
        atexit.register(_reset_on_exit)
        cls._atexit_registered = True

    def apply(
        self,
        *,
        brightness_enabled: bool,
        brightness_level: int,
        gamma_enabled: bool,
        gamma_level: int,
    ) -> None:
        self._monitor_level = max(0, min(100, int(brightness_level)))
        self._gamma_level = max(0, min(100, int(gamma_level)))
        self._monitor_enabled = bool(brightness_enabled) and self._monitor_level > 0
        self._gamma_enabled = bool(gamma_enabled) and self._gamma_level > 0
        self._apply_state()

    def toggle_gamma(self) -> bool:
        if self._gamma_enabled:
            self._gamma_enabled = False
        elif self._gamma_level > 0:
            self._gamma_enabled = True
        self._apply_state()
        return self._gamma_enabled

    def toggle_brightness(self) -> bool:
        if self._monitor_enabled:
            self._monitor_enabled = False
        elif self._monitor_level > 0:
            self._monitor_enabled = True
        self._apply_state()
        return self._monitor_enabled

    def toggle(self) -> bool:
        return self.toggle_gamma()

    def hide(self) -> None:
        self._monitor_enabled = False
        self._gamma_enabled = False
        self._apply_state()

    def shutdown(self) -> None:
        self.hide()
        _release_hdc()

    def _apply_state(self) -> None:
        global _gamma_ramp_active, _last_gamma_params

        if self._gamma_enabled:
            factor, offset = _level_to_gamma_params(self._gamma_level)
            params = (factor, offset)
            if params != _last_gamma_params:
                if _set_gamma_ramp(factor, offset):
                    _gamma_ramp_active = True
                    _last_gamma_params = params
                else:
                    self._gamma_enabled = False
                    _reset_gamma_ramp()
        else:
            _reset_gamma_ramp()

        _sync_backlight(
            gamma_on=self._gamma_enabled,
            monitor_on=self._monitor_enabled,
            monitor_level=self._monitor_level,
        )
