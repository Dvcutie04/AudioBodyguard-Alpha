import time
import json
from .orchestrator import SpatialVoiceEngine

def run_benchmark(frames: int = 100):
    engine = SpatialVoiceEngine()
    sample_frame = [[0.05] * 160, [0.05] * 160]
    
    latencies = []
    start_total = time.perf_counter()
    
    for _ in range(frames):
        t0 = time.perf_counter()
        engine.process_frame(sample_frame)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        
    total_time = (time.perf_counter() - start_total) * 1000.0
    latencies.sort()
    
    p50 = latencies[int(frames * 0.50)]
    p95 = latencies[int(frames * 0.95)]
    p99 = latencies[int(frames * 0.99)]
    
    metrics = {
        "total_frames": frames,
        "total_duration_ms": round(total_time, 2),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 3),
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "p99_ms": round(p99, 3)
    }
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    run_benchmark()
