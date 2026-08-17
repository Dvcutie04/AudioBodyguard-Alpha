import time
import numpy as np

def measure_latency(n_iters=1000):
    start = time.perf_counter()
    for _ in range(n_iters):
        _ = np.dot(np.random.rand(10, 10), np.random.rand(10, 1))
    end = time.perf_counter()
    avg_ms = ((end - start) / n_iters) * 1000
    print(f"Mean Inference Latency: {avg_ms:.3f} ms")

if __name__ == '__main__':
    measure_latency()
