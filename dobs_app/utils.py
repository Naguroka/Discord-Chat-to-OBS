from __future__ import annotations

import re
from typing import Any


def normalize_tk_color(value: Any, fallback: str) -> str:
    if not value:
        return fallback
    if isinstance(value, tuple) and len(value) in {3, 4}:
        r, g, b = (int(float(v)) for v in value[:3])
        return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"
    color = str(value).strip()
    if not color:
        return fallback
    lowered = color.lower()
    if lowered in {"transparent", "none"}:
        return fallback
    if lowered.startswith('#'):
        hex_part = lowered[1:]
        if len(hex_part) in {3, 6} and all(ch in '0123456789abcdef' for ch in hex_part):
            if len(hex_part) == 3:
                hex_part = ''.join(ch * 2 for ch in hex_part)
            return f"#{hex_part}"
        return fallback
    rgba_match = re.match(r'rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)', lowered)
    if rgba_match:
        r, g, b = (int(float(rgba_match.group(i))) for i in range(1, 4))
        return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"
    named_colors = {
        'white': '#ffffff',
        'black': '#000000',
        'red': '#ff0000',
        'green': '#00ff00',
        'blue': '#0000ff',
        'transparent': fallback,
    }
    return named_colors.get(lowered, fallback)


def encode_js_string(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\\", "\\\\").replace("'", "\\'")
    return normalized.replace("\n", "\\n")


def decode_js_string(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).replace("\\r\\n", "\\n")
    normalized = normalized.replace("\\n", "\n")
    normalized = normalized.replace("\\'", "'")
    normalized = normalized.replace("\\\\", "\\")
    return normalized


def escape_js_basic(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\\", "\\\\").replace("'", "\\'")
