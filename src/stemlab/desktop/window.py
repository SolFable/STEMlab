"""A small desktop laboratory over the existing validated application workflow."""

from html import escape
import json
import math
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QElapsedTimer, QModelIndex, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSlider,
    QSizePolicy, QSpinBox, QSplitter, QTableView, QTabWidget, QTextBrowser, QToolButton,
    QVBoxLayout, QWidget, QHeaderView,
)

from stemlab.analysis import analytical_state
from stemlab.application import run_experiment
from stemlab.desktop.charts import MotionCanvas, PlotCanvas, compact
from stemlab.desktop.presets import default_experiment, environment_presets
from stemlab.environments import EnvironmentConfig
from stemlab.experiments.config import MAX_STEPS, ExperimentConfig
from stemlab.experiments.export import save_history_csv
from stemlab.experiments.results import ExperimentResult, save_result
from stemlab.validation import ConfigurationError, number, read_json

STYLE = """
QMainWindow, QWidget#root, QWidget#workspace { background: #0b1422; }
QWidget { color: #e7edf5; font-size: 13px; }
QDialog { background: #101b2a; }
QAbstractItemView { background: #101b2a; color: #e7edf5; selection-background-color: #214d49; }
QLabel { background: transparent; }
QLabel#brand { font-size: 25px; font-weight: 700; }
QLabel#heading { font-size: 22px; font-weight: 600; }
QLabel#muted, QLabel#caption { color: #91a5bb; }
QLabel#caption { font-size: 11px; }
QLabel#section { color: #b6c9da; font-size: 11px; font-weight: 700; padding-top: 12px; }
QLabel#metric { font-size: 23px; font-weight: 600; color: #f0f5fa; }
QLabel#badge { background: #173c38; color: #79e8d0; border-radius: 6px; padding: 7px 12px; font-size: 11px; }
QLabel#notice { background: #17283a; color: #a9c3d8; padding: 12px; border-radius: 8px; }
QFrame#card { background: #101f30; border: 1px solid #26364a; border-radius: 9px; }
QScrollArea { background: #101b2a; border: 1px solid #26364a; border-radius: 10px; }
QScrollArea#workscroll { background: transparent; border: none; }
QWidget#sidebar { background: #101b2a; }
QLineEdit, QSpinBox, QComboBox {
  background: #0c1725; border: 1px solid #334359; border-radius: 5px;
  padding: 7px 8px; selection-background-color: #287568; min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #63dfc4; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #142337; selection-background-color: #25564f; }
QPushButton, QToolButton {
  background: #19293e; border: 1px solid #33465c; border-radius: 6px; padding: 9px 13px;
}
QPushButton:hover, QToolButton:hover { background: #243c50; border-color: #71928f; }
QPushButton:disabled, QToolButton:disabled { color: #64788d; background: #142133; border-color: #243348; }
QPushButton#primary { background: #63dfc4; color: #08211f; font-weight: 700; border: none; padding: 12px; }
QPushButton#primary:hover { background: #8aecd7; }
QPushButton#primary:disabled { background: #315d58; color: #a8c4bd; }
QTabWidget::pane { background: #101b2a; border: 1px solid #26364a; border-radius: 8px; }
QTabBar::tab { background: transparent; color: #91a5bb; padding: 11px 18px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #76e4cf; border-bottom: 2px solid #63dfc4; }
QTableView { background: #101b2a; alternate-background-color: #132235; border: none; gridline-color: #243348; selection-background-color: #214d49; }
QHeaderView::section { background: #17283a; color: #b8cadd; padding: 9px; border: none; }
QTextBrowser { background: #101b2a; border: none; padding: 18px; }
QSlider::groove:horizontal { height: 5px; background: #2b4055; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #4ba994; border-radius: 2px; }
QSlider::handle:horizontal { background: #78e5cf; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
QProgressBar { background: #17283a; border: none; max-height: 4px; }
QProgressBar::chunk { background: #63dfc4; }
QStatusBar { background: #0b1422; color: #91a5bb; }
QMenuBar { background: #0b1422; color: #91a5bb; }
QMenuBar::item:selected, QMenu::item:selected { background: #25564f; }
QMenu { background: #142337; border: 1px solid #33465c; padding: 5px; }
QScrollBar:vertical { background: #101b2a; width: 9px; }
QScrollBar::handle:vertical { background: #33465c; border-radius: 4px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #0b1422; width: 12px; }
"""

PROPERTY_LABELS = {
    "friction_coefficient": "Koefisien gesek (1)", "terrain_height_m": "Tinggi acuan (m)",
    "fluid_density_kg_m3": "Densitas fluida (kg/m³)", "temperature_K": "Temperatur (K)",
    **{f"current_{axis}_m_s": f"Arus {axis.upper()} (m/s)" for axis in "xyz"},
    **{f"wind_{axis}_m_s": f"Angin {axis.upper()} (m/s)" for axis in "xyz"},
}


class ExperimentWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, config: ExperimentConfig, parent=None):
        super().__init__(parent)
        self.config = config

    def run(self) -> None:
        try:
            self.succeeded.emit(run_experiment(self.config))
        except Exception as exc:
            # Surface worker failures in the UI instead of terminating the thread silently.
            self.failed.emit(str(exc) or type(exc).__name__)


class HistoryTableModel(QAbstractTableModel):
    HEADERS = ("Langkah", "Waktu (s)", "Posisi (m)", "Kecepatan (m/s)", "Galat posisi (m)", "Galat kecepatan (m/s)")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result: ExperimentResult | None = None

    def set_result(self, result: ExperimentResult) -> None:
        self.beginResetModel()
        self.result = result
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() or self.result is None else len(self.result.history)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self.result is None:
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        sample = self.result.history[index.row()]
        model = self.result.config.model
        q, v = analytical_state(sample.time_s, model.position_m, model.velocity_m_s, self.result.effective_acceleration_m_s2)
        values = (index.row(), sample.time_s, *sample.state, abs(sample.state[0] - q), abs(sample.state[1] - v))
        return str(values[0]) if index.column() == 0 else f"{values[index.column()]:.12g}"


class MainWindow(QMainWindow):
    def __init__(self, *, autorun: bool = True):
        super().__init__()
        self.setWindowTitle("STEMLab — Laboratorium Komputasi")
        self.resize(1380, 900)
        self.setMinimumSize(1060, 720)
        self.setStyleSheet(STYLE)
        self.result: ExperimentResult | None = None
        self.worker: ExperimentWorker | None = None
        self._loading = True
        self._dirty = False
        self._environments = environment_presets()
        self._environment_id = ""
        self._property_inputs: dict[str, QLineEdit] = {}
        self._play_origin = 0.0
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._build_ui()
        self._apply_configuration(default_experiment())
        self.statusBar().showMessage("Siap. Ubah parameter, lalu jalankan eksperimen. Semua besaran menggunakan satuan SI.")
        if autorun:
            QTimer.singleShot(100, self.run_simulation)

    @staticmethod
    def _label(text: str, name: str = "") -> QLabel:
        label = QLabel(text)
        label.setObjectName(name)
        return label

    def _input(self, value: float = 0.0) -> QLineEdit:
        widget = QLineEdit(str(value))
        widget.setMinimumWidth(95)
        widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        widget.setToolTip("Angka dalam satuan SI. Gunakan titik desimal; notasi seperti 1e-3 juga diterima.")
        widget.textChanged.connect(self._parameters_changed)
        return widget

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 12, 22, 12)
        outer.setSpacing(14)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QIcon(str(Path(__file__).with_name("icon.svg"))).pixmap(46, 46))
        header.addWidget(icon)
        title = QVBoxLayout()
        title.setSpacing(2)
        title.addWidget(self._label("STEMLab", "brand"))
        title.addWidget(self._label("LABORATORIUM KOMPUTASI STEM", "caption"))
        header.addLayout(title)
        header.addStretch()
        self.open_button = QPushButton("Buka eksperimen")
        self.open_button.clicked.connect(self._open_dialog)
        self.save_config_button = QPushButton("Simpan konfigurasi")
        self.save_config_button.clicked.connect(self._save_configuration_dialog)
        header.addWidget(self.open_button)
        header.addWidget(self.save_config_button)
        outer.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(16)
        outer.addWidget(splitter, 1)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        form = QVBoxLayout(self.sidebar)
        form.setContentsMargins(19, 15, 19, 19)
        form.setSpacing(11)
        form.addWidget(self._label("Atur eksperimen", "heading"))
        caption = self._label("Satu model. Parameter terbuka.\nHasil yang dapat diperiksa.", "muted")
        form.addWidget(caption)
        form.addWidget(self._label("IDENTITAS", "section"))
        self.experiment_id = QLineEdit()
        self.experiment_id.setMinimumWidth(0)
        self.experiment_id.textChanged.connect(self._parameters_changed)
        self.experiment_id.setAccessibleName("Nama eksperimen")
        form.addWidget(self.experiment_id)
        form.addWidget(self._label("LINGKUNGAN", "section"))
        self.profile = QComboBox()
        self.profile.currentIndexChanged.connect(self._profile_changed)
        self.profile.setToolTip("Memilih profil memuat nilai referensi lingkungan tersebut.")
        form.addWidget(self.profile)
        environment_form = QFormLayout()
        environment_form.setSpacing(9)
        self.gravity_inputs = [self._input() for _ in "xyz"]
        for axis, widget in zip("XYZ", self.gravity_inputs, strict=True):
            environment_form.addRow(f"Gravitasi {axis} (m/s²)", widget)
        form.addLayout(environment_form)
        self.properties_toggle = QToolButton()
        self.properties_toggle.setText("▸  Properti lingkungan lainnya")
        self.properties_toggle.setCheckable(True)
        self.properties_toggle.toggled.connect(self._toggle_properties)
        form.addWidget(self.properties_toggle)
        self.properties_container = QWidget()
        self.properties_form = QFormLayout(self.properties_container)
        self.properties_form.setContentsMargins(0, 0, 0, 0)
        self.properties_form.setSpacing(9)
        self.properties_container.hide()
        form.addWidget(self.properties_container)

        form.addWidget(self._label("MODEL & KONDISI AWAL", "section"))
        form.addWidget(self._label("Gerak 1D • percepatan konstan", "muted"))
        model_form = QFormLayout()
        model_form.setSpacing(9)
        self.axis = QComboBox()
        for axis in "xyz":
            self.axis.addItem(f"{axis.upper()} — sumbu dunia", axis)
        self.axis.currentIndexChanged.connect(self._parameters_changed)
        self.position_input = self._input()
        self.velocity_input = self._input()
        self.acceleration_input = self._input()
        model_form.addRow("Sumbu gerak", self.axis)
        model_form.addRow("Posisi awal (m)", self.position_input)
        model_form.addRow("Kecepatan awal (m/s)", self.velocity_input)
        model_form.addRow("Percepatan tambahan (m/s²)", self.acceleration_input)
        form.addLayout(model_form)
        form.addWidget(self._label("INTEGRASI NUMERIK", "section"))
        solver_form = QFormLayout()
        solver_form.setSpacing(9)
        self.dt_input = self._input()
        self.steps_input = QSpinBox()
        self.steps_input.setRange(1, MAX_STEPS)
        self.steps_input.setSingleStep(100)
        self.steps_input.valueChanged.connect(self._parameters_changed)
        solver_form.addRow("Langkah waktu (s)", self.dt_input)
        solver_form.addRow("Jumlah langkah", self.steps_input)
        form.addLayout(solver_form)
        self.duration_label = self._label("", "muted")
        self.duration_label.setWordWrap(True)
        self.run_button = QPushButton("▶  Jalankan simulasi")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.run_simulation)
        self.reset_button = QPushButton("Muat contoh awal")
        self.reset_button.clicked.connect(self._reset)
        form.addStretch()
        for layout in (environment_form, model_form, solver_form, self.properties_form):
            layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.sidebar)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(345)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_layout.addWidget(scroll, 1)
        left_layout.addWidget(self.duration_label)
        left_layout.addWidget(self.run_button)
        left_layout.addWidget(self.reset_button)
        splitter.addWidget(left_panel)

        work = QWidget()
        work.setObjectName("workspace")
        content = QVBoxLayout(work)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(12)
        heading = QHBoxLayout()
        heading.addWidget(self._label("Ruang eksperimen", "heading"))
        heading.addStretch()
        self.badge = self._label("SIAP DIJALANKAN", "badge")
        heading.addWidget(self.badge)
        content.addLayout(heading)
        notice = self._label(
            "Model ideal: gravitasi + percepatan tambahan. Gesekan, hambatan fluida, gaya apung, "
            "dan tumbukan belum dihitung.", "notice",
        )
        notice.setWordWrap(True)
        content.addWidget(notice)
        metrics = QHBoxLayout()
        self.metrics: dict[str, QLabel] = {}
        self.metric_details: dict[str, QLabel] = {}
        for key, title in (("position", "POSISI AKHIR"), ("velocity", "KECEPATAN AKHIR"), ("acceleration", "PERCEPATAN"), ("validation", "UJI ANALITIS")):
            card = QFrame()
            card.setObjectName("card")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.addWidget(self._label(title, "caption"))
            self.metrics[key] = self._label("—", "metric")
            self.metric_details[key] = self._label("Menunggu hasil", "caption")
            layout.addWidget(self.metrics[key])
            layout.addWidget(self.metric_details[key])
            metrics.addWidget(card, 1)
        content.addLayout(metrics)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setDrawBase(False)
        plot_page = QWidget()
        plots = QVBoxLayout(plot_page)
        plots.setContentsMargins(1, 1, 1, 10)
        plots.setSpacing(8)
        canvas_row = QHBoxLayout()
        canvas_row.setSpacing(0)
        self.plot = PlotCanvas()
        self.motion = MotionCanvas()
        self.plot.sample_selected.connect(self._seek)
        canvas_row.addWidget(self.plot, 1)
        canvas_row.addWidget(self.motion)
        plots.addLayout(canvas_row, 1)
        playback = QHBoxLayout()
        playback.setContentsMargins(12, 0, 12, 0)
        self.play_button = QPushButton("▶  Putar")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self._toggle_playback)
        playback.addWidget(self.play_button)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self._display_sample)
        self.slider.sliderPressed.connect(self._pause)
        self.slider.actionTriggered.connect(self._pause)
        playback.addWidget(self.slider, 1)
        self.speed = QComboBox()
        for speed in (0.25, 0.5, 1.0, 2.0, 4.0):
            self.speed.addItem(f"{speed:g}×", speed)
        self.speed.setCurrentIndex(2)
        self.speed.currentIndexChanged.connect(self._change_speed)
        playback.addWidget(self.speed)
        plots.addLayout(playback)
        self.sample_label = self._label("Belum ada hasil simulasi", "muted")
        self.sample_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plots.addWidget(self.sample_label)
        self.tabs.addTab(plot_page, "Grafik dan gerak")
        self.table_model = HistoryTableModel(self)
        table = QTableView()
        table.setModel(self.table_model)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.verticalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(table, "Tabel data")
        self.model_notes = QTextBrowser()
        self.model_notes.setOpenExternalLinks(False)
        self.tabs.addTab(self.model_notes, "Model dan validasi")
        content.addWidget(self.tabs, 1)
        bottom = QHBoxLayout()
        self.result_label = self._label("Hasil disimpan hanya saat Anda memilih ekspor.", "muted")
        self.result_label.setWordWrap(True)
        bottom.addWidget(self.result_label, 1)
        self.save_result_button = QPushButton("Simpan hasil JSON")
        self.save_result_button.clicked.connect(self._save_result_dialog)
        self.csv_button = QPushButton("Ekspor CSV")
        self.csv_button.clicked.connect(self._csv_dialog)
        self.save_result_button.setEnabled(False)
        self.csv_button.setEnabled(False)
        bottom.addWidget(self.save_result_button)
        bottom.addWidget(self.csv_button)
        content.addLayout(bottom)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        content.addWidget(self.progress)
        work_scroll = QScrollArea()
        work_scroll.setObjectName("workscroll")
        work_scroll.setWidgetResizable(True)
        work_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        work_scroll.setWidget(work)
        work_scroll.setMinimumWidth(630)
        splitter.addWidget(work_scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([355, 1000])
        for name, shortcut, callback in (
            ("Buka eksperimen…", "Ctrl+O", self._open_dialog),
            ("Simpan konfigurasi…", "Ctrl+S", self._save_configuration_dialog),
            ("Jalankan simulasi", "Ctrl+R", self.run_simulation),
        ):
            action = QAction(name, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            self.addAction(action)

    def _toggle_properties(self, expanded: bool) -> None:
        self.properties_container.setVisible(expanded)
        self.properties_toggle.setText(("▾" if expanded else "▸") + "  Properti lingkungan lainnya")

    def _set_environment(self, environment: EnvironmentConfig) -> None:
        self._environment_id = environment.id
        for widget, value in zip(self.gravity_inputs, environment.gravity_m_s2, strict=True):
            widget.setText(str(value))
        while self.properties_form.rowCount():
            self.properties_form.removeRow(0)
        self._property_inputs = {}
        for name, value in environment.properties.items():
            widget = self._input(value)
            self._property_inputs[name] = widget
            self.properties_form.addRow(PROPERTY_LABELS.get(name, name), widget)

    def _profile_changed(self, index: int) -> None:
        if index < 0:
            return
        was_loading = self._loading
        self._loading = True
        self._set_environment(self._environments[self.profile.currentData()])
        self._loading = was_loading
        self._parameters_changed()

    def _apply_configuration(self, config: ExperimentConfig) -> None:
        self._loading = True
        self._environments[config.environment.category] = config.environment
        self.profile.blockSignals(True)
        self.profile.clear()
        labels = {"land": "LAND  /  Darat", "marine": "MARINE  /  Laut", "air": "AIR  /  Udara"}
        for category in self._environments:
            self.profile.addItem(labels.get(category, category), category)
        self.profile.setCurrentIndex(self.profile.findData(config.environment.category))
        self.profile.blockSignals(False)
        self._set_environment(config.environment)
        self.experiment_id.setText(config.id)
        self.axis.setCurrentIndex(self.axis.findData(config.model.axis))
        self.position_input.setText(str(config.model.position_m))
        self.velocity_input.setText(str(config.model.velocity_m_s))
        self.acceleration_input.setText(str(config.model.applied_acceleration_m_s2))
        self.dt_input.setText(str(config.solver.dt_s))
        self.steps_input.setValue(config.solver.steps)
        self._loading = False
        self._parameters_changed()

    @staticmethod
    def _read_number(widget: QLineEdit, label: str) -> float:
        try:
            return number(float(widget.text().strip().replace(",", ".")), label)
        except (ValueError, OverflowError) as exc:
            raise ConfigurationError(f"{label}: masukkan angka berhingga yang valid.") from exc

    def configuration(self) -> ExperimentConfig:
        """Take a validated snapshot; displayed results retain their own snapshot."""
        return ExperimentConfig.from_dict({
            "schema_version": 1, "id": self.experiment_id.text().strip(),
            "environment": {
                "schema_version": 1, "id": self._environment_id, "category": self.profile.currentData(),
                "gravity_m_s2": [self._read_number(widget, f"Gravitasi {axis}") for axis, widget in zip("xyz", self.gravity_inputs, strict=True)],
                "properties": {key: self._read_number(widget, PROPERTY_LABELS.get(key, key)) for key, widget in self._property_inputs.items()},
            },
            "model": {
                "id": "constant_acceleration_1d", "version": "1", "axis": self.axis.currentData(),
                "parameters": {"applied_acceleration_m_s2": self._read_number(self.acceleration_input, "Percepatan tambahan")},
                "initial_state": {
                    "position_m": self._read_number(self.position_input, "Posisi awal"),
                    "velocity_m_s": self._read_number(self.velocity_input, "Kecepatan awal"),
                },
            },
            "solver": {
                "id": "python_rk4", "version": "1", "dt_s": self._read_number(self.dt_input, "Langkah waktu"),
                "steps": self.steps_input.value(),
            },
        })

    def _parameters_changed(self, *_args) -> None:
        if self._loading:
            return
        self._dirty = True
        self.badge.setText("PARAMETER DIUBAH" if self.result else "SIAP DIJALANKAN")
        try:
            duration = self._read_number(self.dt_input, "dt") * self.steps_input.value()
            if duration <= 0 or not math.isfinite(duration):
                raise ValueError("Durasi tidak valid")
            self.duration_label.setText(f"Durasi {compact(duration)} s  •  {self.steps_input.value() + 1:,} sampel\nMetode RK4 • CPU")
        except ValueError:
            self.duration_label.setText("Periksa langkah waktu sebelum menjalankan.")
        if self.result:
            self.result_label.setText("Parameter berubah. Grafik dan ekspor tetap memakai hasil terakhir; jalankan lagi untuk memperbarui.")

    def _set_busy(self, busy: bool) -> None:
        self.sidebar.setEnabled(not busy)
        self.run_button.setEnabled(not busy)
        self.reset_button.setEnabled(not busy)
        self.open_button.setEnabled(not busy)
        self.save_config_button.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.run_button.setText("Menghitung…" if busy else "▶  Jalankan simulasi")
        self.save_result_button.setEnabled(not busy and self.result is not None)
        self.csv_button.setEnabled(not busy and self.result is not None)

    def run_simulation(self) -> None:
        if self.worker is not None:
            return
        try:
            config = self.configuration()
        except (ValueError, OverflowError) as exc:
            self._show_error("Konfigurasi belum valid", str(exc))
            return
        self._pause()
        self._set_busy(True)
        self.badge.setText("MENGHITUNG")
        self.statusBar().showMessage("Menjalankan simulasi dan membandingkan setiap sampel dengan solusi analitis…")
        self.worker = ExperimentWorker(config, self)
        self.worker.succeeded.connect(self._accept_result)
        self.worker.failed.connect(self._simulation_failed)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _worker_finished(self) -> None:
        worker = self.worker
        self.worker = None
        self._set_busy(False)
        if worker is not None:
            worker.deleteLater()

    def _simulation_failed(self, message: str) -> None:
        self.badge.setText("SIMULASI GAGAL")
        self.result_label.setText("Run baru gagal. Hasil sebelumnya, jika ada, tetap dipertahankan.")
        self._show_error("Simulasi tidak dapat diselesaikan", message)

    def _accept_result(self, result: ExperimentResult) -> None:
        self.result = result
        self._dirty = False
        self.plot.set_result(result)
        self.motion.set_result(result)
        self.table_model.set_result(result)
        self.slider.setRange(0, len(result.history) - 1)
        self.slider.setValue(0)
        self.slider.setEnabled(True)
        self.play_button.setEnabled(True)
        self._display_sample(0)
        final = result.history[-1]
        self.metrics["position"].setText(f"{compact(final.state[0])} m")
        self.metrics["velocity"].setText(f"{compact(final.state[1])} m/s")
        self.metrics["acceleration"].setText(f"{compact(result.effective_acceleration_m_s2)} m/s²")
        self.metrics["validation"].setText("Lulus")
        self.metric_details["position"].setText(f"pada t = {compact(final.time_s)} s")
        self.metric_details["velocity"].setText(f"sumbu {result.config.model.axis.upper()}")
        self.metric_details["acceleration"].setText("gravitasi + tambahan")
        self.metric_details["validation"].setText(f"galat q ≤ {result.validation.max_position_error_m:.2e} m")
        self.badge.setText("TERVALIDASI")
        self.result_label.setText(f"{result.config.id}  •  {len(result.history):,} sampel  •  seluruh sampel lulus uji analitis")
        self.statusBar().showMessage("Simulasi selesai. Putar gerak, geser waktu, atau periksa tabel dan model.")
        self._update_model_notes(result)

    def _update_model_notes(self, result: ExperimentResult) -> None:
        config = result.config
        report = result.validation
        below_reference = (
            config.environment.category == "land" and config.model.axis == "z"
            and min(sample.state[0] for sample in result.history) < config.environment.properties["terrain_height_m"]
        )
        ground_note = (
            "<p style='color:#efbb78'>Lintasan melewati bidang tanah acuan. Model ini tidak menangani tumbukan; "
            "bagian tersebut hanya solusi matematis tanpa batas kontak.</p>" if below_reference else ""
        )
        self.model_notes.setHtml(f"""
        <style>body {{color:#dce7f0;font-family:sans-serif;line-height:1.5}}
        h2,h3 {{color:#79e8d0}} code {{color:#efbb78}} td {{padding:6px 15px 6px 0}}</style>
        <h2>Gerak satu dimensi dengan percepatan konstan</h2>
        <p>Catatan ini menjelaskan <b>hasil terakhir</b>, bukan parameter yang belum dijalankan.</p>
        <h3>Persamaan</h3><p><code>dq/dt = v<br>dv/dt = a<br>a = g[sumbu] + a_tambahan</code></p>
        <p>Solusi analitis: <code>q(t) = q₀ + v₀t + ½at²</code> dan <code>v(t) = v₀ + at</code>.</p>
        <h3>Eksperimen {escape(config.id)}</h3>
        <table><tr><td>Lingkungan / sumbu</td><td>{escape(config.environment.category.upper())} / {config.model.axis.upper()}</td></tr>
        <tr><td>Kondisi awal</td><td>q₀ = {config.model.position_m:g} m; v₀ = {config.model.velocity_m_s:g} m/s</td></tr>
        <tr><td>Percepatan efektif</td><td>{result.effective_acceleration_m_s2:g} m/s²</td></tr>
        <tr><td>Metode</td><td>Runge–Kutta orde 4, langkah tetap {config.solver.dt_s:g} s</td></tr>
        <tr><td>Galat maksimum posisi</td><td>{report.max_position_error_m:.12g} m</td></tr>
        <tr><td>Galat maksimum kecepatan</td><td>{report.max_velocity_error_m_s:.12g} m/s</td></tr>
        <tr><td>Toleransi</td><td>absolut {report.absolute_tolerance:g} dalam satuan masing-masing; relatif {report.relative_tolerance:g}</td></tr></table>
        <h3>Asumsi & batas model</h3>
        <p>Benda berupa partikel titik dalam kerangka inersial. Gravitasi dan percepatan tambahan konstan.
        Percepatan tambahan merupakan masukan kinematik, bukan hasil perhitungan gaya atau mesin.</p>
        <p><b>Gesekan, drag, gaya apung, angin/arus, rotasi, dan tumbukan tidak dihitung.</b>
        Properti lingkungan selain gravitasi dicatat untuk eksperimen, tetapi tidak memengaruhi persamaan model ini.
        Memilih MARINE atau AIR tidak otomatis menghasilkan dinamika kapal atau pesawat.</p>{ground_note}
        <h3>Membaca hasil</h3>
        <p>Garis hijau adalah RK4, garis putus-putus jingga adalah solusi analitis. Keduanya hampir menumpuk
        karena RK4 tepat untuk percepatan konstan dalam aritmetika eksak; selisih kecil berasal dari pembulatan.
        Jejak gerak hanya memutar ulang koordinat tersimpan, dengan skala otomatis.</p>
        <h3>Mengulangi eksperimen</h3>
        <p>Simpan hasil JSON untuk menyimpan konfigurasi, data, asumsi, dan identitas implementasi.
        Buka JSON tersebut sebagai konfigurasi untuk menjalankan ulang. CSV berisi data tabular saja;
        simpan JSON juga bila perlu rekam eksperimen lengkap.</p>
        <p><code>SHA-256 konfigurasi ada di hasil JSON.<br>Sumber: {escape(result.source_sha256)}</code></p>
        """)

    def _display_sample(self, index: int) -> None:
        if self.result is None:
            return
        self.plot.set_sample(index)
        self.motion.set_sample(index)
        sample = self.result.history[index]
        self.sample_label.setText(
            f"t = {compact(sample.time_s)} s     |     q = {compact(sample.state[0])} m     |     "
            f"v = {compact(sample.state[1])} m/s     |     sampel {index + 1}/{len(self.result.history)}"
        )

    def _pause(self, *_args) -> None:
        self._timer.stop()
        self.play_button.setText("▶  Putar")

    def _seek(self, index: int) -> None:
        self._pause()
        self.slider.setValue(index)

    def _toggle_playback(self) -> None:
        if self.result is None:
            return
        if self._timer.isActive():
            self._pause()
            return
        if self.slider.value() == self.slider.maximum():
            self.slider.setValue(0)
        self._play_origin = self.result.history[self.slider.value()].time_s
        self._clock.start()
        self._timer.start()
        self.play_button.setText("Ⅱ  Jeda")

    def _change_speed(self, *_args) -> None:
        if self._timer.isActive() and self.result:
            self._play_origin = self.result.history[self.slider.value()].time_s
            self._clock.restart()

    def _tick(self) -> None:
        if self.result is None:
            return
        end_time = self.result.history[-1].time_s
        time_s = self._play_origin + self._clock.elapsed() / 1000 * self.speed.currentData()
        fraction = min(1.0, time_s / end_time)
        self.slider.setValue(int(fraction * self.slider.maximum()))
        if fraction >= 1.0:
            self._pause()

    def _reset(self) -> None:
        if self.worker is None:
            self._apply_configuration(default_experiment())
            self.run_simulation()

    def load_configuration(self, path: str | Path) -> None:
        if self.worker is not None:
            raise ValueError("Tunggu simulasi selesai sebelum membuka eksperimen.")
        data = read_json(path)
        from_result = isinstance(data, dict) and "configuration" in data
        config = ExperimentConfig.from_dict(data["configuration"] if from_result else data)
        self._apply_configuration(config)
        self.statusBar().showMessage(
            "Konfigurasi dari hasil lama dimuat. Jalankan untuk menghitung ulang pada versi ini."
            if from_result else "Konfigurasi dimuat. Klik Jalankan simulasi untuk menghitung hasilnya."
        )

    def save_configuration(self, path: str | Path) -> None:
        contents = json.dumps(self.configuration().to_dict(), indent=2, allow_nan=False) + "\n"
        with Path(path).open("x", encoding="utf-8") as stream:
            stream.write(contents)

    def export_result(self, path: str | Path, *, csv: bool = False) -> None:
        if self.result is None:
            raise ValueError("Jalankan eksperimen sebelum mengekspor hasil.")
        (save_history_csv if csv else save_result)(self.result, path)

    def _show_error(self, title: str, message: str) -> None:
        self.statusBar().showMessage(f"{title}: {message}")
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Warning)
        box.exec()

    def _open_dialog(self) -> None:
        if self.worker is not None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Buka konfigurasi atau hasil STEMLab", "", "JSON (*.json)")
        if path:
            try:
                self.load_configuration(path)
            except (OSError, ValueError, OverflowError) as exc:
                self._show_error("Tidak dapat membuka eksperimen", str(exc))

    def _save_dialog(self, kind: str) -> None:
        if self.worker is not None:
            return
        suffix = "csv" if kind == "csv" else "json"
        name = "konfigurasi" if kind == "configuration" else "hasil"
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan sebagai file baru", f"stemlab-{name}.{suffix}", f"{suffix.upper()} (*.{suffix})",
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not path:
            return
        if not Path(path).suffix:
            path += f".{suffix}"
        try:
            if kind == "configuration":
                self.save_configuration(path)
            else:
                self.export_result(path, csv=kind == "csv")
            self.statusBar().showMessage(f"Tersimpan: {path}")
        except FileExistsError:
            self._show_error("File sudah ada", "Pilih nama file baru. File eksperimen lama tetap dipertahankan.")
        except (OSError, ValueError, OverflowError) as exc:
            self._show_error("Tidak dapat menyimpan", str(exc))

    def _save_configuration_dialog(self) -> None:
        self._save_dialog("configuration")

    def _save_result_dialog(self) -> None:
        self._save_dialog("result")

    def _csv_dialog(self) -> None:
        self._save_dialog("csv")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker is not None:
            self.statusBar().showMessage("Tunggu proses simulasi selesai, lalu tutup kembali aplikasi.")
            event.ignore()
            return
        self._pause()
        super().closeEvent(event)
