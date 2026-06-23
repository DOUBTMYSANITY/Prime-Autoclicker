"""First-run disclaimer and acceptance tracking."""
from __future__ import annotations

import json
from pathlib import Path

_FLAG_FILE = Path.home() / ".mtautoclicker_first_run.json"
_DISCLAIMER_VERSION = 2


def disclaimer_accepted() -> bool:
    try:
        if not _FLAG_FILE.is_file():
            return False
        data = json.loads(_FLAG_FILE.read_text(encoding="utf-8"))
        return int(data.get("disclaimer_version", 0)) >= _DISCLAIMER_VERSION
    except Exception:
        return False


def mark_disclaimer_accepted() -> None:
    _FLAG_FILE.write_text(
        json.dumps({"disclaimer_version": _DISCLAIMER_VERSION, "accepted": True}, indent=2),
        encoding="utf-8",
    )


def show_first_run_disclaimer(parent) -> bool:
    """Show disclaimer dialog. Returns True if user may continue."""
    from PyQt5.QtWidgets import QMessageBox

    from plugins.Phasmo.phasmo_fan_disclaimer import ABOUT_PHASMO_DISCLAIMER, GAME_CREDIT

    if disclaimer_accepted():
        return True

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Prime Autoclicker — Please Read")
    box.setText("Welcome to Prime Autoclicker")
    box.setInformativeText(
        "This software automates mouse and keyboard input.\n\n"
        "• Use responsibly and only where permitted.\n"
        "• Automation may violate third-party Terms of Service.\n"
        "• Not affiliated with Mojang or any game publisher.\n"
        f"• {GAME_CREDIT}\n"
        "• The Phasmophobia plugin is unofficial, non-commercial fan content — not endorsed by Kinetic Games.\n"
        "• Route Recorder can capture keystrokes — do not record while typing passwords.\n\n"
        "You use this software at your own risk.\n\n"
        "Click Show Details for the full Phasmophobia fan content notice from Kinetic Games."
    )
    box.setDetailedText(ABOUT_PHASMO_DISCLAIMER)
    box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    box.setDefaultButton(QMessageBox.Ok)
    if box.exec_() != QMessageBox.Ok:
        return False
    mark_disclaimer_accepted()
    return True
