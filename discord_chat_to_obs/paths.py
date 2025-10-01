from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "web"
ASSETS_DIR = ROOT_DIR / "assets"
SETTINGS_PATH = ROOT_DIR / "settings.ini"


def ensure_static_dir() -> Path:
    """Return the directory that holds static web assets."""
    return STATIC_DIR if STATIC_DIR.exists() else ROOT_DIR
