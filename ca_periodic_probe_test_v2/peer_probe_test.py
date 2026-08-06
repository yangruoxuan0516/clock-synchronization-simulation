#!/usr/bin/env python3
"""
Two-computer UDP peer probe test.

Purpose:
Compare these behaviors:
1) until_ack: send probe packets until the peer is discovered, then stop probing.
2) periodic: keep sending probe packets forever.

The program uses only the Python standard library and works on Windows/macOS/Linux.
"""

from __future__ import annotations

import argparse
import csv
import json
import queue
import socket
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


PROTOCOL_VERSION = 1
VALID_PROBE_MODES = {"off", "once", "until_ack", "periodic"}
MAX_DATAGRAM_SIZE = 65507


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def monotonic_ms() -> int:
    return time.monotonic_ns() // 1_000_000


def compact_json(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class Config:
    node_id: str
    bind_ip: str
    bind_port: int
    peer_id: str
    peer_ip: str
    peer_port: int
    probe_mode: str
    probe_interval_ms: int
    route_ttl_ms: Optional[int]
    data_ack_timeout_ms: int
    auto_start_tests: bool
    auto_test_sender: bool
    auto_idle_tests_sec: Tuple[float, ...]
    auto_test_repetitions: int
    log_file: str

    @staticmethod
    def load(path: Path) -> "Config":
        raw = json.loads(path.read_text(encoding="utf-8"))

        required = [
            "node_id", "bind_ip", "bind_port",
            "peer_id", "peer_ip", "peer_port",
            "probe_mode",
        ]
        missing = [key for key in required if key not in raw]
        if missing:
            raise ValueError(f"Missing config fields: {', '.join(missing)}")

        peer_ip = str(raw["peer_ip"]).strip()
        if not peer_ip or "CHANGE_TO_" in peer_ip:
            raise ValueError(
                "peer_ip is still a placeholder. Replace it with the other computer's LAN IP."
            )

        probe_mode = str(raw["probe_mode"]).strip().lower()
        if probe_mode not in VALID_PROBE_MODES:
            raise ValueError(
                f"probe_mode must be one of {sorted(VALID_PROBE_MODES)}, got {probe_mode!r}"
            )

        ttl_raw = raw.get("route_ttl_ms", None)
        route_ttl_ms = None if ttl_raw is None else int(ttl_raw)
        if route_ttl_ms is not None and route_ttl_ms <= 0:
            raise ValueError("route_ttl_ms must be null or a positive integer")

        idle_tests = tuple(float(x) for x in raw.get("auto_idle_tests_sec", [5, 30, 60]))
        if any(x < 0 for x in idle_tests):
            raise ValueError("auto_idle_tests_sec cannot contain negative values")

        cfg = Config(
            node_id=str(raw["node_id"]),
            bind_ip=str(raw["bind_ip"]),
            bind_port=int(raw["bind_port"]),
            peer_id=str(raw["peer_id"]),
            peer_ip=peer_ip,
            peer_port=int(raw["peer_port"]),
            probe_mode=probe_mode,
            probe_interval_ms=int(raw.get("probe_interval_ms", 500)),
            route_ttl_ms=route_ttl_ms,
            data_ack_timeout_ms=int(raw.get("data_ack_timeout_ms", 3000)),
            auto_start_tests=bool(raw.get("auto_start_tests", False)),
            auto_test_sender=bool(raw.get("auto_test_sender", False)),
            auto_idle_tests_sec=idle_tests,
            auto_test_repetitions=int(raw.get("auto_test_repetitions", 1)),
            log_file=str(raw.get("log_file", f"peer_probe_{raw['node_id']}.csv")),
        )

        if not (1 <= cfg.bind_port <= 65535 and 1 <= cfg.peer_port <= 65535):
            raise ValueError("bind_port and peer_port must be in 1..65535")
        if cfg.probe_interval_ms < 50:
            raise ValueError("probe_interval_ms must be at least 50 ms")
        if cfg.data_ack_timeout_ms < 100:
            raise ValueError("data_ack_timeout_ms must be at least 100 ms")
        if cfg.auto_test_repetitions < 1:
            raise ValueError("auto_test_repetitions must be at least 1")

        return cfg


class CsvEventLog:
    FIELDNAMES = [
        "wall_time",
        "monotonic_ms",
        "node_id",
        "event",
        "packet_type",
        "seq",
        "remote_ip",
        "remote_port",
        "details_json",
    ]

    def __init__(self, path: Path, node_id: str):
        self.path = path
        self.node_id = node_id
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        new_file = not self.path.exists() or self.path.stat().st_size == 0
        self._file = self.path.open("a", encoding="utf-8", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=self.FIELDNAMES)
        if new_file:
            self._writer.writeheader()
            self._file.flush()

    def write(
        self,
        event: str,
        packet_type: str = "",
        seq: Optional[int] = None,
        remote: Optional[Tuple[str, int]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        row = {
            "wall_time": iso_now(),
            "monotonic_ms": monotonic_ms(),
            "node_id": self.node_id,
            "event": event,
            "packet_type": packet_type,
            "seq": "" if seq is None else seq,
            "remote_ip": "" if remote is None else remote[0],
            "remote_port": "" if remote is None else remote[1],
            "details_json": json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
        }
        with self._lock:
            self._writer.writerow(row)
            self._file.flush()

    def close(self) -> None:
        with self._lock:
            self._file.flush()
            self._file.close()


class PeerProbeTester:
    def __init__(self, config: Config, config_path: Path):
        self.cfg = config
        self.config_path = config_path

        log_path = Path(config.log_file)
        if not log_path.is_absolute():
            log_path = config_path.parent / log_path
        self.log = CsvEventLog(log_path, config.node_id)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Deliberately do not enable SO_REUSEADDR. A second test process must
        # fail to bind instead of silently sharing the same UDP port.
        self.sock.bind((config.bind_ip, config.bind_port))
        self.sock.settimeout(0.5)

        self.stop_event = threading.Event()
        self.state_lock = threading.RLock()
        self.print_lock = threading.Lock()

        self.learned_route: Optional[Tuple[str, int]] = None
        self.route_last_seen_ns: Optional[int] = None
        self.peer_ready = False

        self.probe_seq = 0
        self.data_seq = 0
        self.probes_sent = 0
        self.probes_received = 0
        self.probe_acks_sent = 0
        self.probe_acks_received = 0
        self.data_sent = 0
        self.data_received = 0
        self.data_acks_sent = 0
        self.data_acks_received = 0

        self.last_probe_tx_ns: Optional[int] = None
        self.last_probe_rx_ns: Optional[int] = None
        self.last_any_peer_packet_ns: Optional[int] = None

        self.pending_data: Dict[int, Dict[str, Any]] = {}
        self.command_queue: "queue.Queue[str]" = queue.Queue()
        self.peer_mode_mismatch: Optional[str] = None
        self._reported_peer_mode_mismatch = False

        self.receiver_thread = threading.Thread(
            target=self._receiver_loop, name="udp-receiver", daemon=True
        )
        self.probe_thread = threading.Thread(
            target=self._probe_loop, name="probe-loop", daemon=True
        )
        self.command_thread = threading.Thread(
            target=self._command_loop, name="command-loop", daemon=True
        )
        self.auto_thread: Optional[threading.Thread] = None

    def console(self, message: str) -> None:
        with self.print_lock:
            print(f"[{iso_now()}] [{self.cfg.node_id}] {message}", flush=True)

    def start(self) -> None:
        self.log.write(
            "program_start",
            details={
                "config_path": str(self.config_path),
                "probe_mode": self.cfg.probe_mode,
                "probe_interval_ms": self.cfg.probe_interval_ms,
                "route_ttl_ms": self.cfg.route_ttl_ms,
                "bind": [self.cfg.bind_ip, self.cfg.bind_port],
                "configured_peer": [self.cfg.peer_ip, self.cfg.peer_port],
            },
        )
        self.console(
            f"Listening on {self.cfg.bind_ip}:{self.cfg.bind_port}; "
            f"peer={self.cfg.peer_ip}:{self.cfg.peer_port}; "
            f"probe_mode={self.cfg.probe_mode}"
        )
        self.console("Commands: status | probe | send <text> | auto | help | quit")

        self.receiver_thread.start()
        self.probe_thread.start()
        self.command_thread.start()

        if self.cfg.auto_start_tests and self.cfg.auto_test_sender:
            self.start_auto_tests()

    def wait(self) -> None:
        try:
            while not self.stop_event.wait(0.25):
                pass
        except KeyboardInterrupt:
            self.console("Keyboard interrupt received.")
            self.stop()
        finally:
            self._shutdown()

    def stop(self) -> None:
        self.stop_event.set()

    def _shutdown(self) -> None:
        self.stop_event.set()
        try:
            self.sock.close()
        except OSError:
            pass

        with self.state_lock:
            for pending in self.pending_data.values():
                pending["event"].set()

        self.log.write("program_stop", details=self.status_snapshot())
        self.log.close()
        self.console("Stopped.")

    def _route_is_fresh_locked(self) -> bool:
        if self.learned_route is None or self.route_last_seen_ns is None:
            return False
        if self.cfg.route_ttl_ms is None:
            return True
        age_ms = (time.monotonic_ns() - self.route_last_seen_ns) / 1_000_000
        return age_ms < self.cfg.route_ttl_ms

    def _effective_target_locked(self) -> Tuple[str, int]:
        if self._route_is_fresh_locked() and self.learned_route is not None:
            return self.learned_route
        return (self.cfg.peer_ip, self.cfg.peer_port)

    def _mark_peer_seen(self, addr: Tuple[str, int], source: str) -> None:
        now_ns = time.monotonic_ns()
        with self.state_lock:
            was_ready = self.peer_ready and self._route_is_fresh_locked()
            self.learned_route = (addr[0], addr[1])
            self.route_last_seen_ns = now_ns
            self.last_any_peer_packet_ns = now_ns
            self.peer_ready = True
        if not was_ready:
            self.console(f"Peer route ready via {source}: {addr[0]}:{addr[1]}")
            self.log.write(
                "peer_route_ready",
                remote=addr,
                details={"source": source},
            )

    def _send_packet(
        self,
        packet: Dict[str, Any],
        target: Optional[Tuple[str, int]] = None,
    ) -> bool:
        raw = compact_json(packet)
        if len(raw) > MAX_DATAGRAM_SIZE:
            raise ValueError("Datagram too large")

        with self.state_lock:
            destination = target or self._effective_target_locked()

        try:
            sent = self.sock.sendto(raw, destination)
        except OSError as exc:
            self.console(f"SEND ERROR to {destination}: {exc}")
            self.log.write(
                "send_error",
                packet_type=str(packet.get("type", "")),
                seq=packet.get("seq"),
                remote=destination,
                details={"error": repr(exc)},
            )
            return False

        if sent != len(raw):
            self.console(f"Partial UDP send: {sent}/{len(raw)} bytes")
            return False
        return True

    def send_probe(self, reason: str = "manual") -> None:
        with self.state_lock:
            self.probe_seq += 1
            seq = self.probe_seq
            self.probes_sent += 1
            self.last_probe_tx_ns = time.monotonic_ns()
            target = self._effective_target_locked()

        packet = {
            "version": PROTOCOL_VERSION,
            "type": "probe",
            "sender_id": self.cfg.node_id,
            "receiver_id": self.cfg.peer_id,
            "seq": seq,
            "sent_wall_time": iso_now(),
            "sent_monotonic_ns": time.monotonic_ns(),
            "reason": reason,
            "probe_mode": self.cfg.probe_mode,
        }
        ok = self._send_packet(packet, target)
        self.log.write(
            "packet_sent" if ok else "packet_send_failed",
            packet_type="probe",
            seq=seq,
            remote=target,
            details={"reason": reason},
        )
        if reason in {"manual", "startup_once"}:
            self.console(f"Probe #{seq} sent to {target[0]}:{target[1]} ({reason})")

    def _send_probe_ack(self, probe: Dict[str, Any], addr: Tuple[str, int]) -> None:
        seq = int(probe.get("seq", -1))
        packet = {
            "version": PROTOCOL_VERSION,
            "type": "probe_ack",
            "sender_id": self.cfg.node_id,
            "receiver_id": self.cfg.peer_id,
            "seq": seq,
            "probe_sent_monotonic_ns": probe.get("sent_monotonic_ns"),
            "ack_sent_monotonic_ns": time.monotonic_ns(),
            "probe_mode": self.cfg.probe_mode,
        }
        ok = self._send_packet(packet, addr)
        with self.state_lock:
            self.probe_acks_sent += 1
        self.log.write(
            "packet_sent" if ok else "packet_send_failed",
            packet_type="probe_ack",
            seq=seq,
            remote=addr,
        )

    def send_data(
        self,
        text: str,
        test_label: str = "manual",
        wait_for_ack: bool = True,
    ) -> Dict[str, Any]:
        with self.state_lock:
            self.data_seq += 1
            seq = self.data_seq
            target = self._effective_target_locked()
            now_ns = time.monotonic_ns()
            peer_idle_ms = (
                None
                if self.last_any_peer_packet_ns is None
                else (now_ns - self.last_any_peer_packet_ns) / 1_000_000
            )
            probe_tx_age_ms = (
                None
                if self.last_probe_tx_ns is None
                else (now_ns - self.last_probe_tx_ns) / 1_000_000
            )
            pending_event = threading.Event()
            self.pending_data[seq] = {
                "event": pending_event,
                "sent_ns": now_ns,
                "target": target,
                "test_label": test_label,
                "ack": None,
            }
            self.data_sent += 1

        packet = {
            "version": PROTOCOL_VERSION,
            "type": "data",
            "sender_id": self.cfg.node_id,
            "receiver_id": self.cfg.peer_id,
            "seq": seq,
            "sent_wall_time": iso_now(),
            "sent_monotonic_ns": now_ns,
            "text": text,
            "test_label": test_label,
            "sender_peer_idle_ms": peer_idle_ms,
            "sender_last_probe_tx_age_ms": probe_tx_age_ms,
            "probe_mode": self.cfg.probe_mode,
        }

        ok = self._send_packet(packet, target)
        self.log.write(
            "packet_sent" if ok else "packet_send_failed",
            packet_type="data",
            seq=seq,
            remote=target,
            details={
                "test_label": test_label,
                "peer_idle_ms": peer_idle_ms,
                "last_probe_tx_age_ms": probe_tx_age_ms,
                "text": text,
            },
        )
        self.console(
            f"DATA #{seq} sent to {target[0]}:{target[1]}, "
            f"label={test_label}, peer_idle_ms={peer_idle_ms}"
        )

        if not ok:
            with self.state_lock:
                self.pending_data.pop(seq, None)
            return {"ok": False, "seq": seq, "reason": "send_error"}

        if not wait_for_ack:
            return {"ok": True, "seq": seq, "reason": "sent_without_wait"}

        timeout_sec = self.cfg.data_ack_timeout_ms / 1000.0
        got_ack = pending_event.wait(timeout_sec)

        with self.state_lock:
            pending = self.pending_data.pop(seq, None)
            ack = None if pending is None else pending.get("ack")

        if got_ack and ack:
            rtt_ms = ack["rtt_ms"]
            self.console(f"PASS DATA #{seq}: ACK received, RTT={rtt_ms:.3f} ms")
            self.log.write(
                "data_test_pass",
                packet_type="data",
                seq=seq,
                remote=target,
                details={
                    "test_label": test_label,
                    "rtt_ms": rtt_ms,
                    "ack": ack,
                },
            )
            return {"ok": True, "seq": seq, "rtt_ms": rtt_ms, "ack": ack}

        self.console(
            f"FAIL DATA #{seq}: no ACK within {self.cfg.data_ack_timeout_ms} ms"
        )
        self.log.write(
            "data_test_fail",
            packet_type="data",
            seq=seq,
            remote=target,
            details={
                "test_label": test_label,
                "timeout_ms": self.cfg.data_ack_timeout_ms,
            },
        )
        return {"ok": False, "seq": seq, "reason": "ack_timeout"}

    def _send_data_ack(self, data: Dict[str, Any], addr: Tuple[str, int]) -> None:
        seq = int(data.get("seq", -1))
        packet = {
            "version": PROTOCOL_VERSION,
            "type": "data_ack",
            "sender_id": self.cfg.node_id,
            "receiver_id": self.cfg.peer_id,
            "seq": seq,
            "data_sent_monotonic_ns": data.get("sent_monotonic_ns"),
            "receiver_data_received_monotonic_ns": time.monotonic_ns(),
            "ack_sent_monotonic_ns": time.monotonic_ns(),
            "test_label": data.get("test_label"),
            "probe_mode": self.cfg.probe_mode,
        }
        ok = self._send_packet(packet, addr)
        with self.state_lock:
            self.data_acks_sent += 1
        self.log.write(
            "packet_sent" if ok else "packet_send_failed",
            packet_type="data_ack",
            seq=seq,
            remote=addr,
            details={"test_label": data.get("test_label")},
        )
        self.console(
            f"DATA_ACK #{seq} {'sent' if ok else 'FAILED'} "
            f"to {addr[0]}:{addr[1]}"
        )

    def _probe_loop(self) -> None:
        mode = self.cfg.probe_mode
        interval_sec = self.cfg.probe_interval_ms / 1000.0

        if mode == "off":
            return

        if self.stop_event.wait(0.2):
            return

        if mode == "once":
            self.send_probe("startup_once")
            return

        while not self.stop_event.is_set():
            should_send = False
            reason = ""

            with self.state_lock:
                fresh = self._route_is_fresh_locked()
                if not fresh:
                    self.peer_ready = False

                if mode == "periodic":
                    should_send = True
                    reason = "periodic"
                elif mode == "until_ack" and not fresh:
                    should_send = True
                    reason = "retry_until_ready"

            if should_send:
                self.send_probe(reason)

            if self.stop_event.wait(interval_sec):
                return

    def _receiver_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                raw, addr = self.sock.recvfrom(MAX_DATAGRAM_SIZE)
            except socket.timeout:
                continue
            except OSError:
                return

            try:
                packet = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                self.console(f"Discarded malformed datagram from {addr}: {exc}")
                self.log.write(
                    "malformed_datagram",
                    remote=addr,
                    details={"error": repr(exc), "size": len(raw)},
                )
                continue

            if packet.get("version") != PROTOCOL_VERSION:
                self.log.write(
                    "wrong_protocol_version",
                    packet_type=str(packet.get("type", "")),
                    seq=packet.get("seq"),
                    remote=addr,
                    details={"received_version": packet.get("version")},
                )
                continue

            if str(packet.get("receiver_id")) != self.cfg.node_id:
                self.log.write(
                    "wrong_receiver",
                    packet_type=str(packet.get("type", "")),
                    seq=packet.get("seq"),
                    remote=addr,
                    details={"receiver_id": packet.get("receiver_id")},
                )
                continue

            if str(packet.get("sender_id")) != self.cfg.peer_id:
                self.log.write(
                    "unexpected_sender",
                    packet_type=str(packet.get("type", "")),
                    seq=packet.get("seq"),
                    remote=addr,
                    details={"sender_id": packet.get("sender_id")},
                )
                continue

            peer_mode = packet.get("probe_mode")
            if peer_mode is not None and str(peer_mode) != self.cfg.probe_mode:
                self.peer_mode_mismatch = str(peer_mode)
                self.log.write(
                    "peer_mode_mismatch",
                    packet_type=str(packet.get("type", "")),
                    seq=packet.get("seq"),
                    remote=addr,
                    details={
                        "local_probe_mode": self.cfg.probe_mode,
                        "peer_probe_mode": str(peer_mode),
                    },
                )
                if not self._reported_peer_mode_mismatch:
                    self._reported_peer_mode_mismatch = True
                    self.console(
                        "ERROR: peer probe_mode mismatch: "
                        f"local={self.cfg.probe_mode}, peer={peer_mode}. "
                        "Stop all old test processes and launch the matching B script."
                    )

            packet_type = str(packet.get("type", ""))
            seq = packet.get("seq")
            self.log.write(
                "packet_received",
                packet_type=packet_type,
                seq=seq,
                remote=addr,
                details={"size": len(raw)},
            )

            if packet_type == "probe":
                with self.state_lock:
                    self.probes_received += 1
                    self.last_probe_rx_ns = time.monotonic_ns()
                self._mark_peer_seen(addr, "probe")
                self._send_probe_ack(packet, addr)

            elif packet_type == "probe_ack":
                self._mark_peer_seen(addr, "probe_ack")
                with self.state_lock:
                    self.probe_acks_received += 1
                sent_ns = packet.get("probe_sent_monotonic_ns")
                rtt_ms = None
                if isinstance(sent_ns, int):
                    rtt_ms = (time.monotonic_ns() - sent_ns) / 1_000_000
                self.log.write(
                    "probe_ack_processed",
                    packet_type="probe_ack",
                    seq=int(seq) if seq is not None else None,
                    remote=addr,
                    details={"rtt_ms": rtt_ms},
                )
                self.console(
                    f"Probe ACK #{seq} received"
                    + ("" if rtt_ms is None else f", RTT={rtt_ms:.3f} ms")
                )

            elif packet_type == "data":
                self._mark_peer_seen(addr, "data")
                with self.state_lock:
                    self.data_received += 1
                sent_ns = packet.get("sent_monotonic_ns")
                one_process_delta_ms = None
                if isinstance(sent_ns, int):
                    # Monotonic clocks on different computers are not comparable.
                    # This number is logged only when both instances happen to run
                    # on the same machine; it is not used for pass/fail.
                    one_process_delta_ms = (time.monotonic_ns() - sent_ns) / 1_000_000
                self.console(
                    f"DATA #{seq} received from {addr[0]}:{addr[1]}: "
                    f"{packet.get('text', '')!r}, label={packet.get('test_label')}"
                )
                self.log.write(
                    "data_received",
                    packet_type="data",
                    seq=int(seq) if seq is not None else None,
                    remote=addr,
                    details={
                        "text": packet.get("text"),
                        "test_label": packet.get("test_label"),
                        "sender_peer_idle_ms": packet.get("sender_peer_idle_ms"),
                        "sender_last_probe_tx_age_ms": packet.get(
                            "sender_last_probe_tx_age_ms"
                        ),
                        "local_minus_remote_monotonic_ms_not_cross_host_valid":
                            one_process_delta_ms,
                    },
                )
                self._send_data_ack(packet, addr)

            elif packet_type == "data_ack":
                self._mark_peer_seen(addr, "data_ack")
                now_ns = time.monotonic_ns()
                with self.state_lock:
                    self.data_acks_received += 1
                    pending = self.pending_data.get(int(seq))
                    if pending is not None:
                        rtt_ms = (now_ns - pending["sent_ns"]) / 1_000_000
                        pending["ack"] = {
                            "rtt_ms": rtt_ms,
                            "remote": [addr[0], addr[1]],
                            "received_wall_time": iso_now(),
                            "test_label": packet.get("test_label"),
                        }
                        pending["event"].set()
                self.log.write(
                    "data_ack_processed",
                    packet_type="data_ack",
                    seq=int(seq) if seq is not None else None,
                    remote=addr,
                    details={"matched_pending": pending is not None},
                )
            else:
                self.log.write(
                    "unknown_packet_type",
                    packet_type=packet_type,
                    seq=int(seq) if seq is not None else None,
                    remote=addr,
                )

    def status_snapshot(self) -> Dict[str, Any]:
        now_ns = time.monotonic_ns()
        with self.state_lock:
            route_fresh = self._route_is_fresh_locked()
            route_age_ms = (
                None
                if self.route_last_seen_ns is None
                else (now_ns - self.route_last_seen_ns) / 1_000_000
            )
            last_probe_tx_age_ms = (
                None
                if self.last_probe_tx_ns is None
                else (now_ns - self.last_probe_tx_ns) / 1_000_000
            )
            last_probe_rx_age_ms = (
                None
                if self.last_probe_rx_ns is None
                else (now_ns - self.last_probe_rx_ns) / 1_000_000
            )
            last_peer_packet_age_ms = (
                None
                if self.last_any_peer_packet_ns is None
                else (now_ns - self.last_any_peer_packet_ns) / 1_000_000
            )
            return {
                "node_id": self.cfg.node_id,
                "probe_mode": self.cfg.probe_mode,
                "configured_peer": [self.cfg.peer_ip, self.cfg.peer_port],
                "learned_route": None
                if self.learned_route is None
                else [self.learned_route[0], self.learned_route[1]],
                "route_fresh": route_fresh,
                "route_age_ms": route_age_ms,
                "route_ttl_ms": self.cfg.route_ttl_ms,
                "peer_ready": self.peer_ready,
                "peer_mode_mismatch": self.peer_mode_mismatch,
                "last_probe_tx_age_ms": last_probe_tx_age_ms,
                "last_probe_rx_age_ms": last_probe_rx_age_ms,
                "last_peer_packet_age_ms": last_peer_packet_age_ms,
                "counters": {
                    "probes_sent": self.probes_sent,
                    "probes_received": self.probes_received,
                    "probe_acks_sent": self.probe_acks_sent,
                    "probe_acks_received": self.probe_acks_received,
                    "data_sent": self.data_sent,
                    "data_received": self.data_received,
                    "data_acks_sent": self.data_acks_sent,
                    "data_acks_received": self.data_acks_received,
                },
            }

    def print_status(self) -> None:
        snapshot = self.status_snapshot()
        self.console(json.dumps(snapshot, indent=2, ensure_ascii=False))

    def start_auto_tests(self) -> None:
        if not self.cfg.auto_test_sender:
            self.console(
                "This config has auto_test_sender=false. "
                "Run auto on the designated sender computer instead."
            )
            return
        if self.auto_thread is not None and self.auto_thread.is_alive():
            self.console("Auto tests are already running.")
            return

        self.auto_thread = threading.Thread(
            target=self._auto_test_loop, name="auto-tests", daemon=True
        )
        self.auto_thread.start()

    def _wait_for_peer_ready(self, timeout_sec: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while not self.stop_event.is_set() and time.monotonic() < deadline:
            with self.state_lock:
                if self._route_is_fresh_locked():
                    return True
            time.sleep(0.1)
        return False

    def _auto_test_loop(self) -> None:
        self.console("Auto test sequence started.")
        self.log.write(
            "auto_test_start",
            details={
                "idle_tests_sec": list(self.cfg.auto_idle_tests_sec),
                "repetitions": self.cfg.auto_test_repetitions,
                "probe_mode": self.cfg.probe_mode,
            },
        )

        if self.cfg.probe_mode != "off":
            ready = self._wait_for_peer_ready(timeout_sec=30.0)
            if self.peer_mode_mismatch is not None:
                self.console(
                    "AUTO TEST ABORTED: the peer is running probe_mode="
                    f"{self.peer_mode_mismatch}, but this node is "
                    f"{self.cfg.probe_mode}."
                )
                self.log.write(
                    "auto_test_aborted_mode_mismatch",
                    details={
                        "local_probe_mode": self.cfg.probe_mode,
                        "peer_probe_mode": self.peer_mode_mismatch,
                    },
                )
                return
            if not ready:
                self.console(
                    "Peer route was not established within 30 seconds. "
                    "Auto tests will still try the configured endpoint."
                )

        results = []
        for idle_sec in self.cfg.auto_idle_tests_sec:
            for repetition in range(1, self.cfg.auto_test_repetitions + 1):
                if self.stop_event.is_set():
                    return

                with self.state_lock:
                    before_probe_sent = self.probes_sent
                    before_probe_received = self.probes_received
                    idle_start_ns = time.monotonic_ns()

                label = f"idle_{idle_sec:g}s_rep_{repetition}"
                self.console(
                    f"IDLE TEST {label}: no application data for {idle_sec:g} seconds."
                )
                self.log.write(
                    "idle_wait_start",
                    details={
                        "label": label,
                        "idle_sec": idle_sec,
                        "probe_mode": self.cfg.probe_mode,
                        "probe_count_before": before_probe_sent,
                    },
                )

                if self.stop_event.wait(idle_sec):
                    return

                with self.state_lock:
                    actual_idle_sec = (time.monotonic_ns() - idle_start_ns) / 1_000_000_000
                    probes_sent_during_idle = self.probes_sent - before_probe_sent
                    probes_received_during_idle = (
                        self.probes_received - before_probe_received
                    )

                result = self.send_data(
                    text=f"automatic test after {idle_sec:g} seconds idle",
                    test_label=label,
                    wait_for_ack=True,
                )
                clean_no_probe_idle = (
                    probes_sent_during_idle == 0
                    and probes_received_during_idle == 0
                )
                test_valid = (
                    result.get("ok", False)
                    and (
                        self.cfg.probe_mode != "until_ack"
                        or clean_no_probe_idle
                    )
                    and self.peer_mode_mismatch is None
                )
                result.update(
                    {
                        "label": label,
                        "configured_idle_sec": idle_sec,
                        "actual_idle_sec": actual_idle_sec,
                        "probes_sent_during_idle": probes_sent_during_idle,
                        "probes_received_during_idle": probes_received_during_idle,
                        "clean_no_probe_idle": clean_no_probe_idle,
                        "test_valid": test_valid,
                    }
                )
                results.append(result)
                self.log.write("idle_test_result", details=result)

                if (
                    self.cfg.probe_mode == "until_ack"
                    and not clean_no_probe_idle
                ):
                    verdict = "INVALID/CONTAMINATED"
                else:
                    verdict = "PASS" if test_valid else "FAIL"

                self.console(
                    f"RESULT {label}: {verdict}, "
                    f"delivery_ack={'yes' if result.get('ok') else 'no'}, "
                    f"probes_sent_during_idle={probes_sent_during_idle}, "
                    f"probes_received_during_idle={probes_received_during_idle}"
                )

                if self.stop_event.wait(1.0):
                    return

        passed = sum(1 for item in results if item.get("test_valid"))
        failed = len(results) - passed
        summary = {
            "probe_mode": self.cfg.probe_mode,
            "passed": passed,
            "failed": failed,
            "total": len(results),
            "results": results,
        }
        self.log.write("auto_test_complete", details=summary)
        self.console(
            f"AUTO TEST COMPLETE: passed={passed}, failed={failed}, total={len(results)}"
        )
        self.console(
            "Compare the CSV from probe_mode=until_ack with probe_mode=periodic."
        )

    def _command_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                line = input().strip()
            except EOFError:
                return
            except Exception:
                return

            if not line:
                continue

            command, _, rest = line.partition(" ")
            command = command.lower()

            if command == "status":
                self.print_status()
            elif command == "probe":
                self.send_probe("manual")
            elif command == "send":
                text = rest.strip() or "manual test"
                threading.Thread(
                    target=self.send_data,
                    args=(text, "manual", True),
                    daemon=True,
                ).start()
            elif command == "auto":
                self.start_auto_tests()
            elif command == "help":
                self.console(
                    "Commands:\n"
                    "  status       show route age and packet counters\n"
                    "  probe        send one probe immediately\n"
                    "  send <text>  send one DATA and wait for DATA_ACK\n"
                    "  auto         run configured idle tests (sender only)\n"
                    "  quit         stop the program"
                )
            elif command in {"quit", "exit"}:
                self.stop()
                return
            else:
                self.console(f"Unknown command: {command!r}. Type help.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test whether a two-computer UDP path needs periodic probes."
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to the node JSON config file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        cfg = Config.load(args.config)
        tester = PeerProbeTester(cfg, args.config.resolve())
    except Exception as exc:
        print(f"Configuration/startup error: {exc}", file=sys.stderr)
        return 2

    tester.start()
    tester.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
