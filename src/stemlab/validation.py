"""Small boundary validators; JSON Schema files describe the same public format."""

import json
import math
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """A configuration violates a structural or scientific constraint."""


def fields(value: Any, expected: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ConfigurationError(f"{path}: expected exactly {sorted(expected)}")
    return value


def number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{path}: expected a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ConfigurationError(f"{path}: number exceeds floating-point range") from exc
    if not math.isfinite(result):
        raise ConfigurationError(f"{path}: expected a finite number")
    return result


def text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{path}: expected a nonempty string")
    return value


def version(value: Any, path: str) -> None:
    if type(value) is not int or value != 1:
        raise ConfigurationError(f"{path}: only schema version 1 is supported")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ConfigurationError(f"non-standard JSON numeric constant: {value}")


def read_json(path: str | Path) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"invalid JSON: {exc}") from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
