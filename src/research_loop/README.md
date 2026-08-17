# AQSS-36-OMEGA – Research Loop Subsystem

This directory houses the asynchronous research tools, dataset extraction scripts, and IBM Quantum evaluation pipelines for **Project AQSS-36-OMEGA**.

---

### � Subsystem Architecture & Purpose
* **Real-time Authority**: The core `DSP-Bayesian-FSM` engine remains the sole real-time authority (10 ms latency budget).
* **Asynchronous Research Role**: IBM Quantum execution is strictly relegated to this background research loop for off-line model candidate generation and tail-case analysis.

---

### 8�� Benchmark Baseline (20-Point Sweep)
* **Tested Configuration**: $5 \times \text{Latency Weights } [0.05 - 0.25] \times 4 \times \text{Shot Weights } [0.05 - 0.20]$.
* **Sweep Outcome**: Classical path dominated 100% of policy configurations due to quantum shot/latency overhead.
* **Core Constraint**: Quantum probability edge (0.95/0.05) vs (0.90/0.10)) is consistently swallowed by execution overhead (25l ms vs 10 ms; 1024 shots vs 1).

---

### 𝌂 Directory Layout
* `hard_cases.py` — Extracts ambiguous acoustic tail samples (confidence \in [0.40, 0.90]).
* `qkernel.py` — Fidelity Quantum Kernel + Classical SVM
classification pipeline.
* `mitigation.py` — Zero-Noise Extrapolation (ZNE) error mitigation benchmarking.
* `datasets/` — Isolated storage for extracted ambiguous acoustic feature vectors.
