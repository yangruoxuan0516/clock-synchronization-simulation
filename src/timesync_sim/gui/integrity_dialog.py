from __future__ import annotations

from typing import Dict, Optional, Set, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from ..logic import IntegrityTrace
from ..models import DataMessage


class IntegrityFlowWidget(QWidget):
    def __init__(self, trace: IntegrityTrace, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.trace = trace
        self.setMinimumSize(820, 560)

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        nodes: Dict[str, Tuple[QRectF, str]] = {
            "start": (QRectF(330, 15, 160, 45), "Receive CA message"),
            "dmax_zero": (QRectF(300, 90, 220, 60), "Dmax == 0?"),
            "offset_unknown": (
                QRectF(300, 190, 220, 60),
                "local_clock_offset\nUnknown?",
            ),
            "counter_equal": (
                QRectF(300, 290, 220, 60),
                "reset_counter equal?",
            ),
            "age_valid": (QRectF(300, 390, 220, 60), "0 < age < Dmax?"),
            "result_pass": (QRectF(620, 240, 150, 60), "PASS"),
            "result_discard": (QRectF(620, 390, 150, 60), "DISCARD"),
        }
        edges = [
            ("start", "dmax_zero", ""),
            ("dmax_zero", "result_pass", "Yes"),
            ("dmax_zero", "offset_unknown", "No"),
            ("offset_unknown", "result_pass", "Yes"),
            ("offset_unknown", "counter_equal", "No"),
            ("counter_equal", "age_valid", "Yes"),
            ("counter_equal", "result_discard", "No"),
            ("age_valid", "result_pass", "Yes"),
            ("age_valid", "result_discard", "No"),
        ]

        traversed: Set[str] = {"start"}
        traversed.update(step.key for step in self.trace.steps)
        traversed_edges = self._traversed_edges()

        for source, target, label in edges:
            active = (source, target) in traversed_edges
            self._draw_edge(painter, nodes[source][0], nodes[target][0], label, active)

        for key, (rect, text) in nodes.items():
            self._draw_node(painter, rect, text, key in traversed, key)

    def _traversed_edges(self) -> Set[Tuple[str, str]]:
        keys = ["start"] + [step.key for step in self.trace.steps]
        edges: Set[Tuple[str, str]] = set()
        for source, target in zip(keys, keys[1:]):
            edges.add((source, target))
        return edges

    @staticmethod
    def _draw_node(
        painter: QPainter,
        rect: QRectF,
        text: str,
        active: bool,
        key: str,
    ) -> None:
        if active:
            fill = QColor("#d7f5dd") if "discard" not in key else QColor("#ffd9d9")
            border = QColor("#187a2f") if "discard" not in key else QColor("#a11313")
        else:
            fill = QColor("#f2f2f2")
            border = QColor("#888888")
        painter.setPen(QPen(border, 2 if active else 1))
        painter.setBrush(fill)
        if key in {"dmax_zero", "offset_unknown", "counter_equal", "age_valid"}:
            painter.drawRoundedRect(rect, 18, 18)
        else:
            painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QPen(QColor("black"), 1))
        font = QFont()
        font.setBold(active)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    @staticmethod
    def _draw_edge(
        painter: QPainter,
        source: QRectF,
        target: QRectF,
        label: str,
        active: bool,
    ) -> None:
        pen = QPen(QColor("#1667a8") if active else QColor("#aaaaaa"), 3 if active else 1)
        painter.setPen(pen)
        start = QPointF(source.center().x(), source.bottom())
        end = QPointF(target.center().x(), target.top())
        if target.left() > source.right():
            start = QPointF(source.right(), source.center().y())
            end = QPointF(target.left(), target.center().y())
        painter.drawLine(start, end)

        direction = end - start
        length = max(1.0, (direction.x() ** 2 + direction.y() ** 2) ** 0.5)
        ux, uy = direction.x() / length, direction.y() / length
        left = QPointF(end.x() - 10 * ux + 5 * uy, end.y() - 10 * uy - 5 * ux)
        right = QPointF(end.x() - 10 * ux - 5 * uy, end.y() - 10 * uy + 5 * ux)
        painter.drawLine(end, left)
        painter.drawLine(end, right)
        if label:
            midpoint = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
            painter.drawText(midpoint + QPointF(5, -5), label)


class IntegrityDialog(QDialog):
    def __init__(
        self,
        message: DataMessage,
        trace: IntegrityTrace,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(
            f"Time Integrity Check: CA {message.sender_ca_es_id} -> "
            f"CA {message.receiver_ca_es_id}"
        )
        self.resize(850, 680)
        layout = QVBoxLayout(self)
        summary = QLabel(
            f"sender={message.sender_ca_es_id}, receiver={message.receiver_ca_es_id}, "
            f"message reset_counter={message.reset_counter}, "
            f"transmission_latency/age={message.transmission_latency} ms\n"
            f"Result: {'PASS' if trace.accepted else 'DISCARD'} — {trace.reason}"
        )
        summary.setWordWrap(True)
        summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(summary)
        layout.addWidget(IntegrityFlowWidget(trace, self), 1)
