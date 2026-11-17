"""Self-contained results with normalized inputs and implementation fingerprints."""

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stemlab import __version__
from stemlab.analysis import ValidationReport
from stemlab.engines.base import Sample
from stemlab.experiments.config import ExperimentConfig
from stemlab.modeling import ModelDescription
from stemlab.validation import canonical_json


def configuration_sha256(config: ExperimentConfig) -> str:
    return hashlib.sha256(canonical_json(config.to_dict()).encode("utf-8")).hexdigest()


def implementation_sha256() -> str:
    """Fingerprint installed Python source and schemas, including local edits.

    Paths are package-relative; checkout location does not affect the hash.
    The normal setuptools unpacked installation is the supported layout.
    """
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.suffix in (".py", ".json"):
            digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


@dataclass(frozen=True)
class ExperimentResult:
    config: ExperimentConfig
    model_description: ModelDescription
    effective_acceleration_m_s2: float
    history: tuple[Sample, ...]
    validation: ValidationReport
    source_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "configuration": self.config.to_dict(),
            "provenance": {
                "stemlab_version": __version__, "implementation_sha256": self.source_sha256,
                "configuration_sha256": configuration_sha256(self.config),
                "python_version": sys.version, "python_implementation": platform.python_implementation(),
                "platform": platform.platform(), "runtime_dependencies": [],
                "floating_point": "IEEE-754 binary64 (Python float)",
                "randomness": "none", "time_grid": "t_i = i * dt_s, i = 0..steps",
                "engine_id": self.config.solver.id, "engine_version": self.config.solver.version,
            },
            "model_description": self.model_description.to_dict(),
            "resolved_model": {"effective_acceleration_m_s2": self.effective_acceleration_m_s2},
            "history": [{"time_s": sample.time_s, "state": list(sample.state)} for sample in self.history],
            "validation": self.validation.to_dict(),
        }


def save_result(result: ExperimentResult, path: str | Path) -> None:
    """Save strict JSON; refuse overwrites. Filesystem writes are not crash-atomic."""
    contents = json.dumps(result.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(contents)
