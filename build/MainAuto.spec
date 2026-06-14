# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_all

ROOT = Path(SPECPATH).resolve().parent.parent

datas = [
    (str(ROOT / "plugins" / "Phasmo" / "Maps" / "cache"), "plugins/Phasmo/Maps/cache"),
]
binaries = []
hiddenimports = ["sip", "cryptography"]
hiddenimports += collect_submodules("app")
hiddenimports += collect_submodules("plugins")
hiddenimports += collect_submodules("cryptography.hazmat.backends")
hiddenimports += collect_submodules("cryptography.hazmat.bindings.openssl")
hiddenimports += ["_cffi_backend"]

for pkg in ("PyQt5", "PyQt5_sip", "pyautogui", "pynput", "PIL", "numpy", "pydirectinput"):
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
    name="MainAuto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
