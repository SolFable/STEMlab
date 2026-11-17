"""Engine-independent physical model contracts with explicit scientific metadata."""

from dataclasses import asdict, dataclass
from typing import Any, Protocol

State = tuple[float, ...]


@dataclass(frozen=True)
class Quantity:
    name: str
    unit: str
    description: str


@dataclass(frozen=True)
class ModelDescription:
    id: str
    version: str
    state_variables: tuple[Quantity, ...]
    parameters: tuple[Quantity, ...]
    equations: tuple[str, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    environment_inputs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SimulationModel(Protocol):
    """Pure explicit ODE model in SI; adapters own time stepping.

    No GUI, engine handles, hidden randomness, or mutations in rhs().
    State ordering is exactly description.state_variables ordering.
    """

    @property
    def description(self) -> ModelDescription: ...

    @property
    def initial_state(self) -> State: ...

    def rhs(self, time_s: float, state: State) -> State: ...
