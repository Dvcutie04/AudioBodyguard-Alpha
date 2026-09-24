import math

class ChangePointSentinel:
    def __init__(self, window_size=10, threshold=3.0):
        self.window_size = window_size
        self.threshold = threshold
        self.history = []
        self.persistence_counter = 0

    def update(self, value: float):
        if value is None or math.isnan(value) or math.isinf(value):
            return {"detected": False, "direction": 0, "score": 0.0, "confidence": 0.0, "persistence": 0}
        self.history.append(value)
        if len(self.history) > self.window_size:
            self.history.pop(0)
        if len(self.history) < self.window_size:
            return {"detected": False, "direction": 0, "score": 0.0, "confidence": 0.0, "persistence": 0}
        mean = sum(self.history) / len(self.history)
        variance = sum((x - mean) ** 2 for x in self.history) / len(self.history)
        std_dev = math.sqrt(variance)
        if std_dev == 0.0:
            return {"detected": False, "direction": 0, "score": 0.0, "confidence": 0.0, "persistence": 0}
        z_score = (self.history[-1] - mean) / std_dev
        detected = abs(z_score) >= self.threshold
        direction = 1 if z_score > 0 else (-1 if z_score < 0 else 0)
        if detected:
            self.persistence_counter += 1
        else:
            self.persistence_counter = max(0, self.persistence_counter - 1)
        return {"detected": detected, "direction": direction, "score": min(1.0, abs(z_score) / (self.threshold * 2.0)), "confidence": 0.9, "persistence": self.persistence_counter}

    def reset(self):
        self.history = []
        self.persistence_counter = 0
