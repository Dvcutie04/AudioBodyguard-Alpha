import importlib
import src.engine.sensitivity as s
from src.engine.benchmark import BenchmarkHarness, MetricPolicy

importlib.reload(s)
h = BenchmarkHarness()

cd = {
    'y_true': [1, 0, 1, 0],
    'y_pred': [1, 0, 1, 0],
    'y_prob': [0.9, 0.1, 0.8, 0.2],
    'latency_ms': 10,
    'shots': 1
}

qd = {
    'y_true': [1, 0, 1, 0],
    'y_pred': [1, 0, 1, 0],
    'y_prob': [0.95, 0.05, 0.9, 0.1],
    'latency_ms': 25,
    'shots': 1024
}

ev = lambda wl, ws: h.run_faceoff('ds1', cd, qd, MetricPolicy(weight_latency=wl, weight_shots=ws))

res = s.run_sweep(ev)

header = f"{'WL':<6} | {'WS':<6} | {'WINNER':<10} | {'C_COMP':<10} | {'Q_COMP':<10} | {'DELTA':<10}"
print(header)
print('-' * len(header))
for r in res:
    print(f"{r.weight_latency:06.2f} | {r.weight_shots:<6.2f} | {r.winner:<10} | {r.classical_composite:<10.4f} | {r.quantum_composite:<10.4f} | {r.composite_delta:<10.4f}")
