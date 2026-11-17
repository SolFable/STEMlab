import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from stemlab.application import run_experiment
from stemlab.experiments.config import ExperimentConfig
from stemlab.experiments.results import configuration_sha256, save_result
from test_configuration import ROOT, example


class WorkflowTests(unittest.TestCase):
    def test_repeated_runs_and_saved_results_are_identical(self):
        config = ExperimentConfig.from_dict(example())
        first = run_experiment(config)
        second = run_experiment(config)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "a.json", Path(directory) / "b.json"
            save_result(first, a)
            save_result(second, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            saved = json.loads(a.read_text())
            self.assertEqual(saved["configuration"], config.to_dict())
            self.assertEqual(saved["history"][0]["state"], [100.0, 0.0])
            self.assertEqual(saved["history"][-1]["time_s"], 2.0)
            self.assertTrue(saved["validation"]["passed"])
            self.assertEqual(saved["provenance"]["configuration_sha256"], configuration_sha256(config))
            self.assertRegex(saved["provenance"]["implementation_sha256"], r"^[a-f0-9]{64}$")
            self.assertIn("assumptions", saved["model_description"])
            self.assertEqual(ExperimentConfig.from_dict(saved["configuration"]), config)

    def test_input_change_changes_fingerprint(self):
        data = example()
        original = configuration_sha256(ExperimentConfig.from_dict(data))
        data["model"]["initial_state"]["velocity_m_s"] = 1.0
        self.assertNotEqual(original, configuration_sha256(ExperimentConfig.from_dict(data)))

    def test_save_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.json"
            path.write_text("preserved")
            with self.assertRaises(FileExistsError):
                save_result(run_experiment(ExperimentConfig.from_dict(example())), path)
            self.assertEqual(path.read_text(), "preserved")

    def test_cli_runs_without_site_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "new-directory" / "result.json"
            env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
            command = [sys.executable, "-S", "-m", "stemlab", str(ROOT / "examples/constant_acceleration.json"), "--output", str(path)]
            process = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("21 samples", process.stdout)
            self.assertEqual(len(json.loads(path.read_text())["history"]), 21)
            again = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(again.returncode, 1)
            self.assertIn("File exists", again.stderr)

    def test_invalid_cli_input_does_not_write_results(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "bad.json", Path(directory) / "result.json"
            source.write_text('{"wrong": true}')
            process = subprocess.run(
                [sys.executable, "-S", "-m", "stemlab", str(source), "--output", str(output)],
                env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
                capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(process.returncode, 1)
            self.assertIn("stemlab:", process.stderr)
            self.assertFalse(output.exists())
