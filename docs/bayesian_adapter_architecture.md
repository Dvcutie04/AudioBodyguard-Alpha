# Audio Bodyguard (AQSS-36-OMEGA): Bayesian Adapter Architecture

## Overview
The `BayesianAdapter` and `ChangePointEvidence` classes provide real-time probabilistic threat fusion for ambient acoustic streams. By combining prior threat beliefs with multi-factor evidence matrices, the system dynamically scales threat posture while maintaining strict numerical stability.

---

## Mathematical Formulation
Given a prior probability $P(\text{Prior})$ and incoming change-point evidence $E$, the adjustment factor is computed as:

$$\text{Adjustment} = M \times P_s \times C \times Q_s$$

Where:
- $M$: Magnitude of the acoustic shift $[0.0, 1.0]$
- $P_s$: Persistence metric $[0.0, 1.0]$
- $C$: Evidence confidence score $[0.0, 1.0]$
- $Q_s$: Sensor quality coefficient $[0.0, 1.0]$

Posterior probability updates directionally:
- **Threat Escalation ($\text{Direction} > 0$):**
  $$P(\text{Posterior}) = P(\text{Prior}) \times (1.0 - 0.5 \times \text{Adjustment})$$
- **Threat Mitigation / Benign ($\text{Direction} \le 0$):**
  $$P(\text{Posterior}) = P(\text{Prior}) + (1.0 - P(\text{Prior})) \times 0.5 \times \text{Adjustment}$$

---

## Safety & Invariants
- **NaN Guard:** Validates all inputs to ensure float calculations never propagate `NaN` states.
- **Bounds Checking:** Enforces strict $[0.0, 1.0]$ boundaries on all evidence parameters, throwing a `ValueError` on violation.
