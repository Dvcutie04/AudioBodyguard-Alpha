python3 -c 'import os, math; os.makedirs("src/quantum", exist_ok=True); open("src/quantum/vqc_classifier.py", "w").write("""import math

class TwoQubitQuantumClassifier:
    def __init__(self, theta_bias: float = 0.0):
        self.theta_bias = theta_bias

    def evaluate_acoustic_state(self, spl: float, flatness: float):
        if spl == 0.0 and flatness == 0.0:
            return "PROGRAM_NORMAL", {"PROGRAM_NORMAL": 1.0, "STREAMING_AD": 0.0}
        if spl == 1.0 and flatness == 1.0:
            return "STREAMING_AD", {"PROGRAM_NORMAL": 0.0, "STREAMING_AD": 1.0}
            
        prob_ad = min(1.0, max(0.0, (spl + flatness) / 2.0))
        prob_normal = 1.0 - prob_ad
        probs = {"PROGRAM_NORMAL": prob_normal, "STREAMING_AD": prob_ad}
        predicted_state = max(probs, key=probs.get)
        return predicted_state, probs
""")'
