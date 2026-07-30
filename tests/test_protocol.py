from __future__ import annotations

import pytest

from timesync_sim.models import (
    ClockOffsetEntry,
    ClockOffsetListMessage,
    DataMessage,
    RequestMessage,
)
from timesync_sim.protocol import ProtocolError, decode_message, encode_message


def test_request_round_trip() -> None:
    original = RequestMessage(
        message_type="request",
        cm_es_id=1,
        request_number=42,
        t1=100.0,
    )
    decoded = decode_message(encode_message(original))
    assert decoded == original


def test_none_is_serialized_as_json_null() -> None:
    message = ClockOffsetListMessage(
        message_type="clock_offset_list",
        cm_es_id=1,
        request_number=7,
        number_of_ca=1,
        entries=[
            ClockOffsetEntry(
                ca_es_id=101,
                relative_offset=None,
                reset_counter=None,
                relative_offset_error=0.38,
            )
        ],
    )
    encoded = encode_message(message)
    assert b'"relative_offset":null' in encoded
    assert b'"reset_counter":null' in encoded
    assert decode_message(encoded) == message


def test_invalid_message_type_is_rejected() -> None:
    with pytest.raises(ProtocolError):
        decode_message(b'{"message_type":"not_supported"}')
