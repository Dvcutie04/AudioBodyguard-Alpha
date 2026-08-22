import numpy as np

class ZeroNoiseExtrapolator:
    def __init__(self, scale_factors=[1.0, 3.0, 5.0]):
        self.scale_factors = scale_factors

    def extrapolate(self, noisy_values):
        # Fit a 2nd degree polynomial to extrapolate noise back to scale factor 0.0
        coeffs = np.polyfit(self.scale_factors, noisy_values, 2)
        mitigated_value = np.polyval(coeffs, 0.0)
        return mitigated_value

    def compute_mitigation_gain(self, raw_val, mitigated_val, true_val):
        raw_err = abs(raw_val - true_val)
        mit_err = abs(mitigated_val - true_val)
        gain = ((raw_err - mit_err) / raw_err) * 100 if raw_err > 0 else 0.0
        return max(gain, 0.0)
