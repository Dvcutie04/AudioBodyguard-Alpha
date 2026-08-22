import time, statistics
from src.voice.orchestrator import SpatialVoiceEngine

engine = SpatialVoiceEngine()
frame = [[0.05 * (i % 7 - 3) for i in range(160)], [0.05 * (i % 11 - 5) for i in range(160)]]

for _ in range(100):
    engine.process_frame(frame)

timings = []
for _ in range(1000):
    t0 = time.perf_counter()
    engine.process_frame(frame)
    t1 = time.perf_counter()
    timings.append((t1 - t0) * 1000)

print(f"p50: {statistics.median(timings):.4f} ms")
print(f"p95: {statistics.quantiles(timings, n=20)[18]:.4f} ms")
print(f"p99: {statistics.quantiles(timings, n=100)[98]:.4f} ms")
