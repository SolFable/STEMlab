"""Classical four-stage, fixed-step Runge-Kutta, implemented in Python."""

import math

from stemlab.engines.base import Sample, SimulationError
from stemlab.experiments.config import SolverConfig
from stemlab.modeling import SimulationModel, State


class RK4Adapter:
    id = "python_rk4"
    version = "1"

    def run(self, model: SimulationModel, solver: SolverConfig) -> tuple[Sample, ...]:
        # Validate direct API input as well as loaded JSON.
        solver = SolverConfig.from_dict(solver.to_dict())
        size = len(model.description.state_variables)

        def checked(values: State) -> State:
            if size == 0 or len(values) != size or any(
                isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)
                for v in values
            ):
                raise SimulationError("model returned a nonfinite or incorrectly sized state/derivative")
            return tuple(values)

        def stage(state: State, derivative: State, scale: float) -> State:
            return checked(tuple(y + scale * dy for y, dy in zip(state, derivative, strict=True)))

        state = checked(model.initial_state)
        samples = [Sample(0.0, state)]
        for index in range(solver.steps):
            start = index * solver.dt_s
            end = (index + 1) * solver.dt_s
            step = end - start
            if step <= 0:
                raise SimulationError("time grid is not strictly increasing")
            middle = start + step / 2
            k1 = checked(model.rhs(start, state))
            k2 = checked(model.rhs(middle, stage(state, k1, step / 2)))
            k3 = checked(model.rhs(middle, stage(state, k2, step / 2)))
            k4 = checked(model.rhs(end, stage(state, k3, step)))
            state = checked(tuple(
                y + step * (a / 6 + b / 3 + c / 3 + d / 6)
                for y, a, b, c, d in zip(state, k1, k2, k3, k4, strict=True)
            ))
            samples.append(Sample(end, state))
        return tuple(samples)
