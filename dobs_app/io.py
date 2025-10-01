from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Iterable


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def read_lines(path: Path) -> list[str]:
    return read_text(path).splitlines()


def write_lines(path: Path, lines: Iterable[str]) -> None:
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    write_text(path, text)


def regex_get(path: Path, pattern: re.Pattern[str]) -> str:
    match = pattern.search(read_text(path))
    if not match:
        raise ValueError(f"Pattern not found in {path.name}.")
    return match.group("value")


def regex_update(path: Path, pattern: re.Pattern[str], replacer: Callable[[re.Match[str]], str]) -> None:
    text = read_text(path)
    new_text, count = pattern.subn(lambda m: replacer(m), text, count=1)
    if count == 0:
        raise ValueError(f"Pattern not found in {path.name}.")
    if new_text != text:
        write_text(path, new_text)
