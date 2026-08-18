import math
from dataclasses import dataclass

@dataclass
class DoAFeatures:
    azimuth: float
    elevation: float
    spatial_confidence: float
    phase_differences: list

class DoAExtractor:
    def __init__(self, sample_rate=16000, speed_of_sound=343.0, spacing_meters=0.08):
        self.sample_rate = sample_rate
        self.speed_of_sound = speed_of_sound
        self.spacing_meters = spacing_meters

    def extract(self, frame_channels):
        if not frame_channels or len(frame_channels) < 2:
            return DoAFeatures(0.0, 0.0, 0.0, [0.0])
        ch0, ch1 = frame_channels[0], frame_channels[1]
        n = min(len(ch0), len(ch1))
        if n == 0:
            return DoAFeatures(0.0, 0.0, 0.0, [0.0])
        e0 = sum(x * x for x in ch0) / n
        e1 = sum(x * x for x in ch1) / n
        avg_energy = (e0 + e1) / 2.0
        if avg_energy < 1e-6:
            return DoAFeatures(0.0, 0.0, 0.0, [0.0])
        best_lag = 0
        max_corr = -1e9
        max_lag = int(math.ceil(self.spacing_meters / self.speed_of_sound * self.sample_rate)) + 2
        for lag in range(-max_lag, max_lag + 1):
            corr = 0.0
            count = 0
            for i in range(n):
                j = i + lag
                if 0 <= j < n:
                    corr += ch0[i] * ch1[j]
                    count += 1
            if count > 0:
                corr /= count
                if corr > max_corr:
                    max_corr = corr
                    best_lag = lag
        norm_factor = math.sqrt(e0 * e1) + 1e-12
        corr_coef = max(0.0, min(1.0, max_corr / norm_factor))
        tdoa = best_lag / self.sample_rate
        sin_val = (tdoa * self.speed_of_sound) / self.spacing_meters
        sin_val = max(-1.0, min(1.0, sin_val))
        azimuth_deg = math.degrees(math.asin(sin_val))
        confidence = round(corr_coef * min(1.0, avg_energy / 0.001), 2)
        return DoAFeatures(azimuth=round(azimuth_deg, 2), elevation=0.0, spatial_confidence=confidence, phase_differences=[round(tdoa * 1e6, 2)])
