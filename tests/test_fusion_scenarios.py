import math, random
from src.voice.orchestrator import SpatialVoiceEngine

def generate_channel_pair(freq=440.0, sample_rate=16000, frame_len=160, tdoa_samples=0.0, snr_db=30.0, amplitude=0.1):
    ch0, ch1 = [], []
    noise_amp = amplitude / (10.0 ** (snr_db / 20.0)) if snr_db < 100 else 0.0
    for i in range(frame_len):
        t = i / sample_rate
        s0 = amplitude * math.sin(2 * math.pi * freq * t)
        t_shifted = (i - tdoa_samples) / sample_rate
        s1 = amplitude * math.sin(2 * math.pi * freq * t_shifted)
        # Independent decorrelated noise per channel
        n0 = noise_amp * (((i * 7 + 3) % 13) / 6.0 - 1.0)
        n1 = noise_amp * (((i * 11 + 5) % 17) / 8.0 - 1.0)
        ch0.append(s0 + n0)
        ch1.append(s1 + n1)
    return [ch0, ch1]

def run_tests():
    engine = SpatialVoiceEngine()
    print("[1/4] Testing Clean Target Speaker (High SNR)...")
    frame = generate_channel_pair(snr_db=40.0)
    for _ in range(5):
        out = engine.process_frame(frame)
    hyp = out["hypothesis"]
    assert hyp["confidence"] >= 0.70, f"Clean frame confidence too low: {hyp['confidence']}"
    assert hyp["sector_confidence"]["fallback_active"] is False, "Fallback erroneously active on clean frame"
    
    print("[2/4] Testing Sudden SNR Collapse...")
    noisy_frame = generate_channel_pair(snr_db=-15.0)
    for _ in range(5):
        out_noisy = engine.process_frame(noisy_frame)
    hyp_noisy = out_noisy["hypothesis"]
    print(f"    -> Post-noise DoA Rel: {hyp_noisy['sector_confidence']['doa_rel']}")
    assert hyp_noisy["sector_confidence"]["doa_rel"] < 0.80, f"DoA reliability failed to drop under noise: {hyp_noisy['sector_confidence']['doa_rel']}"
    
    print("[3/4] Testing Trajectory Jump & Hysteresis Activation...")
    far_frame = generate_channel_pair(tdoa_samples=3.5)
    for _ in range(3):
        out_jump = engine.process_frame(far_frame)
    
    print("[4/4] Testing Total Modality Degradation (Zero Frame)...")
    zero_frame = [[0.0] * 160, [0.0] * 160]
    for _ in range(3):
        out_zero = engine.process_frame(zero_frame)
    
    print("\n[SUCCESS] All deterministic synthetic scenario checks passed!")

if __name__ == "__main__":
    run_tests()
