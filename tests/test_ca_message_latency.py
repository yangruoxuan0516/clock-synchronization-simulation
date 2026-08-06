from __future__ import annotations

from typing import List, Tuple

from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, QTimer, Signal

import timesync_sim.ca_engine as ca_engine_module
from timesync_sim.ca_engine import CAEngine
from timesync_sim.models import (
    CAParameters,
    CANodeConfig,
    ClockOffsetEntry,
    ClockOffsetListMessage,
    DataMessage,
    Endpoint,
    TopologyConfig,
)


class FakeTransport(QObject):
    datagram_received = Signal(bytes, str, int)
    error_occurred = Signal(str)

    def __init__(self, local_endpoint: Endpoint, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.local_endpoint = local_endpoint
        self.sent: List[Tuple[object, Endpoint]] = []
        self.sent_to: List[Tuple[object, str, int]] = []

    def send(self, message: object, destination: Endpoint) -> bool:
        self.sent.append((message, destination))
        return True

    def send_to(self, message: object, destination_ip: str, destination_port: int) -> bool:
        self.sent_to.append((message, destination_ip, destination_port))
        return True


def _application() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


def _wait(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def _topology() -> TopologyConfig:
    return TopologyConfig(
        endpoints=[
            Endpoint(es_id=101, name="CA101", role="CA", ip="127.0.0.1", port=30101),
            Endpoint(es_id=102, name="CA102", role="CA", ip="127.0.0.1", port=30102),
        ],
        ca_parameters={
            101: CAParameters(l2=0.0, clock_drift_rate=0.0, relative_offset_delay=0.0),
            102: CAParameters(l2=0.0, clock_drift_rate=0.0, relative_offset_delay=0.0),
        },
    )


def _engine(monkeypatch: object, es_id: int, probe_enabled: bool = False) -> CAEngine:
    _application()
    monkeypatch.setattr(ca_engine_module, "UdpTransport", FakeTransport)  # type: ignore[attr-defined]
    return CAEngine(
        CANodeConfig(
            role="CA",
            es_id=es_id,
            t2=200.0,
            dmax=100.0,
            topology_path="unused.json",
            probe_enabled=probe_enabled,
        ),
        _topology(),
    )


def _clock_list(sender_reset_counter: int) -> ClockOffsetListMessage:
    return ClockOffsetListMessage(
        message_type="clock_offset_list",
        cm_es_id=1,
        request_number=1,
        number_of_ca=2,
        entries=[
            ClockOffsetEntry(
                ca_es_id=101,
                relative_offset=10.0,
                reset_counter=sender_reset_counter,
                relative_offset_error=0.0,
            ),
            ClockOffsetEntry(
                ca_es_id=102,
                relative_offset=0.0,
                reset_counter=0,
                relative_offset_error=0.0,
            ),
        ],
    )


def test_receiver_reset_keeps_in_flight_message_and_delivery_uses_latest_state(
    monkeypatch: object,
) -> None:
    engine = _engine(monkeypatch, es_id=102)
    delivered: list[tuple[DataMessage, object]] = []
    engine.integrity_checked.connect(lambda message, trace: delivered.append((message, trace)))

    engine.local_clock_offsets[101] = 5.0
    engine.current_used_clock_list = _clock_list(sender_reset_counter=7)
    message = DataMessage(
        message_type="ca_data",
        sender_ca_es_id=101,
        receiver_ca_es_id=102,
        reset_counter=7,
        transmission_latency=40,
        payload="survives reset",
    )

    engine._schedule_data_message_delivery(message, "127.0.0.1", 30101)
    _wait(5)
    assert delivered == []
    assert len(engine.data_delivery_timers) == 1

    engine.reset()
    assert len(engine.data_delivery_timers) == 1

    # Model a new receiver state becoming effective before simulated arrival.
    engine.local_clock_offsets[101] = 5.0
    engine.current_used_clock_list = _clock_list(sender_reset_counter=8)

    _wait(70)
    assert len(delivered) == 1
    delivered_message, trace = delivered[0]
    assert delivered_message == message
    assert not trace.accepted
    assert trace.reason == "reset_counter mismatch or unavailable"
    assert engine.data_delivery_timers == []
    engine.stop()


def test_multiple_received_messages_have_independent_delivery_timers(
    monkeypatch: object,
) -> None:
    engine = _engine(monkeypatch, es_id=102)
    delivery_order: list[str] = []
    engine.integrity_checked.connect(
        lambda message, _trace: delivery_order.append(message.payload)
    )

    slow = DataMessage(
        message_type="ca_data",
        sender_ca_es_id=101,
        receiver_ca_es_id=102,
        reset_counter=0,
        transmission_latency=80,
        payload="slow",
    )
    fast = DataMessage(
        message_type="ca_data",
        sender_ca_es_id=101,
        receiver_ca_es_id=102,
        reset_counter=0,
        transmission_latency=10,
        payload="fast",
    )

    engine._schedule_data_message_delivery(slow, "127.0.0.1", 30101)
    engine._schedule_data_message_delivery(fast, "127.0.0.1", 30101)

    _wait(35)
    assert delivery_order == ["fast"]
    _wait(80)
    assert delivery_order == ["fast", "slow"]
    engine.stop()


def test_probe_pending_message_survives_sender_reset_with_click_time_snapshot(
    monkeypatch: object,
) -> None:
    engine = _engine(monkeypatch, es_id=101, probe_enabled=True)
    engine.elapsed.start()

    engine.send_ca_message(102, 25, "queued before reset")
    queued = engine.pending_peer_messages[102]
    assert len(queued) == 1
    assert queued[0].reset_counter == 0

    engine.reset()
    assert engine.reset_counter == 1
    assert len(queued) == 1
    assert queued[0].reset_counter == 0

    engine._record_peer_route(102, "127.0.0.1", 30102)
    transport = engine.transport
    sent_data = [item[0] for item in transport.sent_to if isinstance(item[0], DataMessage)]  # type: ignore[attr-defined]
    assert len(sent_data) == 1
    assert sent_data[0].reset_counter == 0
    assert sent_data[0].transmission_latency == 25
    assert sent_data[0].payload == "queued before reset"
    assert engine.pending_peer_messages[102] == []
    engine.stop()
