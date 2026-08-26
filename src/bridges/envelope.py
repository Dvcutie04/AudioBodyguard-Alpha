from dataclasses import dataclass
from src.bridges.protocol import MessageType, ProtocolVersion
from src.edge.protocol import AcousticObservation


@dataclass(frozen=True, slots=True)
class ObservationEnvelope:
    protocol_version: ProtocolVersion
    message_type: MessageType
    node_id: str
    sequence_id: int
    monotonic_timestamp_ns: int
    payload_digest: str
    authentication_tag: str
    payload: AcousticObservation

    def __post_init__(self):
        if not isinstance(self.protocol_version, ProtocolVersion):
            raise ValueError("Invalid protocol_version type")
        if not isinstance(self.message_type, MessageType):
            raise ValueError("Invalid message_type")
        if self.node_id != self.payload.node_id:
            raise ValueError("Envelope node_id must match payload node_id")
        if self.sequence_id != self.payload.sequence_id:
            raise ValueError("Envelope sequence_id must match payload sequence_id")
