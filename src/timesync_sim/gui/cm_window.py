from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..cm_engine import CMEngine, CMRequestRecord
from ..constants import CYCLE_MS
from ..models import ClockOffsetListMessage
from .common import format_optional_number


class CMWindow(QMainWindow):
    def __init__(self, engine: CMEngine) -> None:
        super().__init__()
        self.engine = engine
        self.setWindowTitle(f"Clock Manager - ES_ID {engine.config.es_id}")
        self.resize(880, 680)

        central = QWidget(self)
        root = QVBoxLayout(central)

        heading = QLabel(
            f"Clock Manager (CM) | ES_ID={engine.config.es_id} | "
            f"T1={engine.config.t1} ms | E1={engine.config.e1} ms"
        )
        heading.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(heading)

        self.phase_label = QLabel("Cycle phase: 0 ms")
        self.phase_bar = QProgressBar()
        self.phase_bar.setRange(0, CYCLE_MS - 1)
        self.phase_bar.setTextVisible(True)
        root.addWidget(self.phase_label)
        root.addWidget(self.phase_bar)

        requests_group = QGroupBox("Last two sent request_numbers")
        self.requests_layout = QHBoxLayout(requests_group)
        self.empty_requests_label = QLabel("No request sent yet.")
        self.requests_layout.addWidget(self.empty_requests_label)

        # Create the two request buttons once and only update their contents.
        # Recreating them on every 10 ms state update caused visible flicker and
        # could destroy a button between mouse press and mouse release.
        self.request_buttons: List[QPushButton] = []
        self.request_messages: List[Optional[ClockOffsetListMessage]] = [None, None]
        for slot_index in range(2):
            button = QPushButton()
            button.setMinimumWidth(150)
            button.setVisible(False)
            button.clicked.connect(
                lambda checked=False, index=slot_index: self._show_request_slot(index)
            )
            self.request_buttons.append(button)
            self.requests_layout.addWidget(button)
        self.requests_layout.addStretch(1)
        root.addWidget(requests_group)

        list_group = QGroupBox("clock_offset_list")
        list_layout = QVBoxLayout(list_group)
        self.list_title = QLabel("Select a completed request_number.")
        list_layout.addWidget(self.list_title)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                "CA_ES_ID",
                "CA_relative_offset",
                "CA_reset_counter",
                "CA_relative_offset_error",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        list_layout.addWidget(self.table)
        root.addWidget(list_group, 1)

        log_group = QGroupBox("Runtime log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(160)
        log_layout.addWidget(self.log_view)
        root.addWidget(log_group)

        self.setCentralWidget(central)
        self.engine.state_changed.connect(self._update_state)
        self.engine.log_message.connect(self._append_log)

    def closeEvent(self, event: object) -> None:
        self.engine.stop()
        super().closeEvent(event)  # type: ignore[arg-type]

    def _update_state(self, state: Dict[str, object]) -> None:
        phase = int(state["phase_ms"])
        self.phase_label.setText(f"Cycle phase: {phase} ms / 1000 ms")
        self.phase_bar.setValue(phase)
        self.phase_bar.setFormat(f"{phase} ms")
        records = state.get("records", [])
        self._update_request_buttons(records)  # type: ignore[arg-type]

    def _update_request_buttons(self, records: List[CMRequestRecord]) -> None:
        self.empty_requests_label.setVisible(not records)

        for slot_index, button in enumerate(self.request_buttons):
            if slot_index >= len(records):
                self.request_messages[slot_index] = None
                button.setEnabled(False)
                button.setVisible(False)
                continue

            record = records[slot_index]
            message = record.clock_offset_list
            status = "complete" if record.completed else "calculating"

            self.request_messages[slot_index] = message
            button.setText(f"{record.request_number}\n{status}")
            button.setEnabled(record.completed and message is not None)
            button.setVisible(True)

    def _show_request_slot(self, slot_index: int) -> None:
        message = self.request_messages[slot_index]
        if message is not None:
            self._show_clock_list(message)

    def _show_clock_list(self, message: ClockOffsetListMessage) -> None:
        self.list_title.setText(
            f"CM_ES_ID={message.cm_es_id}, request_number={message.request_number}, "
            f"number_of_CAs={message.number_of_ca}"
        )
        self.table.setRowCount(len(message.entries))
        for row, entry in enumerate(message.entries):
            values = [
                str(entry.ca_es_id),
                format_optional_number(entry.relative_offset),
                "Unknown" if entry.reset_counter is None else str(entry.reset_counter),
                format_optional_number(entry.relative_offset_error),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
