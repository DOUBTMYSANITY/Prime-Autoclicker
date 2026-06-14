# Third-Party Notices

This project uses the following open-source components:

| Package | License | Notes |
|---|---|---|
| PyQt5 | GPL-3.0 | Qt bindings — requires GPL-compatible licensing for distribution |
| PyQtWebEngine | GPL-3.0 | Chromium-based web engine component |
| pynput | LGPL-3.0 | Input monitoring; dynamic linking |
| PyDirectInput | MIT | DirectInput simulation |
| PyAutoGUI | BSD-3-Clause | Cross-platform GUI automation |
| cryptography | Apache-2.0 OR BSD-3-Clause | Save-version detection (Phasmo plugin) |
| numpy | BSD-3-Clause | Numerical utilities |
| Pillow | HPND | Image handling |
| mss | MIT | Screen capture |
| psutil | BSD-3-Clause | System diagnostics |
| pywin32 | PSF License | Windows API access |

Run `pip-licenses` after install for the full dependency tree in your environment.

## PyQt5 / GPL compliance

When distributing binaries built with PyQt5, you must comply with GPL-3.0 (provide corresponding source, license text, and notices).

## Separate projects

- **PhasmoSaveEditor** (`../PhasmoSaveEditor/`) — not bundled; separate legal review recommended before distribution.
