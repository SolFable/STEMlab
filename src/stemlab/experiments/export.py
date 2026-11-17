"""Portable tabular export of a completed, immutable experiment."""

import csv
from pathlib import Path

from stemlab.analysis import analytical_state
from stemlab.experiments.results import ExperimentResult


def save_history_csv(result: ExperimentResult, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow((
            "time_s", "position_m", "velocity_m_s", "analytical_position_m",
            "analytical_velocity_m_s", "position_error_m", "velocity_error_m_s",
        ))
        for sample in result.history:
            q, v = analytical_state(
                sample.time_s, result.config.model.position_m, result.config.model.velocity_m_s,
                result.effective_acceleration_m_s2,
            )
            writer.writerow((
                sample.time_s, *sample.state, q, v,
                abs(sample.state[0] - q), abs(sample.state[1] - v),
            ))
