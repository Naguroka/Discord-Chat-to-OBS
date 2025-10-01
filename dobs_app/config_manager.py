from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from .constants import CONFIG_FILE_EXTENSIONS
from .io import read_text, write_text
from .paths import CONFIG_DIR, STATE_PATH
from .variables import VARIABLE_MAP, VARIABLES, Variable


class ConfigManager:
    def __init__(self, variables: List[Variable]):
        self.variables = variables
        CONFIG_DIR.mkdir(exist_ok=True)
        self.state = self._load_state()
        self.favorites: set[str] = set(self.state.get("favorites", []))
        self.current_name: str = self.state.get("last_config", "default")
        self.current_values: Dict[str, Any] = {}
        self.defaults: Dict[str, Any] = self._capture_defaults()
        self.raw_values: Dict[str, Any] = {}
        self._invalid_inputs: Dict[str, str] = {}
        self._dirty: bool = False
        self.load(self.current_name, apply_to_files=False)

    def _capture_defaults(self) -> Dict[str, Any]:
        defaults: Dict[str, Any] = {}
        for var in self.variables:
            try:
                value = var.getter()
            except Exception:
                value = None
            var.default = value
            defaults[var.key] = value
        return defaults

    def _load_state(self) -> Dict[str, Any]:
        if STATE_PATH.exists():
            try:
                return json.loads(read_text(STATE_PATH))
            except Exception:
                return {}
        return {}

    def _save_state(self) -> None:
        payload = {"last_config": self.current_name, "favorites": sorted(self.favorites)}
        write_text(STATE_PATH, json.dumps(payload, indent=2))

    def is_favorite(self, key: str) -> bool:
        return key in self.favorites

    def add_favorite(self, key: str) -> None:
        if key not in self.favorites:
            self.favorites.add(key)
            self._save_state()

    def remove_favorite(self, key: str) -> None:
        if key in self.favorites:
            self.favorites.remove(key)
            self._save_state()

    def toggle_favorite(self, key: str) -> None:
        if key in self.favorites:
            self.favorites.remove(key)
        else:
            self.favorites.add(key)
        self._save_state()

    def list_configs(self) -> List[str]:
        names: set[str] = set()
        for ext in CONFIG_FILE_EXTENSIONS:
            for path in CONFIG_DIR.glob(f"*{ext}"):
                if path.name == STATE_PATH.name:
                    continue
                names.add(path.stem)
        if "default" not in names:
            names.add("default")
        return sorted(names)

    def config_path(self, name: str):
        for ext in CONFIG_FILE_EXTENSIONS:
            candidate = CONFIG_DIR / f"{name}{ext}"
            if candidate.exists():
                return candidate
        return CONFIG_DIR / f"{name}.json"

    def load(self, name: str, apply_to_files: bool = True) -> Dict[str, Any]:
        path = self.config_path(name)
        if path.exists():
            try:
                payload = json.loads(read_text(path))
            except Exception:
                payload = {}
            values = payload.get("values", payload)
        else:
            values = {key: self.defaults.get(key) for key in VARIABLE_MAP}
            write_text(path, json.dumps({"values": values}, indent=2))

        new_raw: Dict[str, Any] = {}
        coerced: Dict[str, Any] = {}
        for key, var in VARIABLE_MAP.items():
            raw = values.get(key, self.defaults.get(key))
            new_raw[key] = raw
            try:
                coerced[key] = var.coerce(raw)
            except Exception:
                coerced[key] = var.default
        self.current_name = name
        self.raw_values = new_raw
        self.current_values = coerced
        self._invalid_inputs.clear()
        self._dirty = False
        self._save_state()
        if apply_to_files:
            self.apply_all()
        return coerced

    def save(self) -> None:
        write_text(self.config_path(self.current_name), json.dumps({"values": self.raw_values}, indent=2))
        self._save_state()

    def apply_all(self) -> None:
        for key, value in self.current_values.items():
            var = VARIABLE_MAP[key]
            try:
                var.setter(value if value is not None else var.default)
            except Exception as exc:
                print(f"Failed to apply {var.label}: {exc}")

    def has_invalid_inputs(self) -> bool:
        return bool(self._invalid_inputs)

    def pending_errors(self) -> list[str]:
        errors: list[str] = []
        for key, message in self._invalid_inputs.items():
            variable = VARIABLE_MAP.get(key)
            label = variable.label if variable else key
            errors.append(f"{label}: {message}")
        return errors

    def update_value(self, key: str, value: Any) -> None:
        variable = VARIABLE_MAP.get(key)
        if variable is None:
            raise KeyError(f"Unknown variable key: {key}")
        if self.set_raw_value(variable, value):
            self.save()
            self.apply_all()

    def apply_pending(self) -> None:
        if self._invalid_inputs:
            raise ValueError("\n".join(self.pending_errors()))
        self.save()
        self.apply_all()
        self._dirty = False

    def set_raw_value(self, variable: Variable, raw_value: Any) -> bool:
        try:
            parsed = variable.parse_value(raw_value)
        except Exception as exc:
            self._invalid_inputs[variable.key] = str(exc)
            return False
        else:
            self._invalid_inputs.pop(variable.key, None)
            self.raw_values[variable.key] = raw_value
            self.current_values[variable.key] = parsed
            self._dirty = True
            return True

    def get_invalid_message(self, variable: Variable) -> str | None:
        return self._invalid_inputs.get(variable.key)

    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False


