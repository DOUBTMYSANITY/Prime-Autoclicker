# Prime Autoclicker

Desktop autoclicker with plugin system, macro builder, stats, and an optional **unofficial** Phasmophobia reference plugin.

**Current release: v1.1.0**

Licensed under **GPL-3.0** (see [LICENSE](LICENSE)).

## About this project

Prime Autoclicker was **mostly built with AI assistance** (Cursor and similar tools). As a solo student project, there is not enough free time outside of school to hand-write every feature from scratch — AI helped with structure, UI, plugins, packaging, and documentation. The project is still maintained, tested, and released under GPL-3.0; contributions and issue reports are welcome.

## Community

- **Discord** — [Prime Projects](https://discord.gg/nkQT7XCX) (support, updates, feedback)
- **GitHub** — [DOUBTMYSANITY/Prime-Autoclicker](https://github.com/DOUBTMYSANITY/Prime-Autoclicker)

## Requirements

- Python 3.11+
- **Windows** (primary target — full feature set)
- **Linux/macOS** (experimental — core autoclicker may run; some Windows-only plugins/features are disabled)

## Install

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python Main/MainAuto.py
```

### Standalone unofficial Phasmo reference (no autoclicker UI)

```bash
python Main/MainAuto.py --phasmo-only
```

## Optional environment variables

| Variable | Purpose |
|---|---|
| `MTA_ADMIN_PASSWORD` | Password for the hidden admin panel |
| `MTA_ADMIN_EASTER_EGG` | Optional code typed in the interval field to open the admin prompt (disabled if unset) |
| `MTA_GITHUB_REPO` | GitHub repo for About link and update checker (`DOUBTMYSANITY/Prime-Autoclicker`) |
| `MTA_BUNDLE_SIGNING_KEY` | HMAC key for signed profile import/export bundles |

## Plugins (built-in)

- **Unofficial Phasmophobia reference** — offline ghost guide, timers, Tanglewood map, field guide (no save editor; not affiliated with Kinetic Games)
- **Route Recorder** — record/replay input routes (keyboard recording off by default)
- **Input Humanization** — jitter, micro-pauses, fatigue curves in the click engine
- **Preset Benchmark** — per-session smoothness / accuracy score

## v1.1.0 highlights

- First-run disclaimer dialog
- System tray minimize + compact click HUD (click count)
- Input Humanization wired into clicks
- Preset Benchmark telemetry + toast summary
- Per-app preset binding (Presets → **Bind to active app**)
- Macro flow loops + JSON import/export
- Color/pixel auto-stop trigger (Settings → Advanced)
- Tanglewood map page in Phasmo plugin
- GitHub release update notification
- `--phasmo-only` standalone reference mode

## Security

- Plugins load from an **allowlist** in `app/services/plugin_system.py`
- Profile bundles are **HMAC-signed** on export and verified on import
- Admin easter-egg code is **not hardcoded** — set `MTA_ADMIN_EASTER_EGG` if you need it
- Route Recorder keyboard capture defaults to **off** with an in-app warning

## Disclaimer

### General (autoclicker)

This software automates mouse and keyboard input. Use responsibly and only where permitted.
Automation may violate third-party Terms of Service — **use at your own risk**.

Not affiliated with Mojang or any game publisher.

### Phasmophobia fan content (Kinetic Games)

*Phasmophobia* is a game by [Kinetic Games](https://www.kineticgames.co.uk/).

The optional Phasmophobia reference plugin is **fan-created content** shared under Kinetic Games' [Fan Creation Policy](https://www.kineticgames.co.uk/fan-creation-policy). It does **not** edit save files — see [PhasmoSaveEditor](../../PhasmoSaveEditor/) for that separate tool.

This third-party material, product or tool is an independent, non-commercial, not-for-profit project and is not affiliated with, endorsed by or sponsored by Kinetic Games.

Any use of Kinetic Games' trademarks, logos, copyrighted materials or the 'Phasmophobia' brand is for descriptive and/or informational purposes only.

Such use has not been authorised by Kinetic Games and does not constitute a licence, consent or waiver of Kinetic Games' rights, all of which are expressly reserved.

Kinetic Games has not reviewed, assessed or approved this project and makes no representations or warranties as to its accuracy, quality, functionality, or fitness for purpose.

The third-party material, product and/or tool comprised in this project is provided "as is". Use is at the end user's own risk and Kinetic Games shall have no liability arising out of or in connection with any person's reliance on, or use of, such project, material, product or tool.

See also [PHASMOPHOBIA_FAN_CONTENT.md](PHASMOPHOBIA_FAN_CONTENT.md).

## Third-party licenses

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Roadmap

### v1.2+ (planned)

- Portable mode (config next to EXE)
- More Phasmo maps / data packs
- Deeper Linux support and packaging
- Optional PyQtWebEngine embed for maps without browser fallback

Track progress on [GitHub Issues](https://github.com/DOUBTMYSANITY/Prime-Autoclicker/issues) and [Releases](https://github.com/DOUBTMYSANITY/Prime-Autoclicker/releases).
