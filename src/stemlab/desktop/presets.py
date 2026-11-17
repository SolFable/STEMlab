"""Editable desktop starting points, using the same validated core contracts."""

from stemlab.environments import EnvironmentConfig
from stemlab.experiments.config import ExperimentConfig, ModelConfig, SolverConfig


def environment_presets() -> dict[str, EnvironmentConfig]:
    properties = {
        "land": {"friction_coefficient": 0.6, "terrain_height_m": 0.0},
        "marine": {
            "fluid_density_kg_m3": 1025.0,
            "current_x_m_s": 0.2, "current_y_m_s": 0.0, "current_z_m_s": 0.0,
        },
        "air": {
            "fluid_density_kg_m3": 1.225, "temperature_K": 288.15,
            "wind_x_m_s": 1.0, "wind_y_m_s": 0.0, "wind_z_m_s": 0.0,
        },
    }
    return {
        category: EnvironmentConfig.from_dict({
            "schema_version": 1, "id": f"uniform-{category}-reference", "category": category,
            "gravity_m_s2": [0.0, 0.0, -9.80665], "properties": values,
        })
        for category, values in properties.items()
    }


def default_experiment() -> ExperimentConfig:
    return ExperimentConfig(
        id="eksperimen-pertama", environment=environment_presets()["land"],
        model=ModelConfig("z", 0.0, 100.0, 0.0), solver=SolverConfig(0.01, 200),
    )
