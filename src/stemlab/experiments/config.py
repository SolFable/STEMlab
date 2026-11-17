"""Strict version-1 experiment input. No executable code in configuration."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stemlab.environments import EnvironmentConfig
from stemlab.validation import ConfigurationError, fields, number, read_json, text, version

MAX_STEPS = 100_000


@dataclass(frozen=True)
class ModelConfig:
    axis: str
    applied_acceleration_m_s2: float
    position_m: float
    velocity_m_s: float
    id: str = "constant_acceleration_1d"
    version: str = "1"

    @classmethod
    def from_dict(cls, raw: Any) -> "ModelConfig":
        data = fields(raw, {"id", "version", "axis", "parameters", "initial_state"}, "model")
        if data["id"] != "constant_acceleration_1d" or data["version"] != "1":
            raise ConfigurationError("model: unsupported id or version")
        if data["axis"] not in ("x", "y", "z"):
            raise ConfigurationError("model.axis: expected x, y, or z")
        params = fields(data["parameters"], {"applied_acceleration_m_s2"}, "model.parameters")
        initial = fields(data["initial_state"], {"position_m", "velocity_m_s"}, "model.initial_state")
        return cls(
            data["axis"], number(params["applied_acceleration_m_s2"], "applied_acceleration_m_s2"),
            number(initial["position_m"], "position_m"), number(initial["velocity_m_s"], "velocity_m_s"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "version": self.version, "axis": self.axis,
            "parameters": {"applied_acceleration_m_s2": self.applied_acceleration_m_s2},
            "initial_state": {"position_m": self.position_m, "velocity_m_s": self.velocity_m_s},
        }


@dataclass(frozen=True)
class SolverConfig:
    dt_s: float
    steps: int
    id: str = "python_rk4"
    version: str = "1"

    @classmethod
    def from_dict(cls, raw: Any) -> "SolverConfig":
        data = fields(raw, {"id", "version", "dt_s", "steps"}, "solver")
        if data["id"] != "python_rk4" or data["version"] != "1":
            raise ConfigurationError("solver: unsupported id or version")
        dt = number(data["dt_s"], "solver.dt_s")
        steps = data["steps"]
        if dt <= 0 or dt / 2 == 0:
            raise ConfigurationError("solver.dt_s: must be positive and support half steps")
        if type(steps) is not int or not 1 <= steps <= MAX_STEPS:
            raise ConfigurationError(f"solver.steps: expected an integer in [1, {MAX_STEPS}]")
        if not math.isfinite(dt * steps):
            raise ConfigurationError("solver: final time exceeds floating-point range")
        return cls(dt, steps)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "version": self.version, "dt_s": self.dt_s, "steps": self.steps}


@dataclass(frozen=True)
class ExperimentConfig:
    id: str
    environment: EnvironmentConfig
    model: ModelConfig
    solver: SolverConfig
    schema_version: int = 1

    @classmethod
    def from_dict(cls, raw: Any) -> "ExperimentConfig":
        data = fields(raw, {"schema_version", "id", "environment", "model", "solver"}, "experiment")
        version(data["schema_version"], "experiment.schema_version")
        return cls(
            text(data["id"], "experiment.id"), EnvironmentConfig.from_dict(data["environment"]),
            ModelConfig.from_dict(data["model"]), SolverConfig.from_dict(data["solver"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "id": self.id,
            "environment": self.environment.to_dict(), "model": self.model.to_dict(),
            "solver": self.solver.to_dict(),
        }


def load_experiment(path: str | Path) -> ExperimentConfig:
    return ExperimentConfig.from_dict(read_json(path))
