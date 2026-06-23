# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent

_EXCLUDED_DATA_SUFFIXES = frozenset({".pyc", ".pyo", ".pyd"})


def _is_excluded_plugin_data(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if "__pycache__" in rel.parts:
        return True
    return path.suffix.lower() in _EXCLUDED_DATA_SUFFIXES


def _collect_tree(root: Path, prefix: str, *, filter_plugins: bool = False) -> list[tuple[str, str]]:
    if not root.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if filter_plugins and _is_excluded_plugin_data(file_path, root):
            continue
        dest = str(Path(prefix) / file_path.relative_to(root))
        out.append((str(file_path), dest))
    return out


datas: list[tuple[str, str]] = []
_plugins = ROOT / "plugins"
_assets = ROOT / "assets"
datas += _collect_tree(_plugins, "plugins", filter_plugins=True)
datas += _collect_tree(_assets, "assets", filter_plugins=False)

_maps_cache = ROOT / "plugins" / "Phasmo" / "Maps" / "cache"
if _maps_cache.is_dir():
    datas += _collect_tree(_maps_cache, "plugins/Phasmo/Maps/cache", filter_plugins=True)

binaries: list = []
hiddenimports = ["sip"]
hiddenimports += collect_submodules("app")
hiddenimports += collect_submodules("plugins")

for pkg in ("PyQt5", "PyQt5_sip", "pyautogui", "pynput", "PIL", "numpy", "psutil", "screen_brightness_control"):
    tmp = collect_all(pkg)
    datas += tmp[0]
    binaries += tmp[1]
    hiddenimports += tmp[2]

a = Analysis(
    [str(ROOT / "Main" / "MainAuto.py")],
    pathex=[str(ROOT), str(ROOT / "Main"), str(ROOT / "plugins")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["games"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Prime-Autoclicker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
