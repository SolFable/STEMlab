"""Composition root for the single supported Phase 0 experiment workflow."""

from stemlab.analysis import validate_constant_acceleration
from stemlab.engines.base import SimulationError
from stemlab.engines.rk4 import RK4Adapter
from stemlab.experiments.config import ExperimentConfig
from stemlab.experiments.results import ExperimentResult, implementation_sha256
from stemlab.models.constant_acceleration import ConstantAcceleration1D


def run_experiment(config: ExperimentConfig) -> ExperimentResult:
    # Enforce the serialized contract for callers constructing dataclasses directly.
    config = ExperimentConfig.from_dict(config.to_dict())
    model = ConstantAcceleration1D.create(
        axis=config.model.axis, applied_acceleration_m_s2=config.model.applied_acceleration_m_s2,
        position_m=config.model.position_m, velocity_m_s=config.model.velocity_m_s,
        environment=config.environment,
    )
    adapter = RK4Adapter()
    history = adapter.run(model, config.solver)
    report = validate_constant_acceleration(
        history, config.model.position_m, config.model.velocity_m_s, model.acceleration_m_s2,
    )
    if not report.passed:
        raise SimulationError("trajectory failed analytical validation at the declared tolerances")
    return ExperimentResult(
        config, model.description, model.acceleration_m_s2, history, report, implementation_sha256(),
    )
