from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


Role = Literal["CM", "CA"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Endpoint(StrictModel):
    es_id: int = Field(ge=0)
    name: str = Field(min_length=1)
    role: Role
    ip: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)


class CAParameters(StrictModel):
    l2: float = Field(default=0.0, ge=0.0, le=655.35)
    clock_drift_rate: float = Field(ge=0.0)
    relative_offset_delay: float = Field(ge=0.0, le=655.35)


class TopologyConfig(StrictModel):
    endpoints: List[Endpoint]
    ca_parameters: Dict[int, CAParameters]

    @model_validator(mode="after")
    def validate_topology(self) -> "TopologyConfig":
        ids = [endpoint.es_id for endpoint in self.endpoints]
        duplicates = sorted({es_id for es_id in ids if ids.count(es_id) > 1})
        if duplicates:
            raise ValueError(f"topology.json contains duplicate ES_ID values: {duplicates}")

        endpoint_ids = set(ids)
        ca_ids = {endpoint.es_id for endpoint in self.endpoints if endpoint.role == "CA"}
        parameter_ids = set(self.ca_parameters.keys())
        missing = sorted(ca_ids - parameter_ids)
        extra = sorted(parameter_ids - ca_ids)
        if missing:
            raise ValueError(f"Missing CA parameters for ES_ID values: {missing}")
        if extra:
            raise ValueError(f"CA parameters exist for non-CA ES_ID values: {extra}")

        endpoint_pairs = [(endpoint.ip, endpoint.port) for endpoint in self.endpoints]
        duplicate_pairs = sorted({pair for pair in endpoint_pairs if endpoint_pairs.count(pair) > 1})
        if duplicate_pairs:
            raise ValueError(f"Duplicate IP/port endpoint values: {duplicate_pairs}")
        return self

    def endpoint_for(self, es_id: int) -> Endpoint:
        for endpoint in self.endpoints:
            if endpoint.es_id == es_id:
                return endpoint
        raise KeyError(f"Unknown ES_ID: {es_id}")

    def endpoints_by_role(self, role: Role) -> List[Endpoint]:
        return [endpoint for endpoint in self.endpoints if endpoint.role == role]


class CMNodeConfig(StrictModel):
    role: Literal["CM"]
    es_id: int = Field(ge=0)
    t1: float
    e1: float = Field(default=0.0, ge=0.0, le=655.35)
    topology_path: str = Field(min_length=1)


class CANodeConfig(StrictModel):
    role: Literal["CA"]
    es_id: int = Field(ge=0)
    t2: float
    dmax: float = Field(ge=0.0)
    topology_path: str = Field(min_length=1)
    # Simulation-only transport compatibility switch. When True, this CA
    # actively sends both CA-to-CM transport probes and CA-to-CA peer probes.
    # Incoming probes are still accepted when False, allowing only the node on
    # a restrictive host to enable the workaround. Omission preserves the
    # original direct-UDP simulation behavior.
    probe_enabled: bool = Field(default=False, strict=True)


class RequestMessage(StrictModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["request"]
    cm_es_id: int = Field(ge=0)
    request_number: int = Field(ge=0, le=65535)
    t1: float


class ResponseMessage(StrictModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["response"]
    cm_es_id: int = Field(ge=0)
    ca_es_id: int = Field(ge=0)
    request_number: int = Field(ge=0, le=65535)
    t1: float
    t2: float
    reset_counter: int = Field(ge=0, le=255)


class ClockOffsetEntry(StrictModel):
    ca_es_id: int = Field(ge=0)
    relative_offset: Optional[float]
    reset_counter: Optional[int] = Field(default=None, ge=0, le=255)
    relative_offset_error: float


class ClockOffsetListMessage(StrictModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["clock_offset_list"]
    cm_es_id: int = Field(ge=0)
    request_number: int = Field(ge=0, le=65535)
    number_of_ca: int = Field(ge=0)
    entries: List[ClockOffsetEntry]

    @model_validator(mode="after")
    def validate_entry_count(self) -> "ClockOffsetListMessage":
        if self.number_of_ca != len(self.entries):
            raise ValueError("number_of_ca does not match entries length")
        entry_ids = [entry.ca_es_id for entry in self.entries]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("clock_offset_list contains duplicate CA ES_ID entries")
        return self

    def entry_for(self, ca_es_id: int) -> Optional[ClockOffsetEntry]:
        for entry in self.entries:
            if entry.ca_es_id == ca_es_id:
                return entry
        return None


class TransportProbeMessage(StrictModel):
    """CA-initiated transport poll for restrictive UDP firewalls.

    A CM may immediately return the currently published request and clock
    offset list to the datagram's actual source address.  The fields only
    suppress duplicate delivery; they do not participate in synchronization
    calculations or CM selection.
    """

    protocol_version: Literal[1] = 1
    message_type: Literal["transport_probe"]
    ca_es_id: int = Field(ge=0)
    cm_es_id: int = Field(ge=0)
    last_request_number: Optional[int] = Field(default=None, ge=0, le=65535)
    last_clock_list_request_number: Optional[int] = Field(
        default=None,
        ge=0,
        le=65535,
    )


class CAPeerProbeMessage(StrictModel):
    """Transport-only CA-to-CA path warm-up message."""

    protocol_version: Literal[1] = 1
    message_type: Literal["ca_peer_probe"]
    sender_ca_es_id: int = Field(ge=0)
    receiver_ca_es_id: int = Field(ge=0)


class CAPeerAckMessage(StrictModel):
    """Immediate reply to a CA peer probe."""

    protocol_version: Literal[1] = 1
    message_type: Literal["ca_peer_ack"]
    sender_ca_es_id: int = Field(ge=0)
    receiver_ca_es_id: int = Field(ge=0)


class DataMessage(StrictModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["ca_data"]
    sender_ca_es_id: int = Field(ge=0)
    receiver_ca_es_id: int = Field(ge=0)
    reset_counter: int = Field(ge=0, le=255)
    transmission_latency: int = Field(ge=0)
    payload: str = "CA communication test message"


AnyMessage = Union[
    RequestMessage,
    ResponseMessage,
    ClockOffsetListMessage,
    TransportProbeMessage,
    CAPeerProbeMessage,
    CAPeerAckMessage,
    DataMessage,
]
