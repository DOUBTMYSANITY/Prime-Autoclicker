# Prime Autoclicker

Desktop autoclicker with plugin system, macro builder, stats, and an optional **unofficial** Phasmophobia reference plugin.

Licensed under **GPL-3.0** (see [LICENSE](LICENSE)).

## Community

- **Discord** — [Prime Projects](https://discord.gg/nkQT7XCX) (support, updates, feedback)
- **GitHub** — set `MTA_GITHUB_REPO` locally or configure under Support → Update Checker

## Requirements

- Python 3.11+
- Windows (primary target)

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python Main/MainAuto.py
```

## Optional environment variables

| Variable | Purpose |
|---|---|
| `MTA_ADMIN_PASSWORD` | Password for the hidden admin panel |
| `MTA_GITHUB_REPO` | GitHub repo for About link and update checker (`owner/Prime-Autoclicker`) |
| `MTA_BUNDLE_SIGNING_KEY` | HMAC key for signed profile import/export bundles |

## Plugins (built-in)

- **Unofficial Phasmophobia reference** — offline ghost guide, timers, field guide (no save editor; not affiliated with Kinetic Games)
- **Route Recorder** — record/replay input routes
- **Input Humanization** — natural timing variation for clicks
- **Preset Benchmark** — runtime stability telemetry

## Security

- Plugins load from an **allowlist** in `app/services/plugin_system.py`
- Profile bundles are **HMAC-signed** on export and verified on import
- Do not import bundles from untrusted sources even if signed with a known weak dev key

## Disclaimer

This software automates mouse and keyboard input. Use responsibly and only where permitted.
Not affiliated with Mojang, Kinetic Games, or any game publisher. The Phasmophobia plugin is an **unofficial fan reference** — not endorsed by Kinetic Games.
Automation may violate third-party Terms of Service — **use at your own risk**.

The Phasmophobia **save editor** lives in a separate folder: `../PhasmoSaveEditor/` (not part of this release).

## Third-party licenses

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
