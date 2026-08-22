class PredictiveHorizon:
    def __init__(self, history_size=5, risk_threshold=0.05):
        self.history_size = history_size
        self.risk_threshold = risk_threshold
        self.energy_history = []

    def update_and_predict(self, features):
        energy = features.get("energy", 0.0)
        self.energy_history.append(energy)
        if len(self.energy_history) > self.history_size:
            self.energy_history.pop(0)

        if len(self.energy_history) < 2:
            return {"trajectory": "STABLE", "risk_score": 0.0, "predicted_energy": energy}

        velocity = self.energy_history[-1] - self.energy_history[-2]
        predicted_energy = energy + velocity
        risk_score = min(max(predicted_energy / self.risk_threshold, 0.0), 1.0)

        trajectory = "RISING_THREAT" if velocity > 0.01 else ("STABLE" if abs(velocity) <= 0.01 else "DECAYING")
        return {
            "trajectory": trajectory,
            "risk_score": risk_score,
            "predicted_energy": predicted_energy
        }
