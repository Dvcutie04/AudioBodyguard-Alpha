from src.engine.benchmark import BenchmarkHarness, MetricPolicy
import random
random.seed(42)
yt = [random.choice([0, 1]) for _ in range(1000)]
cp = [t if random.random() > 0.06 else 1-t for t in yt]
c_data = {"y_true": yt, "y_pred": cp, "y_prob": [0.9 if p==1 else 0.1 for p in cp], "shots": 0, "latency": 0.8}
qp = [t if random.random() > 0.04 else 1-t for t in yt]
q_data = {"y_true": yt, "y_pred": qp, "y_prob": [0.95 if p==1 else 0.05 for p in qp], "shots": 2048, "latency": 143.0}
h = BenchmarkHarness()
bid, c_res, q_res = h.run_faceoff("synth_eval_001", c_data, q_data)
print(f"\nBENCHMARK ID: {bid}")
print(f"POLICY:       {MetricPolicy().version}")
print("-" * 50)
print("                 CLASSICAL       QUANTUM")
print("                 ---------       -------")
print(f"Accuracy           {c_res.accuracy*100:2.1f}%          {q_res.accuracy*100:2.1f}%")
print(f"FPR                {c_res.fpr*100:2.1f}%           {q_res.fpr*100:2.1f}%")
print(f"FNR                {c_res.fnr*100:2.1f}%           {q_res.fnr*100:2.1f}%")
print(f"Brier              {c_res.brier_score:.3f}           {q_res.brier_score:.3f}")
print(f"Shots              {c_res.shots}               {q_res.shots}")
print(f"Latency            {c_res.latency_ms} ms          {q_res.latency_ms} ms")
print(f"Composite Score    {c_res.composite_score:.3f}           {q_res.composite_score:.3f}")
print("-" * 50)
print(f"CANDIDATE OUTCOME:   {q_res.decision}\n")
