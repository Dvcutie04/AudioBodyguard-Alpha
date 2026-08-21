import math, random

class MultiMicSimulator:
    def __init__(self, mic_positions=None, sample_rate=16000, speed_of_sound=343.0, seed=42):
        self.sample_rate = sample_rate
        self.c = speed_of_sound
        self.mic_positions = mic_positions or [[0.0, 0.0, 0.0], [0.05, 0.0, 0.0], [0.0, 0.05, 0.0], [0.05, 0.05, 0.0]]
        self.seed = seed
        random.seed(seed)

    def generate_frame(self, source_pos, signal_amplitude=0.5, noise_level=0.01, gain_mismatches=None):
        num_mics = len(self.mic_positions)
        gains = gain_mismatches or [1.0] * num_mics
        frame = []
        for i, mic_pos in enumerate(self.mic_positions):
            dist = math.sqrt(sum((s - m) ** 2 for s, m in zip(source_pos, mic_pos)))
            delay_sec = dist / self.c
            phase_shift = (2 * math.pi * 1000 * delay_sec) % (2 * math.pi)
            attenuation = 1.0 / max(dist, 1.0)
            base_sig = math.sin(phase_shift) * signal_amplitude * attenuation * gains[i]
            noise = random.gauss(0, noise_level)
            frame.append(base_sig + noise)
        return frame
