from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping

from .paths import SETTINGS_PATH

DEFAULT_CHAT_HOST = "127.0.0.1"
DEFAULT_CHAT_PORT = 8080
DEFAULT_HISTORY_SIZE = 200
INCLUDE_MESSAGE_TIMESTAMPS = True


@dataclass(frozen=True)
class Settings:
    token: str
    obs_channel_id: int
    embed_channel_id: int
    host: str = DEFAULT_CHAT_HOST
    port: int = DEFAULT_CHAT_PORT
    history_size: int = DEFAULT_HISTORY_SIZE


def load_settings_file(path: Path = SETTINGS_PATH) -> Dict[str, str]:
    """Read key=value pairs from a .ini style file into a dictionary."""
    if not path.exists():
        raise RuntimeError(
            "settings.ini is missing. Copy settings.ini.example, fill it in, and rerun the bot."
        )

    result: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def get_setting(store: Mapping[str, str], key: str, *, default: str | None = None) -> str | None:
    """Fetch a configuration value, falling back to environment variables."""
    value = store.get(key)
    if value:
        return value

    from os import getenv

    env_value = getenv(key)
    if env_value:
        return env_value
    return default


def require_setting(store: Mapping[str, str], key: str) -> str:
    """Return a mandatory config value or raise a friendly error."""
    value = get_setting(store, key)
    if not value:
        raise RuntimeError(
            f"Configuration value '{key}' is required. See README for setup details."
        )
    return value


def parse_int(value: str, key: str, *, minimum: int | None = None) -> int:
    """Convert config strings to ints and enforce optional minimums."""
    try:
        parsed = int(value)
    except ValueError as err:
        raise RuntimeError(f"Configuration value '{key}' must be an integer.") from err

    if minimum is not None and parsed < minimum:
        raise RuntimeError(f"Configuration value '{key}' must be >= {minimum}.")
    return parsed


def load_settings(path: Path = SETTINGS_PATH) -> Settings:
    store = load_settings_file(path)

    token = require_setting(store, "DISCORD_BOT_TOKEN")

    legacy_channel_raw = get_setting(store, "DISCORD_CHANNEL_ID")

    obs_channel_raw = get_setting(store, "DISCORD_CHANNEL_ID_OBS") or legacy_channel_raw
    if not obs_channel_raw:
        raise RuntimeError("Configuration value 'DISCORD_CHANNEL_ID_OBS' is required. See README for setup details.")
    obs_channel_id = parse_int(obs_channel_raw, "DISCORD_CHANNEL_ID_OBS", minimum=1)

    embed_channel_raw = get_setting(store, "DISCORD_CHANNEL_ID_EMBED")
    if embed_channel_raw:
        embed_channel_id = parse_int(embed_channel_raw, "DISCORD_CHANNEL_ID_EMBED", minimum=1)
    elif legacy_channel_raw:
        embed_channel_id = parse_int(legacy_channel_raw, "DISCORD_CHANNEL_ID_EMBED", minimum=1)
    else:
        embed_channel_id = obs_channel_id

    host = get_setting(store, "CHAT_API_HOST", default=DEFAULT_CHAT_HOST) or DEFAULT_CHAT_HOST
    port_raw = get_setting(store, "CHAT_API_PORT", default=str(DEFAULT_CHAT_PORT)) or str(DEFAULT_CHAT_PORT)
    port = parse_int(port_raw, "CHAT_API_PORT", minimum=1)

    history_raw = get_setting(store, "CHAT_HISTORY_SIZE", default=str(DEFAULT_HISTORY_SIZE)) or str(DEFAULT_HISTORY_SIZE)
    history_size = parse_int(history_raw, "CHAT_HISTORY_SIZE", minimum=1)

    return Settings(
        token=token,
        obs_channel_id=obs_channel_id,
        embed_channel_id=embed_channel_id,
        host=host,
        port=port,
        history_size=history_size,
    )
