"""CPU-painted scientific views; no plotting library, OpenGL, or physics state."""

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPaintEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from stemlab.analysis import analytical_state
from stemlab.experiments.results import ExperimentResult

TEAL = QColor("#63dfc4")
AMBER = QColor("#efbb78")
TEXT = QColor("#e7edf5")
MUTED = QColor("#8fa3b8")
GRID = QColor("#243348")


def compact(value: float) -> str:
    return f"{value:.6g}"


@dataclass(frozen=True)
class Scale:
    """Normalize before subtraction to avoid overflow for finite large values."""
    magnitude: float
    low: float
    high: float

    @classmethod
    def of(cls, values: list[float]) -> "Scale":
        magnitude = max((abs(value) for value in values), default=1.0) or 1.0
        low = min(values) / magnitude
        high = max(values) / magnitude
        if high - low < 1e-12:
            padding = 0.1
        else:
            padding = (high - low) * 0.12
        # Avoid rendering tick labels beyond the finite floating-point range.
        maximum = min(1.2, float.fromhex("0x1.fffffffffffffp+1023") / magnitude)
        return cls(magnitude, max(-maximum, low - padding), min(maximum, high + padding))

    def fraction(self, value: float) -> float:
        return (value / self.magnitude - self.low) / (self.high - self.low)

    def tick(self, fraction: float) -> float:
        return (self.low + fraction * (self.high - self.low)) * self.magnitude


class PlotCanvas(QWidget):
    sample_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result: ExperimentResult | None = None
        self.sample_index = 0
        self._traces: list[tuple[float, tuple[float, float], tuple[float, float]]] = []
        self._scales: list[Scale] = []
        self.setMinimumSize(380, 360)
        self.setToolTip("Klik grafik untuk memilih waktu pada hasil simulasi.")

    def set_result(self, result: ExperimentResult) -> None:
        self.result = result
        self.sample_index = 0
        history = result.history
        stride = max(1, len(history) // 1200)
        indices = list(range(0, len(history), stride))
        if indices[-1] != len(history) - 1:
            indices.append(len(history) - 1)
        model = result.config.model
        self._traces = [
            (history[i].time_s, history[i].state, analytical_state(
                history[i].time_s, model.position_m, model.velocity_m_s, result.effective_acceleration_m_s2,
            )) for i in indices
        ]
        self._scales = [Scale.of([sample.state[column] for sample in history]) for column in (0, 1)]
        self.update()

    def set_sample(self, index: int) -> None:
        self.sample_index = index
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.result and event.button() == Qt.MouseButton.LeftButton:
            fraction = max(0.0, min(1.0, (event.position().x() - 88) / max(1, self.width() - 112)))
            self.sample_selected.emit(round(fraction * (len(self.result.history) - 1)))
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101b2a"))
        if self.result is None:
            painter.setPen(MUTED)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Jalankan simulasi untuk menampilkan grafik.")
            return
        painter.setFont(QFont("DejaVu Sans", 9))
        painter.setPen(TEAL)
        painter.drawLine(24, 20, 43, 20)
        painter.setPen(TEXT)
        painter.drawText(50, 24, "Numerik RK4")
        painter.setPen(QPen(AMBER, 1.5, Qt.PenStyle.DashLine))
        painter.drawLine(168, 20, 188, 20)
        painter.setPen(MUTED)
        painter.drawText(195, 24, "Solusi analitis")
        height = (self.height() - 180) / 2
        end_time = self.result.history[-1].time_s
        for column, title in enumerate(("POSISI  /  m", "KECEPATAN  /  m/s")):
            top = 66 + column * (height + 57)
            box = QRectF(88, top, self.width() - 112, height)
            scale = self._scales[column]
            painter.setPen(TEXT)
            painter.drawText(QPointF(24, top - 12), title)
            for tick in range(5):
                fraction = tick / 4
                y = box.bottom() - fraction * box.height()
                x = box.left() + fraction * box.width()
                painter.setPen(QPen(GRID, 1))
                painter.drawLine(QPointF(box.left(), y), QPointF(box.right(), y))
                painter.drawLine(QPointF(x, box.top()), QPointF(x, box.bottom()))
                painter.setPen(MUTED)
                painter.drawText(QRectF(0, y - 10, 78, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                                 compact(scale.tick(fraction)))
                painter.drawText(QRectF(x - 34, box.bottom() + 7, 68, 20), Qt.AlignmentFlag.AlignCenter,
                                 compact(end_time * fraction))
            painter.setPen(MUTED)
            painter.drawText(QRectF(box.right() - 95, box.bottom() + 28, 95, 20), Qt.AlignmentFlag.AlignRight, "waktu (s)")

            for trace_column, pen in ((1, QPen(TEAL, 2.3)), (2, QPen(AMBER, 1.1, Qt.PenStyle.DashLine))):
                path = QPainterPath()
                for index, point in enumerate(self._traces):
                    x = box.left() + (point[0] / end_time) * box.width()
                    y = box.bottom() - scale.fraction(point[trace_column][column]) * box.height()
                    if index == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                painter.setPen(pen)
                painter.drawPath(path)
            current = self.result.history[self.sample_index]
            x = box.left() + (current.time_s / end_time) * box.width()
            y = box.bottom() - scale.fraction(current.state[column]) * box.height()
            painter.setPen(QPen(QColor("#aac1d5"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(x, box.top()), QPointF(x, box.bottom()))
            painter.setPen(QPen(QColor("#101b2a"), 2))
            painter.setBrush(TEAL)
            painter.drawEllipse(QPointF(x, y), 5, 5)


class MotionCanvas(QWidget):
    """Playback of recorded coordinates; no collision/terrain interpretation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result: ExperimentResult | None = None
        self.sample_index = 0
        self.scale = Scale.of([0.0, 1.0])
        self.setMinimumWidth(180)
        self.setMaximumWidth(245)

    def set_result(self, result: ExperimentResult) -> None:
        self.result = result
        self.sample_index = 0
        self.scale = Scale.of([sample.state[0] for sample in result.history])
        self.update()

    def set_sample(self, index: int) -> None:
        self.sample_index = index
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#132131"))
        painter.setFont(QFont("DejaVu Sans", 9))
        painter.setPen(MUTED)
        painter.drawText(QRectF(0, 17, self.width(), 20), Qt.AlignmentFlag.AlignCenter, "JEJAK GERAK 1D")
        if self.result is None:
            return
        axis = self.result.config.model.axis.upper()
        painter.setPen(TEXT)
        painter.drawText(QRectF(0, 42, self.width(), 20), Qt.AlignmentFlag.AlignCenter, f"Sumbu {axis}  •  meter")
        top, bottom = 100.0, float(self.height() - 98)
        center = self.width() * 0.57
        painter.setPen(QPen(GRID, 2))
        painter.drawLine(QPointF(center, top), QPointF(center, bottom))
        for tick in range(5):
            y = bottom - (bottom - top) * tick / 4
            painter.setPen(QPen(GRID, 1))
            painter.drawLine(QPointF(17, y), QPointF(self.width() - 17, y))
            painter.setPen(MUTED)
            painter.drawText(QRectF(7, y - 19, center - 10, 18), Qt.AlignmentFlag.AlignLeft, compact(self.scale.tick(tick / 4)))
        for sample in self.result.history[::max(1, len(self.result.history) // 45)]:
            y = bottom - self.scale.fraction(sample.state[0]) * (bottom - top)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#315561"))
            painter.drawEllipse(QPointF(center, y), 2.5, 2.5)
        initial_y = bottom - self.scale.fraction(self.result.history[0].state[0]) * (bottom - top)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(AMBER, 2))
        painter.drawEllipse(QPointF(center, initial_y), 7, 7)
        current = self.result.history[self.sample_index]
        current_y = bottom - self.scale.fraction(current.state[0]) * (bottom - top)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#244c50"))
        painter.drawEllipse(QPointF(center, current_y), 20, 20)
        painter.setBrush(TEAL)
        painter.drawEllipse(QPointF(center, current_y), 10, 10)
        painter.setPen(TEXT)
        painter.drawText(QRectF(8, self.height() - 72, self.width() - 16, 24), Qt.AlignmentFlag.AlignCenter,
                         f"q = {compact(current.state[0])} m")
        painter.setPen(MUTED)
        painter.drawText(QRectF(8, self.height() - 44, self.width() - 16, 30), Qt.AlignmentFlag.AlignCenter,
                         "Skala otomatis\nTanpa tumbukan")
