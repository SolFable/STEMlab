"""The minimal engine contract for explicit ODE experiments."""

from dataclasses import dataclass
from typing import Protocol

from stemlab.experiments.config import SolverConfig
from stemlab.modeling import SimulationModel, State


class SimulationError(ValueError):
    """A numerical result is invalid; a partial history is not a successful run."""


@dataclass(frozen=True)
class Sample:
    time_s: float
    state: State


class SimulationAdapter(Protocol):
    id: str
    version: str

    def run(self, model: SimulationModel, solver: SolverConfig) -> tuple[Sample, ...]: ...
