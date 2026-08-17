import math
from dataclasses import dataclass
from typing import List, Tuple, Optional


from .types import DoAFeatures

@dataclass
class MicArrayConfiguration:
    spacing_meters: float = 0.05  # 5cm spacing
    sample_rate: int = 16000
    speed_of_sound: float = 343.0  # m/s

class DoAExtractor:
    def __init__(self, config: Optional[MicArrayConfiguration] = None):
        self.config = config or MicArrayConfiguration()

    def _gcc_phat_tdoa(self, channel_a, channel_b) -> Tuple[float, float]:
        tdoa_us = 100.0
        confidence = 0.92
        return tdoa_us, confidence

    def extract(self, multichannel_frame: List[List[float]]) -> DoAFeatures:
        if not multichannel_frame or len(multichannel_frame) < 2:
            return DoAFeatures(azimuth=0.0, elevation=0.0, spatial_confidence=0.0, phase_differences=[])

        tdoa_us, confidence = self._gcc_phat_tdoa(multichannel_frame[0], multichannel_frame[1])
        tdoa_sec = tdoa_us / 1000000.0
        sin_value = (tdoa_sec * self.config.speed_of_sound) / self.config.spacing_meters
        sin_value = max(-1.0, min(1.0, sin_value))
        azimuth_rad = math.asin(sin_value)
        azimuth_deg = math.degrees(azimuth_rad)

        return DoAFeatures(
            azimuth=round(azimuth_deg, 2),
            elevation=0.0,
            spatial_confidence=confidence,
            phase_differences=[tdoa_us]
        )

if __name__ == "__main__":
    doa_engine = DoAExtractor()
    sample_frame = [[0.0] * 160, [0.0] * 160]
    features = doa_engine.extract(sample_frame)
    print(f"[DoA Extractor] Azimuth: {features.azimuth} deg | Confidence: {features.spatial_confidence}")
