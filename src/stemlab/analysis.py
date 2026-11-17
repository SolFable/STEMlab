"""Analytical reference and validation for the Phase 0 proof experiment."""

import math
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from stemlab.engines.base import Sample


def analytical_state(
    time_s: float, position_m: float, velocity_m_s: float, acceleration_m_s2: float,
) -> tuple[float, float]:
    """Exact constant-acceleration state from t=0, in SI units."""
    return (
        position_m + velocity_m_s * time_s + 0.5 * acceleration_m_s2 * time_s * time_s,
        velocity_m_s + acceleration_m_s2 * time_s,
    )


@dataclass(frozen=True)
class ValidationReport:
    reference: str
    absolute_tolerance: float
    relative_tolerance: float
    max_position_error_m: float
    max_velocity_error_m_s: float
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_constant_acceleration(
    samples: Sequence[Sample], position_m: float, velocity_m_s: float,
    acceleration_m_s2: float, *, atol: float = 1e-10, rtol: float = 1e-12,
) -> ValidationReport:
    """Compare every recorded state to the exact solution from t=0.

    atol applies in the declared SI unit of each variable; these tolerances
    are for this smooth proof problem, not a universal scientific criterion.
    """
    if not samples or any(not math.isfinite(v) or v < 0 for v in (atol, rtol)):
        raise ValueError("validation needs samples and finite nonnegative tolerances")
    position_errors: list[float] = []
    velocity_errors: list[float] = []
    passed = True
    for sample in samples:
        t = sample.time_s
        expected_position, expected_velocity = analytical_state(t, position_m, velocity_m_s, acceleration_m_s2)
        actual_position, actual_velocity = sample.state
        values = (t, actual_position, actual_velocity, expected_position, expected_velocity)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("analytical comparison contains nonfinite values")
        position_errors.append(abs(actual_position - expected_position))
        velocity_errors.append(abs(actual_velocity - expected_velocity))
        passed &= math.isclose(actual_position, expected_position, abs_tol=atol, rel_tol=rtol)
        passed &= math.isclose(actual_velocity, expected_velocity, abs_tol=atol, rel_tol=rtol)
    return ValidationReport(
        "q(t)=q0+v0*t+0.5*a*t^2; v(t)=v0+a*t", atol, rtol,
        max(position_errors), max(velocity_errors), passed,
    )
