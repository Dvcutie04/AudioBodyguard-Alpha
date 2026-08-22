import numpy as np
from src.research_loop.mitigation import ZeroNoiseExtrapolator

def run_session_3():
    extrapolator = ZeroNoiseExtrapolator(scale_factors=[1.0, 3.0, 5.0])
    true_fidelity = 0.9500
    
    # Simulate hardware noise scaled up across factors
    noisy_measurements = [0.8800, 0.7400, 0.5200]
    raw_value = noisy_measurements[0]
    
    mitigated_value = extrapolator.extrapolate(noisy_measurements)
    gain = extrapolator.compute_mitigation_gain(raw_value, mitigated_value, true_fidelity)
    
    print(f"[SESSION 3 COMPLETE] ZNE Error Mitigation Benchmarked.")
    print(f"Raw Noisy Value (Scale 1.0): {raw_value:.4f}")
    print(f"ZNE Extrapolated Value (Scale 0.0): {mitigated_value:.4f}")
    print(f"Target True Fidelity: {true_fidelity:.4f}")
    print(f"Mitigation Error Reduction Gain: {gain:.2f}%")

if __name__ == "__main__":
    run_session_3()
