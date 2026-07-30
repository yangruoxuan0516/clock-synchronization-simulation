from __future__ import annotations

import json
from typing import Dict, Type

from pydantic import ValidationError

from .models import (
    AnyMessage,
    CAPeerAckMessage,
    CAPeerProbeMessage,
    ClockOffsetListMessage,
    DataMessage,
    RequestMessage,
    ResponseMessage,
    StrictModel,
    TransportProbeMessage,
)


class ProtocolError(RuntimeError):
    pass


MESSAGE_MODELS: Dict[str, Type[StrictModel]] = {
    "request": RequestMessage,
    "response": ResponseMessage,
    "clock_offset_list": ClockOffsetListMessage,
    "transport_probe": TransportProbeMessage,
    "ca_peer_probe": CAPeerProbeMessage,
    "ca_peer_ack": CAPeerAckMessage,
    "ca_data": DataMessage,
}


def encode_message(message: AnyMessage) -> bytes:
    return message.model_dump_json(exclude_none=False).encode("utf-8")


def decode_message(payload: bytes) -> AnyMessage:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"Invalid JSON datagram: {exc}") from exc

    if not isinstance(raw, dict):
        raise ProtocolError("Datagram root must be a JSON object")
    message_type = raw.get("message_type")
    model_type = MESSAGE_MODELS.get(message_type)
    if model_type is None:
        raise ProtocolError(f"Unsupported message_type: {message_type!r}")
    try:
        return model_type.model_validate(raw)  # type: ignore[return-value]
    except ValidationError as exc:
        raise ProtocolError(f"Invalid {message_type} message: {exc}") from exc
