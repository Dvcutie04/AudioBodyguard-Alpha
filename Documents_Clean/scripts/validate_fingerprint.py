import numpy as np
import time
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.audio.fingerprint import AcousticFingerprint, AQSSState

def generate_tone(freq, duration_sec, sample_rate=44100, amplitude=0.5):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False, dtype=np.float32)
    return amplitude * np.sin(2 * np.pi * freq * t)

def generate_noise(duration_sec, sample_rate=44100, amplitude=0.05):
    num_samples = int(sample_rate * duration_sec)
    return np.random.uniform(-amplitude, amplitude, num_samples).astype(np.float32)

def run_validation():
    print("[ * ] Initializing AQSS-36-OMEGA Fingerprint Validation Harness...")
    detector = AcousticFingerprint(target_freq=18000.0, tolerance_hz=50.0, chunk_size=1024, sample_rate=44100, entry_snr_db=12.0, exit_snr_db=6.0, min_purity=0.40, required_hits=3)
    chunk_size = 1024
    sample_rate = 44100
    test_stream = generate_tone(18000, 0.2, sample_rate, amplitude=0.4) + generate_noise(0.2, sample_rate, amplitude=0.01)
    print("\n[ TEST 1 ] Validating 18 kHz Trigger Sequence...")
    triggered_count = 0
    start_time = time.perf_counter()
    for i in range(0, len(test_stream) - chunk_size, chunk_size):
        chunk = test_stream[i:i + chunk_size]
        res = detector.process_chunk(chunk)
        print(f"  Frame {i//chunk_size}: TNR={res['tnr_db']}dB | Purity={res['purity']} | Acc={res['persistence']} | State={res['state']}")
        if res["triggered"]:
            triggered_count += 1
    exec_time_us = ((time.perf_counter() - start_time) / (len(test_stream) // chunk_size)) * 1e6
    print(f"  Result: {triggered_count > 0} | Avg Execution Time per Chunk: {exec_time_us:.2f} us\n")
    detector.accumulator = 0
    detector.state = AQSSState.IDLE
    print("[ TEST 2 ] Testing Rejection of Out-of-Band 16 kHz Signal...")
    interfere_16k = generate_tone(16000, 0.2, sample_rate, amplitude=0.5) + generate_noise(0.2, sample_rate, amplitude=0.01)
    false_positives = 0
    for i in range(0, len(interfere_16k) - chunk_size, chunk_size):
        chunk = interfere_16k[i:i + chunk_size]
        res = detector.process_chunk(chunk)
        if res["triggered"]:
            false_positives += 1
    print(f"  False Positives Detected: {false_positives} (Expected: 0)")

if __name__ == "__main__":
    run_validation()
