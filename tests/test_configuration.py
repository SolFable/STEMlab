import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from stemlab.environments import EnvironmentConfig
from stemlab.experiments.config import ExperimentConfig, load_experiment
from stemlab.validation import ConfigurationError, read_json

ROOT = Path(__file__).resolve().parents[1]


def example() -> dict:
    return json.loads((ROOT / "examples/constant_acceleration.json").read_text())


def invalid_examples():
    cases = [
        (("schema_version",), 2), (("schema_version",), True),
        (("model", "id"), "unknown"), (("model", "version"), "2"),
        (("model", "axis"), "north"), (("model", "parameters", "applied_acceleration_m_s2"), True),
        (("model", "initial_state", "position_m"), "100 m"),
        (("solver", "id"), "unknown"), (("solver", "version"), "2"),
        (("solver", "dt_s"), 0), (("solver", "dt_s"), -1),
        (("solver", "steps"), True), (("solver", "steps"), 1.5),
        (("solver", "steps"), 0), (("solver", "steps"), 100001),
        (("environment", "gravity_m_s2"), [0, -9.8]),
        (("environment", "properties", "friction_coefficient"), -0.1),
        (("environment", "category"), "LAND"), (("id",), "   "),
    ]
    for path, value in cases:
        data = example()
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        yield path, data
    data = example()
    data["unexpected"] = 123
    yield ("unexpected",), data
    data = example()
    del data["environment"]["properties"]["terrain_height_m"]
    yield ("missing property",), data


class ConfigurationTests(unittest.TestCase):
    def test_example_round_trip(self):
        config = load_experiment(ROOT / "examples/constant_acceleration.json")
        self.assertEqual(ExperimentConfig.from_dict(config.to_dict()), config)
        self.assertEqual(config.to_dict(), example())

    def test_invalid_structures_and_values(self):
        for name, data in invalid_examples():
            with self.subTest(name=name), self.assertRaises(ConfigurationError):
                ExperimentConfig.from_dict(data)

    def test_nonfinite_and_unrepresentable_numbers(self):
        for value in (math.inf, -math.inf, math.nan, 10 ** 1000):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ConfigurationError):
                data = example()
                data["model"]["initial_state"]["position_m"] = value
                ExperimentConfig.from_dict(data)

    def test_time_grid_numeric_limits(self):
        for dt in (5e-324, 1e308):
            with self.subTest(dt=dt), self.assertRaises(ConfigurationError):
                data = example()
                data["solver"]["dt_s"] = dt
                ExperimentConfig.from_dict(data)

    def test_strict_json_rejects_duplicates_constants_and_invalid_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for contents in ('{"id":"a","id":"b"}', '{"a": NaN}', '{"a": Infinity}', '{broken'):
                with self.subTest(contents=contents), self.assertRaises(ConfigurationError):
                    path.write_text(contents)
                    read_json(path)

    def test_all_environment_profiles_round_trip(self):
        for path in sorted((ROOT / "examples/environments").glob("*.json")):
            with self.subTest(path=path):
                data = read_json(path)
                self.assertEqual(EnvironmentConfig.from_dict(data).to_dict(), data)

    def test_positive_density_and_temperature(self):
        for category, field in (("marine", "fluid_density_kg_m3"), ("air", "temperature_K")):
            data = read_json(ROOT / f"examples/environments/{category}.json")
            for value in (0, -1):
                with self.subTest(category=category, value=value), self.assertRaises(ConfigurationError):
                    data["properties"][field] = value
                    EnvironmentConfig.from_dict(data)

    def test_environment_is_independent_and_properties_are_immutable(self):
        data = example()["environment"]
        environment = EnvironmentConfig.from_dict(data)
        data["properties"]["friction_coefficient"] = 99
        self.assertEqual(environment.properties["friction_coefficient"], 0.6)
        with self.assertRaises(TypeError):
            environment.properties["friction_coefficient"] = 2

    def test_new_category_needs_no_core_enumeration_change(self):
        data = copy.deepcopy(example()["environment"])
        data.update(category="example.orbital", properties={"reference_altitude_m": 400000})
        self.assertEqual(EnvironmentConfig.from_dict(data).category, "example.orbital")
