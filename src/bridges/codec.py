import json
from dataclasses import asdict
from src.bridges.envelope import ObservationEnvelope
from src.bridges.protocol import MessageType, ProtocolVersion
from src.edge.protocol import AcousticObservation, PrivacyStatus


class CanonicalCodec:
    """Enforces deterministic JSON serialization for cryptographic lineage."""

    @staticmethod
    def encode_observation(obs: AcousticObservation) -> bytes:
        obs_dict = {
            "node_id": obs.node_id,
            "sequence_id": obs.sequence_id,
            "monotonic_timestamp_ns": obs.monotonic_timestamp_ns,
            "spl_estimate": obs.spl_estimate,
            "event_class": obs.event_class,
            "confidence": obs.confidence,
            "temporal_metric": obs.temporal_metric,
            "privacy_status": obs.privacy_status.value,
            "feature_digest": obs.feature_digest,
            "payload_digest": obs.payload_digest,
        }
        return json.dumps(obs_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def decode_observation(data: bytes) -> AcousticObservation:
        payload = json.loads(data.decode("utf-8"))
        payload["privacy_status"] = PrivacyStatus(payload["privacy_status"])
        return AcousticObservation(**payload)
