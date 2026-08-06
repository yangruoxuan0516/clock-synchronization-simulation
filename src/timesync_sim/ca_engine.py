from __future__ import annotations

import math
from functools import partial
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Qt, Signal

from .constants import (
    CM_UNAVAILABLE_MS,
    CYCLE_MS,
    LOCAL_CLOCK_OFFSET_EXPIRY_MS,
    RESET_COUNTER_MODULUS,
)
from .logic import (
    IntegrityTrace,
    choose_initial_cm,
    compute_local_offsets_from_list,
    evaluate_time_integrity,
    local_clock_offsets_are_stale,
)
from .models import (
    CANodeConfig,
    CAPeerAckMessage,
    CAPeerProbeMessage,
    ClockOffsetListMessage,
    DataMessage,
    Endpoint,
    RequestMessage,
    ResponseMessage,
    TopologyConfig,
    TransportProbeMessage,
)
from .network import UdpTransport
from .protocol import ProtocolError, decode_message


class CAEngine(QObject):
    state_changed = Signal(object)
    log_message = Signal(str)
    fatal_error = Signal(str)
    integrity_checked = Signal(object, object)

    def __init__(
        self,
        config: CANodeConfig,
        topology: TopologyConfig,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.topology = topology
        self.local_endpoint = topology.endpoint_for(config.es_id)
        self.cm_endpoints: Dict[int, Endpoint] = {
            endpoint.es_id: endpoint
            for endpoint in topology.endpoints_by_role("CM")
        }
        self.ca_endpoints: Dict[int, Endpoint] = {
            endpoint.es_id: endpoint
            for endpoint in topology.endpoints_by_role("CA")
        }
        self.remote_ca_ids = sorted(
            ca_id for ca_id in self.ca_endpoints if ca_id != config.es_id
        )
        self.relative_offset_delays: Dict[int, float] = {
            ca_id: parameters.relative_offset_delay
            for ca_id, parameters in topology.ca_parameters.items()
        }

        self.local_clock_offsets: Dict[int, Optional[float]] = {
            ca_id: None for ca_id in self.remote_ca_ids
        }
        self.last_local_clock_offset_update_ms: Optional[int] = None
        self.reset_counter = 0
        self.current_used_clock_list: Optional[ClockOffsetListMessage] = None

        self.selected_cm_es_id: Optional[int] = None
        self.selected_cm_since_ms: Optional[int] = None
        self.last_clock_list_ms: Dict[int, int] = {}
        self.latest_clock_lists: Dict[int, ClockOffsetListMessage] = {}
        self.last_request_timing: Dict[int, Tuple[int, float]] = {}
        self.last_received_request_numbers: Dict[int, int] = {}
        self.last_received_clock_list_numbers: Dict[int, int] = {}
        self.selected_cycle_anchor_ms: Optional[float] = None

        self.election_started = False
        self.election_finished = False
        self.election_first_cm: Optional[int] = None
        self.election_seen_cms: set[int] = set()
        self.election_timer = QTimer(self)
        self.election_timer.setSingleShot(True)
        self.election_timer.timeout.connect(self._finish_election)

        self.transport = UdpTransport(self.local_endpoint, self)
        self.transport.datagram_received.connect(self._on_datagram)
        self.transport.error_occurred.connect(self.log_message.emit)

        self.elapsed = QElapsedTimer()
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(20)
        self.tick_timer.timeout.connect(self._on_tick)

        self.local_offset_expiry_timer = QTimer(self)
        self.local_offset_expiry_timer.setSingleShot(True)
        self.local_offset_expiry_timer.setTimerType(Qt.PreciseTimer)
        self.local_offset_expiry_timer.timeout.connect(
            self._expire_stale_local_clock_offsets
        )

        # Some managed Windows systems only admit an immediate UDP response
        # to a locally initiated datagram.  Poll every few milliseconds from
        # the CA's bound socket; a CM can return its currently published
        # request/list directly to the observed source tuple.  Direct CM push
        # remains enabled, so unrestricted systems still receive at T1.
        self.transport_probe_timer = QTimer(self)
        self.transport_probe_timer.setTimerType(Qt.PreciseTimer)
        self.transport_probe_timer.setInterval(20)
        self.transport_probe_timer.timeout.connect(self._send_transport_probes)

        # Maintain a CA-to-CA UDP request/reply path as well.  This is separate
        # from the CM pull channel: restrictive Windows policies track each
        # source/destination port pair independently.
        self.peer_probe_timer = QTimer(self)
        self.peer_probe_timer.setInterval(500)
        self.peer_probe_timer.timeout.connect(self._send_ca_peer_probes)
        self.peer_routes: Dict[int, Tuple[str, int]] = {}
        self.peer_route_last_seen_ms: Dict[int, int] = {}
        self.pending_peer_messages: Dict[int, List[DataMessage]] = {
            ca_id: [] for ca_id in self.remote_ca_ids
        }
        self.peer_route_logged: set[int] = set()

        self.response_timers: List[QTimer] = []
        self.apply_timers: List[QTimer] = []
        self.reset_generation = 0
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.elapsed.start()
        self.tick_timer.start()
        if self.config.probe_enabled:
            self.transport_probe_timer.start()
            self.peer_probe_timer.start()
        self.log_message.emit(
            f"CA ES_ID={self.config.es_id} listening on UDP "
            f"0.0.0.0:{self.local_endpoint.port}; advertised as "
            f"{self.local_endpoint.ip}:{self.local_endpoint.port}"
        )
        self.log_message.emit(
            "Loaded CM endpoints: "
            + ", ".join(
                f"CM {endpoint.es_id}={endpoint.ip}:{endpoint.port}"
                for endpoint in sorted(
                    self.cm_endpoints.values(), key=lambda item: item.es_id
                )
            )
        )
        self.log_message.emit(
            "Simulation UDP probes: "
            + ("enabled" if self.config.probe_enabled else "disabled")
        )
        if self.config.probe_enabled:
            self._send_transport_probes()
            self._send_ca_peer_probes()
        self._on_tick()

    def stop(self) -> None:
        self.running = False
        self.tick_timer.stop()
        self.transport_probe_timer.stop()
        self.peer_probe_timer.stop()
        self.local_offset_expiry_timer.stop()
        self._cancel_timers(self.response_timers)
        self._cancel_timers(self.apply_timers)

    def update_t2(self, new_t2: float) -> None:
        self.config.t2 = new_t2
        self.log_message.emit(f"T2 changed to {new_t2} ms")
        self.state_changed.emit(self.snapshot())

    def reset(self, new_t2: Optional[float] = None) -> None:
        self.reset_counter = (self.reset_counter + 1) % RESET_COUNTER_MODULUS
        self.local_clock_offsets = {ca_id: None for ca_id in self.remote_ca_ids}
        self.last_local_clock_offset_update_ms = None
        self.local_offset_expiry_timer.stop()
        self.current_used_clock_list = None
        self.reset_generation += 1
        self._cancel_timers(self.response_timers)
        self._cancel_timers(self.apply_timers)
        for queued in self.pending_peer_messages.values():
            queued.clear()
        if new_t2 is not None:
            self.config.t2 = new_t2
        self.log_message.emit(
            f"Reset completed: reset_counter={self.reset_counter}, T2={self.config.t2}"
        )
        self.state_changed.emit(self.snapshot())

    def send_ca_message(
        self,
        receiver_ca_es_id: int,
        transmission_latency: int,
        payload: str = "CA communication test message",
    ) -> None:
        endpoint = self.ca_endpoints.get(receiver_ca_es_id)
        if endpoint is None or receiver_ca_es_id == self.config.es_id:
            raise ValueError(f"Invalid receiver CA ES_ID: {receiver_ca_es_id}")
        message = DataMessage(
            message_type="ca_data",
            sender_ca_es_id=self.config.es_id,
            receiver_ca_es_id=receiver_ca_es_id,
            reset_counter=self.reset_counter,
            transmission_latency=transmission_latency,
            payload=payload,
        )
        route = self._fresh_peer_route(receiver_ca_es_id)
        if route is not None:
            self.transport.send_to(message, route[0], route[1])
            self.log_message.emit(
                f"Sent CA message to {receiver_ca_es_id} with transmission_latency="
                f"{transmission_latency} ms"
            )
            return

        if not self.config.probe_enabled:
            # Original simulation behavior: perform one direct UDP send using
            # the endpoint declared in topology.json. No transport-only probe,
            # ACK, queueing, or retry is introduced by this CA.
            self.transport.send(message, endpoint)
            self.log_message.emit(
                f"Sent CA message directly to {receiver_ca_es_id} with "
                f"transmission_latency={transmission_latency} ms "
                "(probe_enabled=false)"
            )
            return

        # Compatibility mode: do not sacrifice the user's first data message
        # merely to open a UDP path. Queue it, initiate the transport handshake,
        # and send it as soon as either a probe or ACK reveals a usable route.
        # Reset clears this queue, matching the requirement to cancel unsent
        # messages.
        self.pending_peer_messages[receiver_ca_es_id].append(message)
        self._send_ca_peer_probe(receiver_ca_es_id)
        self.log_message.emit(
            f"Queued CA message to {receiver_ca_es_id}; waiting for UDP peer handshake"
        )

    def _send_transport_probes(self) -> None:
        for cm_es_id, endpoint in self.cm_endpoints.items():
            probe = TransportProbeMessage(
                message_type="transport_probe",
                ca_es_id=self.config.es_id,
                cm_es_id=cm_es_id,
                last_request_number=self.last_received_request_numbers.get(cm_es_id),
                last_clock_list_request_number=(
                    self.last_received_clock_list_numbers.get(cm_es_id)
                ),
            )
            self.transport.send(probe, endpoint)

    def _send_ca_peer_probes(self) -> None:
        for ca_es_id in self.remote_ca_ids:
            self._send_ca_peer_probe(ca_es_id)

    def _send_ca_peer_probe(self, receiver_ca_es_id: int) -> None:
        endpoint = self.ca_endpoints[receiver_ca_es_id]
        probe = CAPeerProbeMessage(
            message_type="ca_peer_probe",
            sender_ca_es_id=self.config.es_id,
            receiver_ca_es_id=receiver_ca_es_id,
        )
        self.transport.send(probe, endpoint)

    def _fresh_peer_route(self, ca_es_id: int) -> Optional[Tuple[str, int]]:
        route = self.peer_routes.get(ca_es_id)
        seen_ms = self.peer_route_last_seen_ms.get(ca_es_id)
        if route is None or seen_ms is None:
            return None
        if self.elapsed.elapsed() - seen_ms >= 1500:
            return None
        return route

    def _record_peer_route(
        self,
        ca_es_id: int,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        self.peer_routes[ca_es_id] = (sender_ip, sender_port)
        self.peer_route_last_seen_ms[ca_es_id] = self.elapsed.elapsed()
        if ca_es_id not in self.peer_route_logged:
            self.peer_route_logged.add(ca_es_id)
            self.log_message.emit(
                f"CA peer UDP path ready: CA {ca_es_id} at {sender_ip}:{sender_port}"
            )
        self._flush_pending_peer_messages(ca_es_id)

    def _flush_pending_peer_messages(self, ca_es_id: int) -> None:
        route = self._fresh_peer_route(ca_es_id)
        if route is None:
            return
        queued = self.pending_peer_messages.get(ca_es_id, [])
        while queued:
            message = queued.pop(0)
            self.transport.send_to(message, route[0], route[1])
            self.log_message.emit(
                f"Sent queued CA message to {ca_es_id} with transmission_latency="
                f"{message.transmission_latency} ms"
            )

    def _handle_ca_peer_probe(
        self,
        message: CAPeerProbeMessage,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        if message.receiver_ca_es_id != self.config.es_id:
            return
        if message.sender_ca_es_id not in self.remote_ca_ids:
            return
        self._record_peer_route(message.sender_ca_es_id, sender_ip, sender_port)
        ack = CAPeerAckMessage(
            message_type="ca_peer_ack",
            sender_ca_es_id=self.config.es_id,
            receiver_ca_es_id=message.sender_ca_es_id,
        )
        self.transport.send_to(ack, sender_ip, sender_port)

    def _handle_ca_peer_ack(
        self,
        message: CAPeerAckMessage,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        if message.receiver_ca_es_id != self.config.es_id:
            return
        if message.sender_ca_es_id not in self.remote_ca_ids:
            return
        self._record_peer_route(message.sender_ca_es_id, sender_ip, sender_port)

    def _on_tick(self) -> None:
        if not self.running:
            return
        self._check_selected_cm_availability()
        self.state_changed.emit(self.snapshot())

    def _on_datagram(self, payload: bytes, sender_ip: str, sender_port: int) -> None:
        try:
            message = decode_message(payload)
        except ProtocolError as exc:
            self.log_message.emit(f"Discarded malformed datagram: {exc}")
            return

        if isinstance(message, RequestMessage):
            self._handle_request(message)
        elif isinstance(message, ClockOffsetListMessage):
            self._handle_clock_offset_list(message)
        elif isinstance(message, CAPeerProbeMessage):
            self._handle_ca_peer_probe(message, sender_ip, sender_port)
        elif isinstance(message, CAPeerAckMessage):
            self._handle_ca_peer_ack(message, sender_ip, sender_port)
        elif isinstance(message, DataMessage):
            self._handle_data_message(message, sender_ip, sender_port)

    def _handle_request(self, message: RequestMessage) -> None:
        endpoint = self.cm_endpoints.get(message.cm_es_id)
        if endpoint is None:
            self.log_message.emit(
                f"Discarded request from unknown CM ES_ID={message.cm_es_id}"
            )
            return

        if self.last_received_request_numbers.get(message.cm_es_id) == message.request_number:
            return
        self.last_received_request_numbers[message.cm_es_id] = message.request_number

        now_ms = self.elapsed.elapsed()
        self.last_request_timing[message.cm_es_id] = (now_ms, message.t1)

        if not self.election_started:
            self.election_started = True
            self.election_first_cm = message.cm_es_id
            self.election_seen_cms = {message.cm_es_id}
            window_ms = max(0, int(math.ceil(self.config.t2 - message.t1)))
            self.election_timer.start(window_ms)
            self.log_message.emit(
                f"Election window started from CM {message.cm_es_id}; length={window_ms} ms"
            )
        elif not self.election_finished:
            self.election_seen_cms.add(message.cm_es_id)

        if self.selected_cm_es_id == message.cm_es_id:
            self.selected_cycle_anchor_ms = now_ms - message.t1

        delay_ms = max(0, int(math.ceil(self.config.t2 - message.t1)))
        response_timer = QTimer(self)
        response_timer.setSingleShot(True)
        response_timer.timeout.connect(
            partial(self._send_response, message, endpoint, response_timer)
        )
        self.response_timers.append(response_timer)
        response_timer.start(delay_ms)
        self.log_message.emit(
            f"Received request {message.request_number} from CM {message.cm_es_id}; "
            f"response scheduled after {delay_ms} ms"
        )

    def _send_response(
        self,
        request: RequestMessage,
        endpoint: Endpoint,
        timer: QTimer,
    ) -> None:
        self._remove_timer(self.response_timers, timer)
        response = ResponseMessage(
            message_type="response",
            cm_es_id=request.cm_es_id,
            ca_es_id=self.config.es_id,
            request_number=request.request_number,
            t1=request.t1,
            t2=self.config.t2,
            reset_counter=self.reset_counter,
        )
        self.transport.send(response, endpoint)
        self.log_message.emit(
            f"Sent response {request.request_number} to CM {request.cm_es_id}"
        )

    def _finish_election(self) -> None:
        if self.election_finished or self.election_first_cm is None:
            return
        selected = choose_initial_cm(
            self.election_first_cm,
            self.election_seen_cms,
        )
        self.election_finished = True
        self._switch_selected_cm(selected, "initial election")

    def _handle_clock_offset_list(self, message: ClockOffsetListMessage) -> None:
        if message.cm_es_id not in self.cm_endpoints:
            self.log_message.emit(
                f"Discarded clock_offset_list from unknown CM {message.cm_es_id}"
            )
            return
        expected_ca_ids = set(self.ca_endpoints.keys())
        message_ca_ids = {entry.ca_es_id for entry in message.entries}
        if message_ca_ids != expected_ca_ids:
            self.log_message.emit(
                f"Discarded structurally invalid clock_offset_list {message.request_number}: "
                "CA ES_ID set does not match topology"
            )
            return

        if (
            self.last_received_clock_list_numbers.get(message.cm_es_id)
            == message.request_number
        ):
            return
        self.last_received_clock_list_numbers[message.cm_es_id] = message.request_number

        now_ms = self.elapsed.elapsed()
        self.last_clock_list_ms[message.cm_es_id] = now_ms
        self.latest_clock_lists[message.cm_es_id] = message

        if message.cm_es_id != self.selected_cm_es_id:
            self.log_message.emit(
                f"Stored clock_offset_list {message.request_number} from non-selected "
                f"CM {message.cm_es_id}"
            )
            return

        self._schedule_selected_clock_list(message)

    def _schedule_selected_clock_list(self, message: ClockOffsetListMessage) -> None:
        local_entry = message.entry_for(self.config.es_id)
        if local_entry is None or local_entry.reset_counter != self.reset_counter:
            self.log_message.emit(
                f"Rejected clock_offset_list {message.request_number}: local reset_counter "
                f"{self.reset_counter} != list value "
                f"{None if local_entry is None else local_entry.reset_counter}"
            )
            return

        computed_offsets = compute_local_offsets_from_list(
            message,
            self.config.es_id,
            self.relative_offset_delays,
        )
        generation = self.reset_generation
        selected_cm = self.selected_cm_es_id
        delay_to_boundary = self._delay_to_next_selected_cycle_boundary()
        apply_timer = QTimer(self)
        apply_timer.setSingleShot(True)
        apply_timer.timeout.connect(
            partial(
                self._apply_clock_list,
                message,
                computed_offsets,
                generation,
                selected_cm,
                apply_timer,
            )
        )
        self.apply_timers.append(apply_timer)
        apply_timer.start(delay_to_boundary)
        self.log_message.emit(
            f"Accepted clock_offset_list {message.request_number}; local offsets will "
            f"become effective after {delay_to_boundary} ms"
        )

    def _apply_clock_list(
        self,
        message: ClockOffsetListMessage,
        computed_offsets: Dict[int, Optional[float]],
        generation: int,
        selected_cm: Optional[int],
        timer: QTimer,
    ) -> None:
        self._remove_timer(self.apply_timers, timer)
        if generation != self.reset_generation:
            return
        if selected_cm != self.selected_cm_es_id:
            return
        self.local_clock_offsets = dict(computed_offsets)
        self.last_local_clock_offset_update_ms = self.elapsed.elapsed()
        self.local_offset_expiry_timer.start(LOCAL_CLOCK_OFFSET_EXPIRY_MS + 1)
        self.current_used_clock_list = message
        self.log_message.emit(
            f"local_clock_offset from CM {message.cm_es_id}, list "
            f"{message.request_number}, is now effective"
        )
        self.state_changed.emit(self.snapshot())

    def _expire_stale_local_clock_offsets(self) -> None:
        now_ms = self.elapsed.elapsed()
        if not local_clock_offsets_are_stale(
            self.last_local_clock_offset_update_ms,
            now_ms,
        ):
            if self.last_local_clock_offset_update_ms is not None:
                age_ms = now_ms - self.last_local_clock_offset_update_ms
                remaining_ms = max(
                    1,
                    LOCAL_CLOCK_OFFSET_EXPIRY_MS + 1 - age_ms,
                )
                self.local_offset_expiry_timer.start(remaining_ms)
            return

        had_known_value = any(
            value is not None for value in self.local_clock_offsets.values()
        )
        self.local_clock_offsets = {ca_id: None for ca_id in self.remote_ca_ids}
        self.last_local_clock_offset_update_ms = None
        if had_known_value:
            self.log_message.emit(
                "local_clock_offset expired after more than 1000 ms without "
                "an effective update; all entries set to Unknown"
            )
            self.state_changed.emit(self.snapshot())

    def _handle_data_message(
        self,
        message: DataMessage,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        if message.receiver_ca_es_id != self.config.es_id:
            return
        if message.sender_ca_es_id not in self.remote_ca_ids:
            self.log_message.emit(
                f"Discarded CA data from unknown/non-remote CA {message.sender_ca_es_id}"
            )
            return

        self._record_peer_route(
            message.sender_ca_es_id,
            sender_ip,
            sender_port,
        )
        local_offset = self.local_clock_offsets.get(message.sender_ca_es_id)
        list_counter: Optional[int] = None
        if self.current_used_clock_list is not None:
            sender_entry = self.current_used_clock_list.entry_for(message.sender_ca_es_id)
            if sender_entry is not None:
                list_counter = sender_entry.reset_counter

        trace = evaluate_time_integrity(
            dmax=self.config.dmax,
            local_clock_offset=local_offset,
            message_reset_counter=message.reset_counter,
            list_reset_counter=list_counter,
            transmission_latency=message.transmission_latency,
        )
        self.log_message.emit(
            f"CA message from {message.sender_ca_es_id}: "
            f"{'PASS' if trace.accepted else 'DISCARD'} ({trace.reason})"
        )
        self.integrity_checked.emit(message, trace)

    def _check_selected_cm_availability(self) -> None:
        if not self.election_finished or self.selected_cm_es_id is None:
            return
        now_ms = self.elapsed.elapsed()
        last_list = self.last_clock_list_ms.get(self.selected_cm_es_id)
        reference = last_list
        if reference is None:
            reference = self.selected_cm_since_ms
        if reference is None or now_ms - reference < CM_UNAVAILABLE_MS:
            return

        available = sorted(
            cm_id
            for cm_id, timestamp in self.last_clock_list_ms.items()
            if now_ms - timestamp < CM_UNAVAILABLE_MS
        )
        if available:
            candidate = available[0]
            if candidate != self.selected_cm_es_id:
                self._switch_selected_cm(candidate, "current CM unavailable")

    def _switch_selected_cm(self, cm_es_id: int, reason: str) -> None:
        if cm_es_id == self.selected_cm_es_id:
            return
        self.selected_cm_es_id = cm_es_id
        self.selected_cm_since_ms = self.elapsed.elapsed()
        timing = self.last_request_timing.get(cm_es_id)
        if timing is not None:
            received_ms, t1 = timing
            self.selected_cycle_anchor_ms = received_ms - t1
        else:
            self.selected_cycle_anchor_ms = None

        self.local_clock_offsets = {ca_id: None for ca_id in self.remote_ca_ids}
        self.last_local_clock_offset_update_ms = None
        self.local_offset_expiry_timer.stop()
        self.current_used_clock_list = None
        self._cancel_timers(self.apply_timers)
        self.log_message.emit(f"Selected CM changed to {cm_es_id}: {reason}")

        cached = self.latest_clock_lists.get(cm_es_id)
        if cached is not None:
            self._schedule_selected_clock_list(cached)

    def _delay_to_next_selected_cycle_boundary(self) -> int:
        if self.selected_cycle_anchor_ms is None:
            return CYCLE_MS
        now_ms = self.elapsed.elapsed()
        phase = (now_ms - self.selected_cycle_anchor_ms) % CYCLE_MS
        delay = CYCLE_MS - phase
        return max(1, int(math.ceil(delay)))

    def _display_phase_ms(self) -> int:
        if self.selected_cycle_anchor_ms is None:
            return self.elapsed.elapsed() % CYCLE_MS if self.elapsed.isValid() else 0
        return int((self.elapsed.elapsed() - self.selected_cycle_anchor_ms) % CYCLE_MS)

    def snapshot(self) -> Dict[str, object]:
        return {
            "es_id": self.config.es_id,
            "phase_ms": self._display_phase_ms(),
            "selected_cm_es_id": self.selected_cm_es_id,
            "source_request_number": (
                None
                if self.current_used_clock_list is None
                else self.current_used_clock_list.request_number
            ),
            "local_clock_offsets": dict(self.local_clock_offsets),
            "reset_counter": self.reset_counter,
            "t2": self.config.t2,
            "dmax": self.config.dmax,
            "election_finished": self.election_finished,
        }

    @staticmethod
    def _remove_timer(timers: List[QTimer], timer: QTimer) -> None:
        if timer in timers:
            timers.remove(timer)
        timer.deleteLater()

    @staticmethod
    def _cancel_timers(timers: List[QTimer]) -> None:
        for timer in list(timers):
            timer.stop()
            timer.deleteLater()
        timers.clear()
