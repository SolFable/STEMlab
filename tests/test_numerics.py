import math
import unittest
from dataclasses import dataclass, replace
from typing import Callable

from stemlab.analysis import validate_constant_acceleration
from stemlab.application import run_experiment
from stemlab.engines.base import Sample, SimulationError
from stemlab.engines.rk4 import RK4Adapter
from stemlab.experiments.config import ExperimentConfig, SolverConfig
from stemlab.modeling import ModelDescription, Quantity, State
from stemlab.validation import ConfigurationError
from test_configuration import example


@dataclass
class ToyODE:
    derivative: Callable[[float, State], State]
    initial_state: State = (1.0,)

    @property
    def description(self):
        return ModelDescription(
            "test_ode", "1", (Quantity("y", "1", "Dimensionless test state"),),
            (), ("dy/dt = f(t,y)",), (), ("Numerical test fixture",), (),
        )

    def rhs(self, time_s, state):
        return self.derivative(time_s, state)


class NumericalTests(unittest.TestCase):
    def test_proof_matches_analytical_solution_at_every_sample(self):
        result = run_experiment(ExperimentConfig.from_dict(example()))
        self.assertEqual(len(result.history), 21)
        self.assertEqual(result.history[0], Sample(0.0, (100.0, 0.0)))
        for sample in result.history:
            with self.subTest(t=sample.time_s):
                self.assertAlmostEqual(sample.state[0], 100 - 0.5 * 9.80665 * sample.time_s ** 2, places=11)
                self.assertAlmostEqual(sample.state[1], -9.80665 * sample.time_s, places=11)
        self.assertEqual(result.history[-1].time_s, 2.0)
        self.assertAlmostEqual(result.history[-1].state[0], 80.3867, places=11)
        self.assertAlmostEqual(result.history[-1].state[1], -19.6133, places=11)
        self.assertTrue(result.validation.passed)

    def test_multiple_axes_and_initial_conditions(self):
        for axis, gravity in zip(("x", "y", "z"), (0.4, -1.2, -9.8), strict=True):
            data = example()
            data["environment"]["gravity_m_s2"] = [0.4, -1.2, -9.8]
            data["model"].update(axis=axis, parameters={"applied_acceleration_m_s2": 2.3},
                                 initial_state={"position_m": -5.0, "velocity_m_s": 3.1})
            with self.subTest(axis=axis):
                result = run_experiment(ExperimentConfig.from_dict(data))
                self.assertAlmostEqual(result.effective_acceleration_m_s2, gravity + 2.3)
                self.assertTrue(result.validation.passed)

    def test_zero_acceleration_and_negative_velocity(self):
        data = example()
        data["environment"]["gravity_m_s2"] = [0, 0, 0]
        data["model"]["initial_state"] = {"position_m": 1.0, "velocity_m_s": -2.0}
        result = run_experiment(ExperimentConfig.from_dict(data))
        self.assertAlmostEqual(result.history[-1].state[0], -3.0)
        self.assertEqual(result.history[-1].state[1], -2.0)

    def test_environment_changes_acceleration_without_changing_model(self):
        data = example()
        reference = run_experiment(ExperimentConfig.from_dict(data))
        data["environment"]["gravity_m_s2"][2] = -1.62
        other = run_experiment(ExperimentConfig.from_dict(data))
        self.assertEqual(reference.config.model, other.config.model)
        self.assertNotEqual(reference.history, other.history)
        self.assertEqual(other.effective_acceleration_m_s2, -1.62)

    def test_rk4_fourth_order_convergence_on_time_dependent_ode(self):
        # y'=y+t, y(0)=1; independent exact solution y(t)=2*exp(t)-t-1.
        model = ToyODE(lambda t, y: (y[0] + t,))
        expected = 2 * math.e - 2
        coarse = RK4Adapter().run(model, SolverConfig(0.1, 10))[-1].state[0]
        fine = RK4Adapter().run(model, SolverConfig(0.05, 20))[-1].state[0]
        ratio = abs(coarse - expected) / abs(fine - expected)
        self.assertGreater(ratio, 14)
        self.assertLess(ratio, 18)
        self.assertLess(abs(fine - expected), 3e-7)

    def test_adapter_rejects_wrong_size_and_nonfinite_derivatives(self):
        for derivative in ((1.0, 2.0), (math.nan,), (math.inf,), (True,)):
            with self.subTest(derivative=derivative), self.assertRaises(SimulationError):
                RK4Adapter().run(ToyODE(lambda t, y: derivative), SolverConfig(0.1, 1))

    def test_adapter_rejects_bad_initial_state(self):
        with self.assertRaises(SimulationError):
            RK4Adapter().run(ToyODE(lambda t, y: y, (math.nan,)), SolverConfig(0.1, 1))

    def test_direct_api_settings_are_validated(self):
        config = ExperimentConfig.from_dict(example())
        with self.assertRaises(ConfigurationError):
            run_experiment(replace(config, solver=SolverConfig(-1, 2)))

    def test_numerical_overflow_fails_instead_of_saving_invalid_data(self):
        with self.assertRaises(SimulationError):
            RK4Adapter().run(ToyODE(lambda t, y: (1e308,), (1e308,)), SolverConfig(10, 2))

    def test_analytical_validation_detects_a_corrupted_state(self):
        report = validate_constant_acceleration((Sample(1.0, (10.0, 0.0)),), 0, 0, 0)
        self.assertFalse(report.passed)
        self.assertEqual(report.max_position_error_m, 10)

    def test_validation_rejects_empty_and_nonfinite_comparisons(self):
        with self.assertRaises(ValueError):
            validate_constant_acceleration((), 0, 0, 0)
        with self.assertRaises(ValueError):
            validate_constant_acceleration((Sample(0, (math.nan, 0)),), 0, 0, 0)
