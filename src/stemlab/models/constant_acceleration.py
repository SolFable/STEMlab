"""One-dimensional motion under uniform, constant acceleration."""

from dataclasses import dataclass

from stemlab.environments import EnvironmentConfig
from stemlab.modeling import ModelDescription, Quantity, State
from stemlab.validation import number


@dataclass(frozen=True)
class ConstantAcceleration1D:
    initial_state: State
    acceleration_m_s2: float

    @classmethod
    def create(
        cls, *, axis: str, applied_acceleration_m_s2: float, position_m: float,
        velocity_m_s: float, environment: EnvironmentConfig,
    ) -> "ConstantAcceleration1D":
        index = ("x", "y", "z").index(axis)
        acceleration = number(
            environment.gravity_m_s2[index] + applied_acceleration_m_s2,
            "effective acceleration",
        )
        return cls((position_m, velocity_m_s), acceleration)

    @property
    def description(self) -> ModelDescription:
        return ModelDescription(
            id="constant_acceleration_1d", version="1",
            state_variables=(
                Quantity("position_m", "m", "Position along the configured world axis"),
                Quantity("velocity_m_s", "m/s", "Velocity along the same axis"),
            ),
            parameters=(Quantity("applied_acceleration_m_s2", "m/s^2", "Prescribed non-gravitational acceleration"),),
            equations=("dq/dt = v", "dv/dt = a", "a = gravity[axis] + applied_acceleration"),
            assumptions=("Uniform constant gravity", "Constant prescribed applied acceleration", "Point particle in an inertial frame"),
            limitations=(
                "No contact, terrain collision, friction, drag, buoyancy, wind, or currents",
                "Ambient category properties are recorded but not used; this is not a land, marine, or air dynamics model",
                "No rotation, mass evolution, relativistic effects, or force-based actuation",
            ),
            environment_inputs=("gravity_m_s2[axis]",),
        )

    def rhs(self, time_s: float, state: State) -> State:
        return (state[1], self.acceleration_m_s2)
