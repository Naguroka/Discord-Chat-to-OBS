from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .constants import CONFIG_FILE_EXTENSIONS
from .io import read_text, write_text, regex_get, regex_update
from .paths import CONFIG_DIR, SETTINGS_PATH
from .utils import decode_js_string, encode_js_string, escape_js_basic


@dataclass
class Variable:
    key: str
    label: str
    description: str
    category: str
    dtype: str
    getter: Callable[[], Any]
    setter: Callable[[Any], None]
    allow_empty: bool = True
    display_formatter: Optional[Callable[[Any], Any]] = None
    input_parser: Optional[Callable[[str], Any]] = None
    secure: bool = False
    default: Any = None
    process_escapes: bool = False

    TRUE_VALUES = {"1", "true", "yes", "on", "y", "t"}
    FALSE_VALUES = {"0", "false", "no", "off", "n", "f"}

    def _stringify(self, value: Any) -> str:
        return "" if value is None else str(value)

    def _as_bool(self, value: Any) -> bool:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in self.TRUE_VALUES:
                return True
            if lowered in self.FALSE_VALUES:
                return False
        return bool(value)

    def coerce(self, value: Any) -> Any:
        if value in (None, ""):
            if self.dtype == "bool":
                return False
            if self.dtype == "int":
                if self.allow_empty:
                    return None
                raise ValueError(f"{self.label} requires a value.")
            if self.dtype == "int_optional":
                return None
            if not self.allow_empty:
                raise ValueError(f"{self.label} cannot be blank.")
            return ""
        if self.dtype == "bool":
            return self._as_bool(value)
        if self.dtype == "int":
            text = self._stringify(value).strip()
            if not text:
                raise ValueError(f"{self.label} requires a value.")
            return int(text)
        if self.dtype == "int_optional":
            text = self._stringify(value).strip()
            return None if not text else int(text)
        return self._stringify(value)

    def parse_value(self, raw: Any) -> Any:
        if self.dtype == "bool":
            return self._as_bool(raw)
        if self.dtype == "int":
            text = self._stringify(raw).strip()
            if not text:
                raise ValueError(f"{self.label} requires a value.")
            return int(text)
        if self.dtype == "int_optional":
            text = self._stringify(raw).strip()
            return None if not text else int(text)
        text = self._stringify(raw)
        if not text.strip() and not self.allow_empty:
            raise ValueError(f"{self.label} cannot be blank.")
        if self.input_parser is not None:
            return self.input_parser(text)
        return text

    def to_display(self, value: Any) -> Any:
        if self.dtype == "bool":
            return self._as_bool(value)
        if value in (None, ""):
            return "" if self.dtype not in {"int", "int_optional"} else value
        result = value
        if self.display_formatter is not None:
            try:
                result = self.display_formatter(value)
            except Exception:
                result = value
        if self.dtype in {"int", "int_optional"}:
            return result
        return self._stringify(result)


def make_settings_variable(key: str, label: str, description: str, *, dtype: str = "str", placeholder: str | None = None, allow_empty: bool = False, secure: bool = False) -> Variable:
    def getter() -> str:
        pattern = re.compile(rf'^\s*{re.escape(key)}\s*=\s*(?P<value>.*)$', re.MULTILINE)
        try:
            value = regex_get(SETTINGS_PATH, pattern)
            return value.strip()
        except ValueError:
            return ""

    def setter(value: Any) -> None:
        text = read_text(SETTINGS_PATH)
        lines = text.splitlines()
        replaced = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                replaced = True
                new_lines.append(f"{key}={value}")
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"{key}={value}")
        write_text(SETTINGS_PATH, "\n".join(new_lines) + "\n")

    return Variable(
        key=key,
        label=label,
        description=description,
        category="settings.ini",
        dtype=dtype,
        getter=getter,
        setter=setter,
        allow_empty=allow_empty,
        default=placeholder,
        secure=secure,
    )


def make_regex_variable(spec: Dict[str, Any]) -> Variable:
    file_path = Path(spec["file"])
    pattern = re.compile(spec["pattern"], re.MULTILINE)
    process_escapes = spec.get("process_escapes", False)
    bool_literals = spec.get("bool_literals", ("true", "false"))
    dtype = spec.get("dtype", "str")

    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, str):
            lowered = value.strip().lower()
            return lowered == str(bool_literals[0]).lower()
        return bool(value)

    def getter() -> Any:
        try:
            value = regex_get(file_path, pattern)
        except ValueError:
            return ""
        if process_escapes:
            value = decode_js_string(value)
        if dtype == "bool":
            return _coerce_bool(value)
        if dtype == "int":
            try:
                return int(str(value).strip())
            except ValueError:
                return 0
        if dtype == "int_optional":
            text_value = str(value).strip()
            return None if not text_value else int(text_value)
        return value

    def setter(value: Any) -> None:
        if dtype == "bool":
            serialised = bool_literals[0] if _coerce_bool(value) else bool_literals[1]
        elif process_escapes:
            serialised = encode_js_string(value)
        else:
            serialised = str(value)

        def replacer(match: re.Match[str]) -> str:
            prefix = match.group("prefix")
            suffix = match.group("suffix")
            return f"{prefix}{serialised}{suffix}"

        regex_update(file_path, pattern, replacer)

    return Variable(
        key=spec["key"],
        label=spec["label"],
        description=spec["description"],
        category=spec["category"],
        dtype=spec.get("dtype", "str"),
        getter=getter,
        setter=setter,
        allow_empty=spec.get("allow_empty", True),
        display_formatter=spec.get("display_formatter"),
        input_parser=spec.get("input_parser"),
        secure=spec.get("secure", False),
        process_escapes=process_escapes,
    )


REGEX_VARIABLE_SPECS: List[Dict[str, Any]] = [
    {
        "key": "default_chat_host",
        "label": "Default Chat Host",
        "description": "Hostname or IP the local web server binds to.",
        "category": "Backend Defaults",
        "dtype": "str",
        "file": "discord_chat_to_obs/config.py",
        "pattern": r'(?P<prefix>DEFAULT_CHAT_HOST\s*=\s*")(?P<value>[^"]*)(?P<suffix>".*)',
    },
    {
        "key": "default_chat_port",
        "label": "Default Chat Port",
        "description": "Port the local web server exposes for OBS and embeds.",
        "category": "Backend Defaults",
        "dtype": "int",
        "file": "discord_chat_to_obs/config.py",
        "pattern": r'(?P<prefix>DEFAULT_CHAT_PORT\s*=\s*)(?P<value>\d+)(?P<suffix>.*)',
    },
    {
        "key": "default_history_size",
        "label": "Default History Size",
        "description": "Number of recent messages each feed retains.",
        "category": "Backend Defaults",
        "dtype": "int",
        "file": "discord_chat_to_obs/config.py",
        "pattern": r'(?P<prefix>DEFAULT_HISTORY_SIZE\s*=\s*)(?P<value>-?\d+)(?P<suffix>.*)',
    },
    {
        "key": "include_timestamps",
        "label": "Include Message Timestamps",
        "description": "Include Discord message timestamps in the payload sent to the frontend.",
        "category": "Backend Defaults",
        "dtype": "bool",
        "file": "discord_chat_to_obs/config.py",
        "pattern": r'(?P<prefix>INCLUDE_MESSAGE_TIMESTAMPS\s*=\s*)(?P<value>True|False)(?P<suffix>.*)',
        "bool_literals": ("True", "False"),
    },
    {
        "key": "show_message_timestamps",
        "label": "Show Message Timestamps",
        "description": "Display (hh:mm) timestamps after each username.",
        "category": "Overlay Script",
        "dtype": "bool",
        "file": "web/scripts/config.js",
        "pattern": r'(?P<prefix>export const SHOW_MESSAGE_TIMESTAMPS\s*=\s*)(?P<value>true|false)(?P<suffix>;.*)',
        "bool_literals": ("true", "false"),
    },
        # === Overlay toggles ===
    {
        "key": "show_avatars",
        "label": "Show Avatars",
        "description": "Display profile pictures next to messages.",
        "category": "Overlay Script",
        "dtype": "bool",
        "file": "web/scripts/config.js",
        "pattern": r'(?P<prefix>export const SHOW_AVATARS\s*=\s*)(?P<value>true|false)(?P<suffix>;.*)',
        "bool_literals": ("true", "false"),
    },
    {
        "key": "apply_role_colors",
        "label": "Apply Role Colors",
        "description": "Tint author text using the sender’s Discord role color.",
        "category": "Overlay Script",
        "dtype": "bool",
        "file": "web/scripts/config.js",
        "pattern": r'(?P<prefix>export const APPLY_ROLE_COLORS\s*=\s*)(?P<value>true|false)(?P<suffix>;.*)',
        "bool_literals": ("true", "false"),
    },
    # === Styling knobs ===
    {
        "key": "css_avatar_size",
        "label": "Avatar Size",
        "description": "Avatar square size (e.g., 40px or 2.5rem).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--avatar-size:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_avatar_width",
        "label": "Avatar Width (override)",
        "description": "Optional explicit avatar width (e.g., 48px).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--avatar-width:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_avatar_height",
        "label": "Avatar Height (override)",
        "description": "Optional explicit avatar height (e.g., 48px).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--avatar-height:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_emoji_size",
        "label": "Emoji Size",
        "description": "Custom emoji width/height (e.g., 1.6em or 24px).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--emoji-size:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "chat_poll_interval",
        "label": "Chat Poll Interval (ms)",
        "description": "Interval in milliseconds for refreshing chat messages.",
        "category": "Overlay Script",
        "dtype": "int",
        "file": "web/scripts/config.js",
        "pattern": r'(?P<prefix>export const CHAT_POLL_INTERVAL_MS\s*=\s*)(?P<value>\d+)(?P<suffix>;.*)',
    },
    {
        "key": "fallback_api_origin",
        "label": "Fallback API Origin",
        "description": "Default API origin when the page is opened locally.",
        "category": "Overlay Script",
        "dtype": "str",
        "file": "web/scripts/config.js",
        "pattern": r"(?P<prefix>export const FALLBACK_API_ORIGIN\s*=\s*`)(?P<value>[^`]*)(?P<suffix>`;.*)",
    },
    {
        "key": "show_embed_scrollbar",
        "label": "Show Embed Scrollbar",
        "description": "Display scrollbars in embed mode when enabled.",
        "category": "Overlay Script",
        "dtype": "bool",
        "file": "web/scripts/config.js",
        "pattern": r'(?P<prefix>export const SHOW_EMBED_SCROLLBAR\s*=\s*)(?P<value>true|false)(?P<suffix>;.*)',
        "bool_literals": ("true", "false"),
    },
    {
        "key": "background_media_url",
        "label": "Background Media URL",
        "description": "Optional image / GIF / video URL used behind the chat.",
        "category": "Overlay Script",
        "dtype": "str",
        "file": "web/scripts/config.js",
        "pattern": r"(?P<prefix>export const BACKGROUND_MEDIA_URL\s*=\s*')(?P<value>(?:\\'|[^'])*)(?P<suffix>';.*)",
        "process_escapes": True,
        "strip": False,
        "allow_empty": True,
    },
    {
        "key": "message_layout_template",
        "label": "Message Layout Template",
        "description": "Template for rendering username, timestamp, and message. Supports HTML and placeholders.",
        "category": "Overlay Script",
        "dtype": "str",
        "file": "web/scripts/config.js",
        "pattern": r"(?P<prefix>export const MESSAGE_LAYOUT_TEMPLATE\s*=\s*')(?P<value>(?:\\'|[^'])*)(?P<suffix>';.*)",
        "process_escapes": True,
        "strip": False,
    },
    {
        "key": "timestamp_template",
        "label": "Timestamp Template",
        "description": "Template surrounding the formatted time. Use {{time}} as placeholder.",
        "category": "Overlay Script",
        "dtype": "str",
        "file": "web/scripts/config.js",
        "pattern": r"(?P<prefix>export const TIMESTAMP_TEMPLATE\s*=\s*')(?P<value>(?:\\'|[^'])*)(?P<suffix>';.*)",
        "process_escapes": True,
        "strip": False,
    },
    {
        "key": "message_hide_username_template",
        "label": "Message Layout (No Username)",
        "description": "Template used when usernames are hidden. Supports HTML and placeholders.",
        "category": "Overlay Script",
        "dtype": "str",
        "file": "web/scripts/config.js",
        "pattern": r"(?P<prefix>export const MESSAGE_HIDE_USERNAME_TEMPLATE\s*=\s*')(?P<value>(?:\\'|[^'])*)(?P<suffix>';.*)",
        "process_escapes": True,
        "strip": False,
    },
    {
        "key": "css_font_family",
        "label": "Font Family",
        "description": "Primary font family for chat text.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--chat-font-family:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_chat_background",
        "label": "Chat Background",
        "description": "Page background color for the overlay.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--chat-background:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_message_background",
        "label": "Message Background",
        "description": "Bubble background color for each message.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--message-background:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_message_color",
        "label": "Message Text Color",
        "description": "Default message text color.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--message-color:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_bubble_padding",
        "label": "Bubble Padding (All Sides)",
        "description": "Inner spacing inside each message bubble (e.g., 10px, 0.8rem).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--bubble-padding:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_message_line_height",
        "label": "Line Spacing (Line-Height)",
        "description": "Space between lines inside messages (e.g., 1.2, 1.35, 120%, 18px).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--message-line-height:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_username_color",
        "label": "Username Color (Fallback)",
        "description": "Fallback color when usernames lack a role color.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--username-color-default:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_author_color",
        "label": "Author Color",
        "description": "Color used by {{author}} when the template uses var(--author-color).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--author-color:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_timestamp_color",
        "label": "Timestamp Color",
        "description": "Color used for the time text.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--timestamp-color:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    # Wrapping and bounds
    {
        "key": "css_message_white_space",
        "label": "Message Wrap Mode",
        "description": "CSS white-space for messages (normal, nowrap, pre, pre-wrap).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--message-white-space:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_message_max_width",
        "label": "Message Max Width",
        "description": "Max width for a single message bubble (e.g., 420px).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--message-max-width:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_message_min_width",
        "label": "Message Min Width",
        "description": "Min width for a single message bubble.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--message-min-width:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    {
        "key": "css_message_line_gap",
        "label": "Header/Body Gap",
        "description": "Space between header line and message line (e.g., 0, 2px, 0.2em).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--message-line-gap:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
    # Transparency sliders (0–100 → 1–0 alpha)
    # Helper is inlined via 'input_parser' below.
]

# Percent (0–100, where 0 = opaque, 100 = fully transparent) → CSS alpha (1–0)
def _percent_to_alpha(text: str) -> str:
    import re
    s = re.sub(r'[^0-9.]+', '', str(text))
    try:
        p = float(s)
    except Exception:
        p = 0.0
    p = max(0.0, min(100.0, p))
    alpha = 1.0 - (p / 100.0)
    out = f"{alpha:.3f}".rstrip('0').rstrip('.')
    return out or "0"

REGEX_VARIABLE_SPECS += [
    {
        "key": "css_message_background_transparency",
        "label": "Message Background Transparency (%)",
        "description": "0 = opaque, 100 = fully transparent.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--message-background-opacity:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
        "input_parser": _percent_to_alpha,
    },
    {
        "key": "css_background_media_transparency",
        "label": "Background Media Transparency (%)",
        "description": "0 = opaque, 100 = fully transparent.",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--background-media-opacity:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
        "input_parser": _percent_to_alpha,
    },
    {
        "key": "css_background_media_opacity",
        "label": "Background Media Opacity",
        "description": "Opacity for background image/video layer (0–1).",
        "category": "Overlay Styling",
        "dtype": "str",
        "file": "web/styles.css",
        "pattern": r'(?P<prefix>\s*--background-media-opacity:\s*)(?P<value>[^;]+)(?P<suffix>;.*)',
    },
]


SETTINGS_VARIABLES: List[Variable] = [
    make_settings_variable(
        "DISCORD_BOT_TOKEN",
        "Discord Bot Token",
        "Bot token used to authenticate with Discord.",
        secure=True,
    ),
    make_settings_variable(
        "DISCORD_CHANNEL_ID_OBS",
        "OBS Channel ID",
        "Discord channel ID whose messages should appear in OBS.",
    ),
    make_settings_variable(
        "DISCORD_CHANNEL_ID_EMBED",
        "Embed Channel ID",
        "Discord channel ID used for the embeddable chat feed.",
        allow_empty=True,
    ),
    make_settings_variable(
        "CHAT_API_HOST",
        "Custom API Host",
        "Override the web server host (leave blank for default).",
        placeholder="127.0.0.1",
        allow_empty=True,
    ),
    make_settings_variable(
        "CHAT_API_PORT",
        "Custom API Port",
        "Override the web server port (leave blank for default).",
        placeholder="8080",
        dtype="int_optional",
        allow_empty=True,
    ),
    make_settings_variable(
        "CHAT_HISTORY_SIZE",
        "Custom History Size",
        "Override how many recent messages stay buffered (leave blank for default).",
        placeholder="200",
        dtype="int_optional",
        allow_empty=True,
    ),
    make_settings_variable(
        "DISCORD_CHANNEL_ID",
        "Legacy Channel ID",
        "Optional legacy channel ID when both feeds mirror the same channel.",
        allow_empty=True,
    ),
]

VARIABLES: List[Variable] = SETTINGS_VARIABLES + [make_regex_variable(spec) for spec in REGEX_VARIABLE_SPECS]
VARIABLE_MAP: Dict[str, Variable] = {var.key: var for var in VARIABLES}





