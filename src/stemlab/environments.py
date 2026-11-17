"""Reusable ambient conditions, independent of any body, engine, or renderer."""

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from stemlab.validation import ConfigurationError, fields, number, text, version

# These describe uniform ambient profiles, not implemented environment simulators.
BUILTIN_PROPERTIES = {
    "land": {"friction_coefficient", "terrain_height_m"},
    "marine": {
        "fluid_density_kg_m3", "current_x_m_s", "current_y_m_s", "current_z_m_s",
    },
    "air": {
        "fluid_density_kg_m3", "temperature_K", "wind_x_m_s", "wind_y_m_s", "wind_z_m_s",
    },
}


@dataclass(frozen=True)
class EnvironmentConfig:
    id: str
    category: str
    gravity_m_s2: tuple[float, float, float]
    properties: Mapping[str, float]
    schema_version: int = 1

    def __post_init__(self) -> None:
        # Copy before freezing so callers cannot mutate a run through a shared dict.
        object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))

    @classmethod
    def from_dict(cls, raw: Any) -> "EnvironmentConfig":
        data = fields(raw, {"schema_version", "id", "category", "gravity_m_s2", "properties"}, "environment")
        version(data["schema_version"], "environment.schema_version")
        category = text(data["category"], "environment.category")
        if re.fullmatch(r"[a-z][a-z0-9_.-]*", category) is None:
            raise ConfigurationError("environment.category: use a lowercase category identifier")
        gravity = data["gravity_m_s2"]
        if not isinstance(gravity, list) or len(gravity) != 3:
            raise ConfigurationError("environment.gravity_m_s2: expected [gx, gy, gz]")
        props = data["properties"]
        if not isinstance(props, dict) or any(not isinstance(key, str) or not key for key in props):
            raise ConfigurationError("environment.properties: expected named numeric properties")
        if category in BUILTIN_PROPERTIES and set(props) != BUILTIN_PROPERTIES[category]:
            raise ConfigurationError(f"environment.properties: {category} requires exactly {sorted(BUILTIN_PROPERTIES[category])}")
        properties = {key: number(value, f"environment.properties.{key}") for key, value in props.items()}
        for key in ("fluid_density_kg_m3", "temperature_K"):
            if key in properties and properties[key] <= 0:
                raise ConfigurationError(f"environment.properties.{key}: must be positive")
        if properties.get("friction_coefficient", 0) < 0:
            raise ConfigurationError("environment.properties.friction_coefficient: must be nonnegative")
        return cls(
            id=text(data["id"], "environment.id"), category=category,
            gravity_m_s2=tuple(number(v, "environment.gravity_m_s2") for v in gravity),
            properties=properties,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "id": self.id, "category": self.category,
            "gravity_m_s2": list(self.gravity_m_s2), "properties": dict(self.properties),
        }
