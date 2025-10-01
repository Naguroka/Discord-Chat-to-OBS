from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
BACKGROUND_LIBRARY_DIR = ASSETS_DIR / "backgrounds"
CONFIG_DIR = BASE_DIR / "configs"
STATE_PATH = CONFIG_DIR / "dobs_state.json"
SETTINGS_PATH = BASE_DIR / "settings.ini"
