import json
from dataclasses import asdict
from typing import Optional, Dict, Any

from .types import SpatialEvidence
from .doa import DoAExtractor
from .speaker import SpeakerExtractor
from .room import RoomAcousticsExtractor
from .temporal import TemporalTracker
from .fusion import DynamicFusionEngine

class SpatialVoiceEngine:
    def __init__(self):
        self.doa_extractor = DoAExtractor()
        self.speaker_extractor = SpeakerExtractor()
        self.room_extractor = RoomAcousticsExtractor()
        self.temporal_tracker = TemporalTracker()
        self.fusion_engine = DynamicFusionEngine()

    def _extract_cheap_features(self, frame: Any) -> SpatialEvidence:
        doa = self.doa_extractor.extract(frame)
        single_channel = frame[0] if isinstance(frame, list) and frame and isinstance(frame[0], list) else frame
        speaker = self.speaker_extractor.extract(single_channel)
        room = self.room_extractor.extract(single_channel)
        temporal = self.temporal_tracker.extract(single_channel, current_azimuth=doa.azimuth)
        return SpatialEvidence(doa=doa, speaker=speaker, room=room, temporal=temporal)

    def process_frame(self, frame: Any) -> Dict[str, Any]:
        evidence = self._extract_cheap_features(frame)
        hypothesis = self.fusion_engine.fuse(evidence)
        fallback_status = hypothesis.sector_confidence.get("fallback_active", False)
        action_taken = "Executed Gated Source Separation" if fallback_status else "Processed Cheap Features"
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
