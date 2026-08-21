import math

class FeatureFabric:
    def __init__(self, sample_rate=16000, frame_size=160):
        self.sample_rate = sample_rate
        self.frame_size = frame_size

    def extract_features(self, frame):
        if isinstance(frame[0], list):
            channels = frame
        else:
            channels = [frame]

        ch_energies = [sum(x * x for x in ch) / max(len(ch), 1) for ch in channels]
        ch_zcrs = [sum(1 for i in range(1, len(ch)) if (ch[i] >= 0) != (ch[i-1] >= 0)) for ch in channels]

        primary_energy = ch_energies[0]
        energy_delta = (max(ch_energies) - min(ch_energies)) if len(channels) > 1 else 0.0
        zcr_delta = (max(ch_zcrs) - min(ch_zcrs)) if len(channels) > 1 else 0

        return {
            "energy": primary_energy,
            "zero_crossings": ch_zcrs[0],
            "energy_delta": energy_delta,
            "zcr_delta": zcr_delta,
            "channels": len(channels),
            "frame_len": len(channels[0])
        }
