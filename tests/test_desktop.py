"""Optional Qt integration checks using the offscreen raster backend."""

import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

try:
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from stemlab.desktop.presets import default_experiment, environment_presets
    from stemlab.desktop.window import MainWindow
except ImportError:
    QApplication = None

from stemlab.experiments.config import ExperimentConfig


@unittest.skipIf(QApplication is None, "optional PySide6 desktop dependency is unavailable")
class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def pump(milliseconds=20):
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    def setUp(self):
        self.window = MainWindow(autorun=False)
        self.errors = []
        self.window._show_error = lambda title, message: self.errors.append((title, message))
        self.window.show()
        self.pump()

    def tearDown(self):
        self.wait_for_worker()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def wait_for_worker(self):
        deadline = time.monotonic() + 10
        while self.window.worker is not None and time.monotonic() < deadline:
            self.pump()
        self.assertIsNone(self.window.worker, "desktop worker did not finish")

    def run_simulation(self):
        self.window.run_simulation()
        self.wait_for_worker()
        self.assertFalse(self.errors, self.errors)
        self.assertIsNotNone(self.window.result)

    def test_default_configuration_and_environment_profiles(self):
        self.assertEqual(self.window.configuration(), default_experiment())
        for category, environment in environment_presets().items():
            with self.subTest(category=category):
                self.window.profile.setCurrentIndex(self.window.profile.findData(category))
                self.assertEqual(self.window.configuration().environment, environment)

    def test_worker_updates_graphs_metrics_and_table(self):
        self.window.run_simulation()
        self.assertFalse(self.window.run_button.isEnabled())
        self.wait_for_worker()
        self.assertFalse(self.errors)
        result = self.window.result
        self.assertTrue(result.validation.passed)
        self.assertEqual(self.window.table_model.rowCount(), 201)
        self.assertEqual(self.window.table_model.columnCount(), 6)
        self.assertEqual(self.window.metrics["validation"].text(), "Lulus")
        self.assertIs(self.window.plot.result, result)
        self.assertIs(self.window.motion.result, result)
        self.assertTrue(self.window.save_result_button.isEnabled())
        self.assertTrue(self.window.run_button.isEnabled())

    def test_parameter_changes_are_used_only_on_next_run(self):
        self.run_simulation()
        previous = self.window.result
        self.window.position_input.setText("0")
        self.window.axis.setCurrentIndex(self.window.axis.findData("x"))
        self.window.acceleration_input.setText("2,0")
        self.assertIs(self.window.result, previous)
        self.assertEqual(self.window.badge.text(), "PARAMETER DIUBAH")
        self.run_simulation()
        self.assertAlmostEqual(self.window.result.history[-1].state[0], 4.0)
        self.assertAlmostEqual(self.window.result.history[-1].state[1], 4.0)

    def test_invalid_input_preserves_previous_result(self):
        self.run_simulation()
        previous = self.window.result
        self.window.dt_input.setText("not a number")
        self.window.run_simulation()
        self.assertIsNone(self.window.worker)
        self.assertIs(self.window.result, previous)
        self.assertEqual(len(self.errors), 1)

    def test_worker_failure_preserves_result_and_unlocks_controls(self):
        self.run_simulation()
        previous = self.window.result
        with patch("stemlab.desktop.window.run_experiment", side_effect=ValueError("test failure")):
            self.window.run_simulation()
            self.wait_for_worker()
        self.assertIs(self.window.result, previous)
        self.assertEqual(len(self.errors), 1)
        self.assertTrue(self.window.run_button.isEnabled())
        self.assertTrue(self.window.save_result_button.isEnabled())
        self.assertEqual(self.window.badge.text(), "SIMULASI GAGAL")

    def test_export_keeps_original_configuration_after_parameter_edit(self):
        self.run_simulation()
        previous = self.window.result.config
        self.window.position_input.setText("999")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "last-result.json"
            self.window.export_result(path)
            self.assertEqual(json.loads(path.read_text())["configuration"], previous.to_dict())
        self.assertNotEqual(self.window.configuration(), previous)

    def test_configuration_and_results_round_trip_and_csv_export(self):
        self.window.position_input.setText("123.12345678901235")
        self.run_simulation()
        snapshot = self.window.result.config
        with tempfile.TemporaryDirectory() as directory:
            config, result, csv = [Path(directory) / name for name in ("config.json", "result.json", "result.csv")]
            self.window.save_configuration(config)
            self.window.export_result(result)
            self.window.export_result(csv, csv=True)
            self.assertEqual(ExperimentConfig.from_dict(json.loads(config.read_text())), snapshot)
            self.window.position_input.setText("999")
            self.window.load_configuration(result)
            self.assertEqual(self.window.configuration(), snapshot)
            self.assertIn("menghitung ulang", self.window.statusBar().currentMessage())
            self.assertEqual(len(csv.read_text().splitlines()), 202)
            with self.assertRaises(FileExistsError):
                self.window.export_result(result)

    def test_playback_seek_pause_and_completion(self):
        self.run_simulation()
        self.window._seek(100)
        self.assertEqual(self.window.plot.sample_index, 100)
        self.assertEqual(self.window.motion.sample_index, 100)
        self.assertIn("t = 1 s", self.window.sample_label.text())
        self.window.speed.setCurrentIndex(self.window.speed.findData(4.0))
        self.window._toggle_playback()
        self.assertTrue(self.window._timer.isActive())
        self.pump(350)
        self.assertEqual(self.window.slider.value(), 200)
        self.assertFalse(self.window._timer.isActive())

    def test_window_renders_all_tabs_and_laptop_size(self):
        self.run_simulation()
        self.window.resize(1280, 740)
        self.pump()
        self.assertEqual(self.window.height(), 740)
        for index in range(self.window.tabs.count()):
            self.window.tabs.setCurrentIndex(index)
            self.pump()
            self.assertFalse(self.window.grab().isNull())
        self.assertTrue(self.window.run_button.isVisible())

    def test_open_invalid_config_does_not_change_inputs(self):
        previous = self.window.configuration()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text('{"wrong":true}')
            with self.assertRaises(ValueError):
                self.window.load_configuration(path)
        self.assertEqual(self.window.configuration(), previous)
