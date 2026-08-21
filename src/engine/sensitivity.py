from dataclasses import dataclass

LATENCY_WEIGHTS = [0.05, 0.10, 0.15, 0.20, 0.25]
SHOT_WEIGHTS = [0.05, 0.10, 0.15, 0.20]

@dataclass(frozen=True)
class SweepResult:
    weight_latency: float
    weight_shots: float
    classical_quality: float
    quantum_quality: float
    quality_delta: float
    latency_multiple: float
    shot_cost: int
    classical_composite: float
    quantum_composite: float
    composite_delta: float
    winner: str

def diagnostic(c, q, wl, ws):
    clat = max(float(c.latency_ms), 1e-9)
    qlat = float(q.latency_ms)
    cq = max(0.0, 1.0 - (2.0 * getattr(c, 'fpr', 0.0) + 1.0 * getattr(c, 'fnr', 0.0)))
    qq = max(0.0, 1.0 - (2.0 * getattr(q, 'fpr', 0.0) + 1.0 * getattr(q, 'fnr', 0.0)))
    return SweepResult(wl, ws, cq, qq, qq-cq, qlat/clat, int(q.shots), float(c.composite_score), float(q.composite_score), float(q.composite_score)-float(c.composite_score), 'QUANTUM' if q.composite_score > c.composite_score else 'CLASSICAL')

def run_sweep(evaluator):
    results = []
    for wl in LATENCY_WEIGHTS:
        for ws in SHOT_WEIGHTS:
            _, classical, quantum, *_ = evaluator(wl, ws)
            results.append(diagnostic(classical, quantum, wl, ws))
    return results
