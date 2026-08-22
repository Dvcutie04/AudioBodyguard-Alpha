import math
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .types import SpatialEvidence, TargetSpeakerHypothesis

@dataclass
class DynamicFusionConfig:
    low_threshold: float = 0.75
    high_threshold: float = 0.85
    max_azimuth_delta: float = 15.0

class DynamicFusionEngine:
    def __init__(self, config: Optional[DynamicFusionConfig] = None):
        self.config = config or DynamicFusionConfig()
        self.fallback_active = False
        self.last_azimuth: Optional[float] = None

    def _compute_doa_reliability(self, evidence: SpatialEvidence) -> float:
        base = evidence.doa.spatial_confidence
        if self.last_azimuth is not None:
            delta = abs(evidence.doa.azimuth - self.last_azimuth)
            if delta > self.config.max_azimuth_delta:
                base *= 0.5  # Penalize high jitter
        self.last_azimuth = evidence.doa.azimuth
        return max(0.0, min(1.0, base))

    def _compute_speaker_reliability(self, evidence: SpatialEvidence) -> float:
        vad_factor = 1.0 if evidence.temporal.voice_activity else 0.2
        return max(0.0, min(1.0, evidence.speaker.embedding_confidence * vad_factor))

    def _compute_room_reliability(self, evidence: SpatialEvidence) -> float:
        return max(0.1, min(1.0, 1.0 - (evidence.room.reverberation_indicator * 0.5)))

    def _compute_temporal_reliability(self, evidence: SpatialEvidence) -> float:
        return max(0.0, min(1.0, evidence.temporal.continuity_score))

    def fuse(self, evidence: SpatialEvidence) -> TargetSpeakerHypothesis:
        r_doa = self._compute_doa_reliability(evidence)
        r_spk = self._compute_speaker_reliability(evidence)
        r_rm = self._compute_room_reliability(evidence)
        r_tmp = self._compute_temporal_reliability(evidence)

        total_rel = r_doa + r_spk + r_rm + r_tmp
        if total_rel == 0:
            w_doa = w_spk = w_rm = w_tmp = 0.25
        else:
            w_doa, w_spk, w_rm, w_tmp = r_doa/total_rel, r_spk/total_rel, r_rm/total_rel, r_tmp/total_rel

        confidence = (
            (w_doa * evidence.doa.spatial_confidence) +
            (w_spk * evidence.speaker.embedding_confidence) +
            (w_rm * (1.0 - evidence.room.reverberation_indicator)) +
            (w_tmp * evidence.temporal.continuity_score)
        )
        confidence = round(max(0.0, min(1.0, confidence)), 2)

        # Hysteresis Decision
        if self.fallback_active and confidence > self.config.high_threshold:
            self.fallback_active = False
        elif not self.fallback_active and confidence < self.config.low_threshold:
            self.fallback_active = True

        return TargetSpeakerHypothesis(
            speaker_id=evidence.speaker.speix_id,
            zone_id=f"sector_{int(evidence.doa.azimuth)}",
            confidence=confidence,
            sector_confidence={
                "doa_rel": round(r_doa, 2),
                "speaker_rel": round(r_spk, 2),
                "room_rel": round(r_rm, 2),
                "temporal_rel": round(r_tmp, 2),
                "fallback_active": self.fallback_active
            }
        )

if __name__ == "__main__":
    print("[Fusion Engine Ready]")
