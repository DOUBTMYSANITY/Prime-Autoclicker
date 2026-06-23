# Third-Party Notices

Prime Autoclicker is licensed under **GPL-3.0** (see [LICENSE](LICENSE)).
This file lists direct and notable transitive open-source components used by the application.

## Direct dependencies

| Package | License | Role |
|---|---|---|
| PyQt5 | GPL-3.0 | Desktop UI (Qt bindings) |
| pynput | LGPL-3.0 | Global keyboard/mouse hooks and input simulation |
| PyAutoGUI | BSD-3-Clause | Mouse click automation (`single_clicker`) |
| cryptography | Apache-2.0 OR BSD-3-Clause | Read-only Phasmophobia save version detection |
| numpy | BSD-3-Clause (and bundled sub-licenses) | Pulled in by PyAutoGUI / image stack |
| Pillow | MIT-CMU | Image handling (PyAutoGUI dependency chain) |
| psutil | BSD-3-Clause | CPU/memory display on Stats page |
| screen_brightness_control | MIT | Optional monitor brightness boost (Phasmo plugin) |
| pywin32 | PSF License | Windows API access (gamma ramp, process info) |

## Notable transitive dependencies

Installed automatically with the packages above. Include these notices when distributing binaries.

| Package | License | Pulled in by |
|---|---|---|
| MouseInfo | GPL-3.0-or-later | PyAutoGUI |
| PyMsgBox | GPL-3.0-or-later | PyAutoGUI |
| PyScreeze | MIT | PyAutoGUI |
| PyGetWindow | BSD-3-Clause | PyAutoGUI |
| pyperclip | BSD-3-Clause | PyAutoGUI |
| pytweening | MIT | PyAutoGUI |
| PyQt5-Qt5 | LGPL-3.0 | PyQt5 (Qt runtime libraries) |
| PyQt5_sip | BSD-2-Clause | PyQt5 |
| cffi | MIT | cryptography |
| pycparser | BSD-3-Clause | cffi |
| WMI | MIT | screen_brightness_control (Windows) |

Run `pip install pip-licenses && pip-licenses --format=markdown` after install for the full dependency tree in your environment.

## GPL-3.0 distribution (binaries / EXE)

Because this project uses **PyQt5** and **GPL-licensed components** (including MouseInfo and PyMsgBox via PyAutoGUI), distributed binaries must:

1. Stay under **GPL-3.0** (same license as this repository).
2. Include the **GPL-3.0 license text** ([LICENSE](LICENSE)).
3. Include this **THIRD_PARTY_NOTICES.md** file (or equivalent notices).
4. Provide **corresponding source** — satisfied by linking to:  
   https://github.com/DOUBTMYSANITY/Prime-Autoclicker

Add that source URL to every GitHub Release when you publish `Prime-Autoclicker.exe`.

## LGPL note (pynput)

pynput is **LGPL-3.0**. It is used as a dynamically loaded library in this Python application. Users may replace the pynput library module with a modified version, consistent with LGPL-3.0.

## Removed / not bundled

The following are **not** required for this project and are omitted from `requirements.txt`:

- **PyQtWebEngine** — not used in application code
- **PyDirectInput** — not imported; pynput/PyAutoGUI are used instead
- **mss** — not imported

## External tools (not bundled)

- **Phasmophobia fan content** — see [PHASMOPHOBIA_FAN_CONTENT.md](PHASMOPHOBIA_FAN_CONTENT.md) for the Kinetic Games fan creation notice.
- **PhasmoSaveEditor** (`../../PhasmoSaveEditor/`) — save file editor only; separate project, not part of this release.
