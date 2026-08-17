import json
from dataclasses import asdict
from typing import Optional, Dict, Any

from .types import SpatialEvidence, DoAFeatures, SpeakerFeatures, RoomFeatures, TemporalFeatures, TargetSpeakerHypothesis
from .doa import DoAExtractor

class SpatialVoiceEngine:
    def __init__(self):
        self.doa_extractor = DoAExtractor()
        self.certainty_threshold = 0.80  # Gate for expensive enhancement

    def _extract_cheap_features(self, frame: Any) -> SpatialEvidence:
        # use real DoA extractor for spatial channel
        doa = self.doa_extractor.extract(frame)
        
        speaker = SpeakerFeatures(speaker_embedding=[, speix_id="david", similarity_score=0.72, embedding_confidence=0.85)
        room = RoomFeatures(rt60_estimate=0.4, reverberation_indicator=0.1, room_fingerprint=[])
        temporal = TemporalFeatures(voice_activity=True, continuity_score=0.95, trajectory={})
        return SpatialEvidence(doa=doa, speaker=speaker, room=room, temporal=temporal)

    def _fuse_evidence(self, evidence: SpatialEvidence) -> TargetSpeakerHypothesis:
        confidence = (0.3 * evidence.doa.spatial_confidence) + (0.4 * evidence.speaker.embedding_confidence) + (0.3 * evidence.temporal.continuity_score)
        return TargetSpeakerHypothesis(
            speaker_id=evidence.speaker.speix_id,
            zone_id=f"sector_{evidence.doa.azimuth}",
            confidence=confidence,
            sector_confidence={
                "spatial": evidence.doa.spatial_confidence,
                "speaker": evidence.speaker.embedding_confidence,
                "temporal": evidence.temporal.continuity_score
            }
        )

    def _expensive_separation(self, frame: Any, evidence: SpatialEvidence):
        print("\n[A5SS_Neural_Net]: Running Expensive Source Separation on 400ms buffer.")
        return "ENHANCED_FRAME"

    def process_frame(self, frame: Any) -> Dict[str, Any]:
        evidence = self._extract_cheap_features(frame)
        hypothesis = self._fuse_evidence(evidence)
        
        action_taken = "Processed Cheap Features"
        if hypothesis.confidence < self.certainty_threshold:
            self._expensive_separation(frame, evidence)
            action_taken = "Executed Gated Source Separation"

        return {
            "hypothesis": asdict(hypothesis),
            "edge_optimization": action_taken,
            "cheap_features": asdict(evidence)
        }

if __name__ == "__main__":
    engine = SpatialVoiceEngine()
    sample_frame = [[0.0] * 160, [0.0] * 160]
    result = engine.process_frame(sample_frame)
    print(json.dumps(result, indent=2))
