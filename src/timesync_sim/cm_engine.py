from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Signal

from .constants import CYCLE_MS, REQUEST_NUMBER_MODULUS, RESPONSE_CUTOFF_MS
from .math_utils import calculate_relative_offset_error
from .models import (
    ClockOffsetEntry,
    ClockOffsetListMessage,
    CMNodeConfig,
    Endpoint,
    RequestMessage,
    ResponseMessage,
    TopologyConfig,
    TransportProbeMessage,
)
from .network import UdpTransport
from .protocol import ProtocolError, decode_message


@dataclass
class CMRequestRecord:
    cycle_index: int
    request_number: int
    completed: bool = False
    clock_offset_list: Optional[ClockOffsetListMessage] = None


class CMEngine(QObject):
    state_changed = Signal(object)
    log_message = Signal(str)
    fatal_error = Signal(str)

    def __init__(
        self,
        config: CMNodeConfig,
        topology: TopologyConfig,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.topology = topology
        self.local_endpoint = topology.endpoint_for(config.es_id)
        self.ca_endpoints: List[Endpoint] = sorted(
            topology.endpoints_by_role("CA"), key=lambda endpoint: endpoint.es_id
        )

        self.relative_offset_delays = {
            ca_id: parameters.relative_offset_delay
            for ca_id, parameters in topology.ca_parameters.items()
        }
        self.relative_offset_errors = {
            ca_id: calculate_relative_offset_error(
                parameters.clock_drift_rate,
                config.e1,
                parameters.l2,
            )
            for ca_id, parameters in topology.ca_parameters.items()
        }
        self.relative_offsets: Dict[int, Optional[float]] = {
            endpoint.es_id: None for endpoint in self.ca_endpoints
        }
        self.last_reset_counters: Dict[int, Optional[int]] = {
            endpoint.es_id: None for endpoint in self.ca_endpoints
        }

        self.transport = UdpTransport(self.local_endpoint, self)
        self.transport.datagram_received.connect(self._on_datagram)
        self.transport.error_occurred.connect(self.log_message.emit)

        self.elapsed = QElapsedTimer()
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(10)
        self.tick_timer.timeout.connect(self._on_tick)

        self.current_cycle = -1
        self.request_sent_for_cycle = False
        self.current_request_number: Optional[int] = None
        self.current_request_message: Optional[RequestMessage] = None
        self.current_clock_list_message: Optional[ClockOffsetListMessage] = None
        self.current_responses: Dict[int, ResponseMessage] = {}
        self.learned_ca_routes: Dict[int, tuple[str, int]] = {}
        # Per-CA probe reply throttling. A burst of probes can already be in flight
        # before the CA receives the first reply and reports updated sequence numbers.
        self.last_probe_reply_ms: Dict[int, int] = {}
        self.last_probe_reply_signature: Dict[
            int, tuple[Optional[int], Optional[int]]
        ] = {}
        self.records: List[CMRequestRecord] = []
        self.last_completed_list: Optional[ClockOffsetListMessage] = None
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.elapsed.start()
        self.tick_timer.start()
        self.log_message.emit(
            f"CM ES_ID={self.config.es_id} listening on UDP "
            f"0.0.0.0:{self.local_endpoint.port}; advertised as "
            f"{self.local_endpoint.ip}:{self.local_endpoint.port}"
        )
        self.log_message.emit(
            "Loaded CA destinations: "
            + ", ".join(
                f"CA {endpoint.es_id}={endpoint.ip}:{endpoint.port}"
                for endpoint in self.ca_endpoints
            )
        )
        self._on_tick()

    def stop(self) -> None:
        self.running = False
        self.tick_timer.stop()

    def _on_tick(self) -> None:
        if not self.running:
            return
        now_ms = self.elapsed.elapsed()
        target_cycle = now_ms // CYCLE_MS
        while self.current_cycle < target_cycle:
            if self.current_cycle >= 0:
                self._finalize_current_cycle()
            self.current_cycle += 1
            self.request_sent_for_cycle = False
            self.current_request_number = None
            self.current_request_message = None
            self.current_clock_list_message = None
            self.current_responses = {}

        phase_ms = now_ms % CYCLE_MS
        if not self.request_sent_for_cycle and phase_ms >= self.config.t1:
            self._send_cycle_messages()

        self.state_changed.emit(self.snapshot())

    def _send_cycle_messages(self) -> None:
        request_number = self.current_cycle % REQUEST_NUMBER_MODULUS
        request = RequestMessage(
            message_type="request",
            cm_es_id=self.config.es_id,
            request_number=request_number,
            t1=self.config.t1,
        )
        self.current_request_message = request
        self.current_clock_list_message = self.last_completed_list

        for endpoint in self.ca_endpoints:
            self.transport.send(request, endpoint)

        if self.last_completed_list is not None:
            for endpoint in self.ca_endpoints:
                self.transport.send(self.last_completed_list, endpoint)
            self.log_message.emit(
                f"Sent request {request_number} and clock_offset_list "
                f"{self.last_completed_list.request_number} to all CAs"
            )
        else:
            self.log_message.emit(
                f"Sent first request {request_number}; no previous clock_offset_list exists"
            )

        self.request_sent_for_cycle = True
        self.current_request_number = request_number
        self.records.append(
            CMRequestRecord(
                cycle_index=self.current_cycle,
                request_number=request_number,
            )
        )
        self.records = self.records[-2:]

    def _finalize_current_cycle(self) -> None:
        if not self.request_sent_for_cycle or self.current_request_number is None:
            return

        entries: List[ClockOffsetEntry] = []
        for endpoint in self.ca_endpoints:
            ca_id = endpoint.es_id
            response = self.current_responses.get(ca_id)
            if response is None:
                relative_offset = None
            else:
                relative_offset = response.t2 - response.t1
                self.last_reset_counters[ca_id] = response.reset_counter
            self.relative_offsets[ca_id] = relative_offset
            entries.append(
                ClockOffsetEntry(
                    ca_es_id=ca_id,
                    relative_offset=relative_offset,
                    reset_counter=self.last_reset_counters[ca_id],
                    relative_offset_error=self.relative_offset_errors[ca_id],
                )
            )

        clock_list = ClockOffsetListMessage(
            message_type="clock_offset_list",
            cm_es_id=self.config.es_id,
            request_number=self.current_request_number,
            number_of_ca=len(entries),
            entries=entries,
        )
        self.last_completed_list = clock_list
        for record in self.records:
            if (
                record.cycle_index == self.current_cycle
                and record.request_number == self.current_request_number
            ):
                record.completed = True
                record.clock_offset_list = clock_list
                break
        self.log_message.emit(
            f"Published clock_offset_list {self.current_request_number} at cycle boundary"
        )

    def _on_datagram(self, payload: bytes, sender_ip: str, sender_port: int) -> None:
        try:
            message = decode_message(payload)
        except ProtocolError as exc:
            self.log_message.emit(f"Discarded malformed datagram: {exc}")
            return

        if isinstance(message, TransportProbeMessage):
            self._handle_transport_probe(message, sender_ip, sender_port)
            return

        if not isinstance(message, ResponseMessage):
            return
        if message.cm_es_id != self.config.es_id:
            return
        known_ca_ids = {endpoint.es_id for endpoint in self.ca_endpoints}
        if message.ca_es_id not in known_ca_ids:
            self.log_message.emit(
                f"Discarded response from unknown CA ES_ID={message.ca_es_id}"
            )
            return
        if self.current_request_number is None:
            return
        if message.request_number != self.current_request_number:
            self.log_message.emit(
                f"Discarded response request_number={message.request_number}; "
                f"current request is {self.current_request_number}"
            )
            return

        phase_ms = self.elapsed.elapsed() % CYCLE_MS
        if phase_ms > RESPONSE_CUTOFF_MS:
            self.log_message.emit(
                f"Response from CA {message.ca_es_id} arrived at {phase_ms} ms and missed cutoff"
            )
            return

        self.current_responses[message.ca_es_id] = message
        self.log_message.emit(
            f"Accepted response {message.request_number} from CA {message.ca_es_id} "
            f"at phase {phase_ms} ms"
        )

    def _handle_transport_probe(
        self,
        message: TransportProbeMessage,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        if message.cm_es_id != self.config.es_id:
            return
        known_ca_ids = {endpoint.es_id for endpoint in self.ca_endpoints}
        if message.ca_es_id not in known_ca_ids:
            return

        route = (sender_ip, sender_port)
        previous_route = self.learned_ca_routes.get(message.ca_es_id)
        self.learned_ca_routes[message.ca_es_id] = route
        if previous_route != route:
            self.log_message.emit(
                f"Learned solicited UDP route for CA {message.ca_es_id}: "
                f"{sender_ip}:{sender_port}"
            )

        request_to_deliver = None
        if (
            self.current_request_message is not None
            and message.last_request_number
            != self.current_request_message.request_number
        ):
            request_to_deliver = self.current_request_message

        clock_list_to_deliver = None
        if (
            self.current_clock_list_message is not None
            and message.last_clock_list_request_number
            != self.current_clock_list_message.request_number
        ):
            clock_list_to_deliver = self.current_clock_list_message

        signature = (
            None if request_to_deliver is None else request_to_deliver.request_number,
            None
            if clock_list_to_deliver is None
            else clock_list_to_deliver.request_number,
        )
        if signature == (None, None):
            return

        # Several 5 ms probes may already be queued with stale acknowledgement
        # fields. Reply immediately once, then retry at most every 25 ms until a
        # later probe confirms receipt. This preserves packet-loss recovery while
        # preventing hundreds of duplicate sends and log lines per second.
        now_ms = self.elapsed.elapsed()
        if (
            self.last_probe_reply_signature.get(message.ca_es_id) == signature
            and now_ms - self.last_probe_reply_ms.get(message.ca_es_id, -10_000) < 40
        ):
            return

        delivered: List[str] = []
        if request_to_deliver is not None and self.transport.send_to(
            request_to_deliver,
            sender_ip,
            sender_port,
        ):
            delivered.append(f"request {request_to_deliver.request_number}")

        if clock_list_to_deliver is not None and self.transport.send_to(
            clock_list_to_deliver,
            sender_ip,
            sender_port,
        ):
            delivered.append(
                f"clock_offset_list {clock_list_to_deliver.request_number}"
            )

        if not delivered:
            return

        self.last_probe_reply_ms[message.ca_es_id] = now_ms
        self.last_probe_reply_signature[message.ca_es_id] = signature

        # Delivery is intentionally not logged per probe/cycle. The learned-route
        # line plus the CA's Received request line provide useful diagnostics
        # without flooding the CM runtime log.

    def snapshot(self) -> Dict[str, object]:
        phase_ms = self.elapsed.elapsed() % CYCLE_MS if self.elapsed.isValid() else 0
        return {
            "es_id": self.config.es_id,
            "phase_ms": phase_ms,
            "cycle_index": self.current_cycle,
            "records": list(self.records),
            "relative_offset_errors": dict(self.relative_offset_errors),
        }
