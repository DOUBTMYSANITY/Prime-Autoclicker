"""Kinetic Games fan content disclaimer — single source of truth for in-app UI."""

from __future__ import annotations

import json
from pathlib import Path

FAN_CONTENT_POLICY_URL = "https://www.kineticgames.co.uk/fan-creation-policy"
KINETIC_GAMES_URL = "https://www.kineticgames.co.uk/"

GAME_CREDIT = "Phasmophobia is a game by Kinetic Games."

SHORT_DISCLAIMER = (
    "Unofficial, non-commercial fan reference. Not affiliated with, endorsed by, or sponsored by Kinetic Games."
)

# Verbatim text from Kinetic Games Support (fan creation correspondence).
KINETIC_GAMES_LEGAL_DISCLAIMER = (
    "This third-party material, product or tool is an independent, non-commercial, not-for-profit "
    "project and is not affiliated with, endorsed by or sponsored by Kinetic Games.\n"
    "Any use of Kinetic Games' trademarks, logos, copyrighted materials or the 'Phasmophobia' brand "
    "is for descriptive and/or informational purposes only.\n"
    "Such use has not been authorised by Kinetic Games and does not constitute a licence, consent or "
    "waiver of Kinetic Games' rights, all of which are expressly reserved.\n"
    "Kinetic Games has not reviewed, assessed or approved this project and makes no representations "
    "or warranties as to its accuracy, quality, functionality, or fitness for purpose.\n"
    "The third-party material, product and/or tool comprised in this project is provided \"as is\". "
    "Use is at the end user's own risk and Kinetic Games shall have no liability arising out of or "
    "in connection with any person's reliance on, or use of, such project, material, product or tool."
)

ABOUT_PHASMO_DISCLAIMER = (
    f"{GAME_CREDIT}\n\n"
    "The optional Phasmophobia reference plugin is fan-created content shared under Kinetic Games' "
    f"Fan Creation Policy ({FAN_CONTENT_POLICY_URL}).\n\n"
    f"{KINETIC_GAMES_LEGAL_DISCLAIMER}"
)


def show_fan_content_disclaimer(parent=None) -> None:
    """Show the full Kinetic Games fan content notice in a dialog."""
    from PyQt5.QtWidgets import QMessageBox

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle("Phasmophobia Fan Content Notice")
    box.setText(GAME_CREDIT)
    box.setInformativeText(
        "This plugin is unofficial fan-created content shared under Kinetic Games' Fan Creation Policy."
    )
    box.setDetailedText(KINETIC_GAMES_LEGAL_DISCLAIMER)
    box.setStandardButtons(QMessageBox.Ok)
    box.exec_()


_PHASMO_NOTICE_VERSION = 1
_PHASMO_NOTICE_FILE = Path.home() / ".mtautoclicker_phasmo_notice.json"


def _phasmo_notice_acknowledged() -> bool:
    try:
        if not _PHASMO_NOTICE_FILE.is_file():
            return False
        data = json.loads(_PHASMO_NOTICE_FILE.read_text(encoding="utf-8"))
        return int(data.get("notice_version", 0)) >= _PHASMO_NOTICE_VERSION
    except Exception:
        return False


def _mark_phasmo_notice_acknowledged() -> None:
    _PHASMO_NOTICE_FILE.write_text(
        json.dumps({"notice_version": _PHASMO_NOTICE_VERSION, "accepted": True}, indent=2),
        encoding="utf-8",
    )


def show_phasmo_notice_if_needed(parent=None) -> bool:
    """Show fan content notice before using the Phasmo reference UI. Returns False if dismissed."""
    from PyQt5.QtWidgets import QMessageBox

    if _phasmo_notice_acknowledged():
        return True

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle("Unofficial Phasmophobia Reference")
    box.setText(GAME_CREDIT)
    box.setInformativeText(
        "This is unofficial, non-commercial fan-created content shared under Kinetic Games' "
        "Fan Creation Policy.\n\nClick Show Details for the full notice from Kinetic Games."
    )
    box.setDetailedText(ABOUT_PHASMO_DISCLAIMER)
    box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    box.setDefaultButton(QMessageBox.Ok)
    if box.exec_() != QMessageBox.Ok:
        return False
    _mark_phasmo_notice_acknowledged()
    return True
