import json
from dataclasses import asdict
from typing import Optional, Dict, Any

from .types import SpatialEvidence, TargetSpeakerHypothesis
from .doa import DoAExtractor
from .speaker import SpeakerExtractor
from .room import RoomAcousticsExtractor
from .temporal import TemporalTracker

class SpatialVoiceEngine:
    def __init__(self):
        self.doa_extractor = DoAExtractor()
        self.speaker_extractor = SpeakerExtractor()
        self.room_extractor = RoomAcousticsExtractor()
        self.temporal_tracker = TemporalTracker()
        self.certainty_threshold = 0.80

    def _extract_cheap_features(self, frame: Any) -> SpatialEvidence:
        doa = self.doa_extractor.extract(frame)
        single_channel = frame[0] if isinstance(frame, list) and frame and isinstance(frame[0], list) else frame
        speaker = self.speaker_extractor.extract(single_channel)
        room = self.room_extractor.extract(single_channel)
        temporal = self.temporal_tracker.extract(single_channel, current_azimuth=doa.azimuth)
        return SpatialEvidence(doa=doa, speaker=speaker, room=room, temporal=temporal)

    def _fuse_evidence(self, evidence: SpatialEvidence) -> TargetSpeakerHypothesis:
        confidence = (0.3 * evidence.doa.spatial_confidence) + (0.4 * evidence.speaker.embedding_confidence) + (0.3 * evidence.temporal.continuity_score)
        return TargetSpeakerHypothesis(
            speaker_id=evidence.speaker.speix_id,
            zone_id=f"sector_{evidence.doa.azimuth}",
            confidence=round(confidence, 2),
            sector_confidence={
                "spatial": evidence.doa.spatial_confidence,
                "speaker": evidence.speaker.embedding_confidence,
                "temporal": evidence.temporal.continuity_score
            }
        )

    def _expensive_separation(self, frame: Any, evidence: SpatialEvidence):
        print("\n[@AQSS_Neural_Net]: Running Expensive Source Separation on 400ms buffer.")
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
    sample_frame = [[0.05] * 160, [0.05] * 160]
    result = engine.process_frame(sample_frame)
    print(json.dumps(result, indent=2))
