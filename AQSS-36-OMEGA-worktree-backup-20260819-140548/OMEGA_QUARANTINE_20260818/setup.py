import os
os.makedirs("src/engine", exist_ok=True)
e = """import sqlite3, json, uuid
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class MetricPolicy:
    version: str = "v0.1"
    weight_quality: float = 0.50
    weight_calibration: float = 0.25
    weight_latency: float = 0.15
    weight_shots: float = 0.10
    max_allowed_fpr: float = 0.05
    max_allowed_fnr: float = 0.10
    max_allowed_shots: int = 8192
    min_improvement_delta: float = 0.02

@dataclass(frozen=True)
class BenchmarkResult:
    model_name: str
    samples: int
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    accuracy: float
    fpr: float
    fnr: float
    brier_score: float
    shots: int
    latency_ms: float
    composite_score: float
    decision: str

class BenchmarkHarness:
    def __init__(self, db_path="events.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS benchmark_log (
                benchmark_id TEXT PRIMARY KEY, dataset_id TEXT, benchmark_version TEXT,
                metric_policy_version TEXT, classical_result TEXT, quantum_result TEXT,
                decision TEXT, logged_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")

    def evaluate_model(self, name: str, data: dict, policy: MetricPolicy) -> BenchmarkResult:
        yt, yp, ypr = data["y_true"], data["y_pred"], data["y_prob"]
        samples = len(yt)
        tp = sum(1 for t, p in zip(yt, yp) if t == 1 and p == 1)
        fp = sum(1 for t, p in zip(yt, yp) if t == 0 and p == 1)
        tn = sum(1 for t, p in zip(yt, yp) if t == 0 and p == 0)
        fn = sum(1 for t, p in zip(yt, yp) if t == 1 and p == 0)
        acc = (tp + tn) / samples if samples else 0
        fpr = fp / (fp + tn) if (fp + tn) else 0
        fnr = fn / (fn + tp) if (fn + tp) else 0
        brier = sum((p - t)**2 for t, p in zip(yt, ypr)) / samples
        quality = max(0.0, 1.0 - (2.0 * fpr + 1.0 * fnr))
        calibration = max(0.0, 1.0 - brier)
        latency_eff = max(0.0, 1.0 - (data.get("latency", data.get("latency_ms", 0.0)) / 250.0))
        shot_eff = max(0.0, 1.0 - (data["shots"] / policy.max_allowed_shots))
        composite = (policy.weight_quality * quality) + (policy.weight_calibration * calibration) + (policy.weight_latency * latency_eff) + (policy.weight_shots * shot_eff)
        decision = "ACCEPT"
        if fpr > policy.max_allowed_fpr or fnr > policy.max_allowed_fnr or data["shots"] > policy.max_allowed_shots:
            decision = "REJECT"
        return BenchmarkResult(name, samples, tp, fp, tn, fn, acc, fpr, fnr, brier, data["shots"], data.get("latency", data.get("latency_ms", 0.0)), composite, decision)

    def run_faceoff(self, dataset_id: str, c_data: dict, q_data: dict, policy: MetricPolicy = MetricPolicy()):
        bench_id = f"bench_{uuid.uuid4().hex[:8]}"
        c_res = self.evaluate_model("CLASSICAL", c_data, policy)
        q_res = self.evaluate_model("QUANTUM", q_data, policy)
        final_decision = q_res.decision
        if final_decision == "ACCEPT" and q_res.composite_score <= c_res.composite_score + policy.min_improvement_delta:
            final_decision = "INCONCLUSIVE"
        q_res = BenchmarkResult(**{**asdict(q_res), "decision": final_decision})
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO benchmark_log VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", (bench_id, dataset_id, "v1.0", policy.version, json.dumps(asdict(c_res)), json.dumps(asdict(q_res)), final_decision))
        return bench_id, c_res, q_res
"""
open("src/engine/benchmark.py", "w").write(e)
