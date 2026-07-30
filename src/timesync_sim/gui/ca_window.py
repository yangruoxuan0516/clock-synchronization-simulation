from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from ..ca_engine import CAEngine
from ..constants import CYCLE_MS
from ..logic import IntegrityTrace
from ..models import DataMessage
from .common import format_optional_number
from .integrity_dialog import IntegrityDialog


class SendMessageDialog(QDialog):
    def __init__(self, receiver_ids: List[int], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Send CA message")
        layout = QFormLayout(self)
        self.receiver_combo = QComboBox()
        for es_id in receiver_ids:
            self.receiver_combo.addItem(str(es_id), es_id)
        self.latency_spin = QSpinBox()
        self.latency_spin.setRange(0, 2_147_483_647)
        self.latency_spin.setSuffix(" ms")
        self.payload_edit = QLineEdit("CA communication test message")
        layout.addRow("receiver_CA ES_ID", self.receiver_combo)
        layout.addRow("transmission_latency", self.latency_spin)
        layout.addRow("payload", self.payload_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> tuple[int, int, str]:
        return (
            int(self.receiver_combo.currentData()),
            self.latency_spin.value(),
            self.payload_edit.text(),
        )


class CAWindow(QMainWindow):
    def __init__(self, engine: CAEngine) -> None:
        super().__init__()
        self.engine = engine
        self.integrity_dialogs: List[IntegrityDialog] = []
        self.setWindowTitle(f"Clock Agent - ES_ID {engine.config.es_id}")
        self.resize(820, 700)

        central = QWidget(self)
        root = QVBoxLayout(central)

        heading = QLabel(
            f"Clock Agent (CA) | ES_ID={engine.config.es_id} | "
            f"T2={engine.config.t2} ms | Dmax={engine.config.dmax} ms"
        )
        heading.setObjectName("heading")
        root.addWidget(heading)
        self.heading = heading

        self.phase_label = QLabel("Selected-CM cycle phase: 0 ms")
        self.phase_bar = QProgressBar()
        self.phase_bar.setRange(0, CYCLE_MS - 1)
        root.addWidget(self.phase_label)
        root.addWidget(self.phase_bar)

        self.source_label = QLabel("Current data source: election pending")
        self.source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.source_label)

        status_group = QGroupBox("CA state")
        status_layout = QHBoxLayout(status_group)
        self.reset_counter_label = QLabel("reset_counter: 0")
        self.t2_label = QLabel(f"T2: {engine.config.t2} ms")
        status_layout.addWidget(self.reset_counter_label)
        status_layout.addWidget(self.t2_label)
        status_layout.addStretch(1)
        root.addWidget(status_group)

        offsets_group = QGroupBox("local_clock_offset")
        offsets_layout = QVBoxLayout(offsets_group)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["remote_ES_ID", "local_clock_offset"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        offsets_layout.addWidget(self.table)
        root.addWidget(offsets_group, 1)

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset")
        self.send_button = QPushButton("Send message")
        self.reset_button.clicked.connect(self._reset)
        self.send_button.clicked.connect(self._send_message)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.send_button)
        button_layout.addStretch(1)
        root.addLayout(button_layout)

        log_group = QGroupBox("Runtime log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(170)
        log_layout.addWidget(self.log_view)
        root.addWidget(log_group)

        self.setCentralWidget(central)
        self.engine.state_changed.connect(self._update_state)
        self.engine.log_message.connect(self._append_log)
        self.engine.integrity_checked.connect(self._show_integrity_dialog)

    def closeEvent(self, event: object) -> None:
        self.engine.stop()
        super().closeEvent(event)  # type: ignore[arg-type]

    def _update_state(self, state: Dict[str, object]) -> None:
        phase = int(state["phase_ms"])
        self.phase_label.setText(f"Selected-CM cycle phase: {phase} ms / 1000 ms")
        self.phase_bar.setValue(phase)
        self.phase_bar.setFormat(f"{phase} ms")

        selected = state["selected_cm_es_id"]
        request_number = state["source_request_number"]
        if selected is None:
            self.source_label.setText("Current data source: election pending")
        elif request_number is None:
            self.source_label.setText(
                f"Current data source: CM {selected}; no effective clock_offset_list"
            )
        else:
            self.source_label.setText(
                f"Current data source: CM {selected}, clock_offset_list "
                f"request_number={request_number}"
            )

        self.reset_counter_label.setText(
            f"reset_counter: {state['reset_counter']}"
        )
        self.t2_label.setText(f"T2: {state['t2']} ms")
        self.heading.setText(
            f"Clock Agent (CA) | ES_ID={self.engine.config.es_id} | "
            f"T2={state['t2']} ms | Dmax={state['dmax']} ms"
        )
        offsets = state["local_clock_offsets"]
        self._update_offsets(offsets)  # type: ignore[arg-type]

    def _update_offsets(self, offsets: Dict[int, object]) -> None:
        rows = sorted(offsets.items())
        self.table.setRowCount(len(rows))
        for row, (remote_id, offset) in enumerate(rows):
            values = [str(remote_id), format_optional_number(offset)]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def _reset(self) -> None:
        self.engine.reset()
        value, accepted = QInputDialog.getDouble(
            self,
            "Change T2 after reset",
            "New T2 (ms). Cancel keeps the current value:",
            self.engine.config.t2,
            -1_000_000_000.0,
            1_000_000_000.0,
            3,
        )
        if accepted:
            self.engine.update_t2(value)

    def _send_message(self) -> None:
        if not self.engine.remote_ca_ids:
            QMessageBox.information(self, "No receiver", "No remote CA exists in topology.")
            return
        dialog = SendMessageDialog(self.engine.remote_ca_ids, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        receiver_id, latency, payload = dialog.values()
        try:
            self.engine.send_ca_message(receiver_id, latency, payload)
        except ValueError as exc:
            QMessageBox.critical(self, "Send failed", str(exc))

    def _show_integrity_dialog(
        self,
        message: DataMessage,
        trace: IntegrityTrace,
    ) -> None:
        dialog = IntegrityDialog(message, trace, self)
        offset = 30 * (len(self.integrity_dialogs) % 6)
        dialog.move(self.pos() + QPoint(self.width() + 20 + offset, offset))
        dialog.destroyed.connect(
            lambda _object=None, current=dialog: self._remove_dialog(current)
        )
        self.integrity_dialogs.append(dialog)
        dialog.show()
        dialog.raise_()

    def _remove_dialog(self, dialog: IntegrityDialog) -> None:
        if dialog in self.integrity_dialogs:
            self.integrity_dialogs.remove(dialog)

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
