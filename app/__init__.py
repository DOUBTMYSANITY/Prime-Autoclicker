"""AutoclickerAdvanced application package."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN_DIR = PROJECT_ROOT / "Main"


def setup_paths() -> Path:
    """Ensure project root and Main/ are importable. Returns PROJECT_ROOT."""
    for path in (PROJECT_ROOT, MAIN_DIR):
        entry = str(path)
        if entry not in sys.path:
            sys.path.insert(0, entry)
    return PROJECT_ROOT
