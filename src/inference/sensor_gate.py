class SensorQualityGate:
    def __init__(self, max_clipping_ratio: float = 0.05, min_energy: float = 0.001):
        self.max_clipping_ratio = max_clipping_ratio
        self.min_energy = min_energy

    def validate(self, raw_frame_stats: dict) -> bool:
        clipping = raw_frame_stats.get("clipping_ratio", 0.0)
        energy = raw_frame_stats.get("acoustic_energy", 1.0)
        if raw_frame_stats.get("adc_saturated", False) or raw_frame_stats.get("corrupted_vector", False) or clipping > self.max_clipping_ratio or energy < self.min_energy:
            return False
        return True
