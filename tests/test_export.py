import csv
from pathlib import Path
import tempfile
import unittest

from stemlab.application import run_experiment
from stemlab.experiments.config import ExperimentConfig
from stemlab.experiments.export import save_history_csv
from test_configuration import example


class ExportTests(unittest.TestCase):
    def test_csv_preserves_history_and_analytical_errors(self):
        result = run_experiment(ExperimentConfig.from_dict(example()))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "history.csv"
            save_history_csv(result, path)
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), len(result.history))
            for sample, row in zip(result.history, rows, strict=True):
                self.assertEqual(float(row["time_s"]), sample.time_s)
                self.assertEqual(float(row["position_m"]), sample.state[0])
                self.assertEqual(float(row["velocity_m_s"]), sample.state[1])
                self.assertLessEqual(float(row["position_error_m"]), result.validation.max_position_error_m)
            previous = path.read_bytes()
            with self.assertRaises(FileExistsError):
                save_history_csv(result, path)
            self.assertEqual(path.read_bytes(), previous)
