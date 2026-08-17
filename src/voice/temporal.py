from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from .types import TemporalFeatures

@dataclass
class TemporalModelConfig:
    vad_threshold: float = 0.01
    continuity_decay: float = 0.95

class TemporalTracker:
    def __init__(self, config: Optional[TemporalModelConfig] = None):
        self.config = config or TemporalModelConfig()
        self.previous_continuity = 1.0

    def extract(self, frame: List[float], current_azimuth: float = 0.0) -> TemporalFeatures:
        energy = sum(abs(x) for x in frame) / max(len(frame), 1)
        has_vad = energy > self.config.vad_threshold
        continuity = round(self.previous_continuity * self.config.continuity_decay, 2) if has_vad else 0.0
        self.previous_continuity = continuity if has_vad else 0.5
        
        return TemporalFeatures(
            voice_activity=has_vad,
            continuity_score=continuity,
            trajectory={"last_azimuth": current_azimuth, "energy_level": round(energy, 4)}
        )

if __name__ == "__main__":
    tracker = TemporalTracker()
    features = tracker.extract([0.05] * 160, current_azimuth=45.0)
    print(f"[Temporal Tracker] VAD: {features.voice_activity} | Continuity: {features.continuity_score} | Trajectory: {features.trajectory}")
