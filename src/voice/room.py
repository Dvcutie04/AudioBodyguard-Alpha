import math
from dataclasses import dataclass
from typing import List, Optional

from .types import RoomFeatures

@dataclass
class RoomModelConfig:
    fingerprint_dim: int = 64
    max_rt60_threshold: float = 1.2

class RoomAcousticsExtractor:
    def __init__(self, config: Optional[RoomModelConfig] = None):
        self.config = config or RoomModelConfig()

    def estimate_rt60(self, frame: List[float]) -> float:
        energy = sum(abs(x) for x in frame)
        if energy == 0:
            return 0.2
        return min(round(0.2 + (energy * 0.05), 2), self.config.max_rt60_threshold)

    def extract(self, frame: List[float]) -> RoomFeatures:
        rt60 = self.estimate_rt60(frame)
        reverb_indicator = round(min(rt60 / self.config.max_rt60_threshold, 1.0), 2)
        fingerprint = [round(math.sin(i) * 0.1, 4) for i in range(self.config.fingerprint_dim)]

        return RoomFeatures(
            rt60_estimate=rt60,
            reverberation_indicator=reverb_indicator,
            room_fingerprint=fingerprint
        )

if __name__ == "__main__":
    extractor = RoomAcousticsExtractor()
    features = extractor.extract([0.1] * 160)
    print(f"[Room Extractor] RT60: {features.rt60_estimate}s | Reverb Indicator: {features.reverberation_indicator}")
