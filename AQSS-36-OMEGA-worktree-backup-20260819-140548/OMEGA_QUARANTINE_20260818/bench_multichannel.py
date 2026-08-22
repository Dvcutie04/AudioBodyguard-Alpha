import time, gc, math, random
from src.sim.acoustic_environment import MultiMicSimulator
from src.voice.orchestrator import SpatialVoiceEngine

def run_benchmark(channels, num_frames=1000):
    mics = [[i * 0.02, 0.0, 0.0] for i in range(channels)]
    sim = MultiMicSimulator(mic_positions=mics, seed=42)
    engine = SpatialVoiceEngine()
    pregenerated_frames = []
    for i in range(num_frames):
        pos = [2.0 - (i * 0.001), 1.0 - (i * 0.0005), 0.0]
        frame = sim.generate_frame(pos, signal_amplitude=0.3 + (i % 10) * 0.02)
        pregenerated_frames.append(frame)
    latencies = []
    gc.disable()
    for frame in pregenerated_frames:
        t0 = time.perf_counter()
        res = engine.process_frame(frame)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
    gc.enable()
    latencies.sort()
    p50 = latencies[int(num_frames * 0.50)]
    p95 = latencies[int(num_frames * 0.95)]
    p99 = latencies[int(num_frames * 0.99)]
    p999 = latencies[int(num_frames * 0.999)]
    max_lat = latencies[-1]
    print(f"{channels} Mics | p50: {p50:.4f}ms | p95: {p95:.4f}ms | p99: {p99:.4f}ms | p99.9: {p999:.4f}ms | Max: {max_lat:.4f}ms")

print("=== Phase 7B Multichannel Performance Matrix ===")
for ch in [2, 4, 8, 16]:
    run_benchmark(ch)
