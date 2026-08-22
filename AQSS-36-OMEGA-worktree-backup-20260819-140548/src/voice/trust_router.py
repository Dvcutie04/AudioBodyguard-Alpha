class TrustGradientRouter:
    def __init__(self, energy_threshold=0.01, zcr_threshold=5):
        self.energy_threshold = energy_threshold
        self.zcr_threshold = zcr_threshold

    def evaluate(self, features):
        energy = features.get("energy", 0.0)
        zcr = features.get("zero_crossings", 0)
        if energy < self.energy_threshold:
            return {"route": "NOISE_GATE", "confidence": 0.99}
        elif zcr > self.zcr_threshold:
            return {"route": "HIGH_FREQUENCY_SPECULATIVE", "confidence": 0.75}
        return {"route": "DETERMINISTIC_PASS", "confidence": 0.95}
