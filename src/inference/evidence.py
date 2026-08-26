from dataclasses import dataclass
from src.edge.protocol import AcousticObservation


@dataclass(frozen=True, slots=True)
class AcousticEvidence:
    node_id: str
    sequence_id: int
    monotonic_timestamp_ns: int
    sustained_energy_ratio: float
    temporal_variance: float
    is_high_spl_event: bool

    @classmethod
    def from_observation(cls, obs: AcousticObservation) -> "AcousticEvidence":
        # Transform raw metrics into evidence indicators
        high_spl = obs.spl_estimate >= 70.0
        energy_ratio = min(1.0, max(0.0, obs.spl_estimate / 100.0))

        return cls(
            node_id=obs.node_id,
            sequence_id=obs.sequence_id,
            monotonic_timestamp_ns=obs.monotonic_timestamp_ns,
            sustained_energy_ratio=energy_ratio,
            temporal_variance=obs.temporal_metric,
            is_high_spl_event=high_spl,
        )
