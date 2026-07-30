from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QHostAddress, QUdpSocket

from .models import AnyMessage, Endpoint
from .protocol import encode_message


class UdpTransport(QObject):
    datagram_received = Signal(bytes, str, int)
    error_occurred = Signal(str)

    def __init__(self, local_endpoint: Endpoint, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.local_endpoint = local_endpoint
        self.socket = QUdpSocket(self)
        self.socket.readyRead.connect(self._read_pending_datagrams)
        self.socket.errorOccurred.connect(self._on_error)

        # Listen on every local IPv4 interface.  The topology IP remains the
        # address advertised to other ES processes.  Binding to AnyIPv4 also
        # lets a same-computer peer reach this socket through 127.0.0.1.
        if not self.socket.bind(QHostAddress.AnyIPv4, local_endpoint.port):
            raise RuntimeError(
                f"Unable to bind UDP socket to 0.0.0.0:{local_endpoint.port} "
                f"(advertised as {local_endpoint.ip}:{local_endpoint.port}): "
                f"{self.socket.errorString()}"
            )

    def send(self, message: AnyMessage, destination: Endpoint) -> bool:
        payload = encode_message(message)

        # When both ES endpoints have the same topology IP, they are intended
        # to run on the same computer.  Use the IPv4 loopback path so Windows
        # does not route the datagram through the physical-interface firewall
        # path.  Remote peers still receive datagrams at their topology IP.
        if destination.ip == self.local_endpoint.ip:
            destination_address = QHostAddress.LocalHost
        else:
            destination_address = QHostAddress(destination.ip)

        written = self.socket.writeDatagram(
            payload,
            destination_address,
            destination.port,
        )
        if written != len(payload):
            self.error_occurred.emit(
                f"Failed to send complete datagram to {destination.ip}:{destination.port}: "
                f"{self.socket.errorString()}"
            )
            return False
        return True

    def send_to(self, message: AnyMessage, destination_ip: str, destination_port: int) -> bool:
        """Send to an address learned from an incoming datagram.

        This is used for CA-initiated transport polling.  Replying to the
        observed source tuple is more reliable behind restrictive host
        firewalls than reconstructing the return path from topology data.
        """
        payload = encode_message(message)
        written = self.socket.writeDatagram(
            payload,
            QHostAddress(destination_ip),
            destination_port,
        )
        if written != len(payload):
            self.error_occurred.emit(
                f"Failed to send complete datagram to {destination_ip}:{destination_port}: "
                f"{self.socket.errorString()}"
            )
            return False
        return True

    def _read_pending_datagrams(self) -> None:
        while self.socket.hasPendingDatagrams():
            datagram = self.socket.receiveDatagram()
            if datagram.isNull():
                continue
            payload = bytes(datagram.data())
            # Zero-length UDP datagrams are legal at the transport layer but
            # are not simulator protocol messages.  Some managed-network/Qt
            # combinations can surface them during heavy polling.  Keep them
            # out of the JSON decoder instead of flooding the runtime log.
            if not payload.strip():
                continue
            self.datagram_received.emit(
                payload,
                datagram.senderAddress().toString(),
                datagram.senderPort(),
            )

    def _on_error(self, socket_error: object) -> None:
        del socket_error
        self.error_occurred.emit(self.socket.errorString())
