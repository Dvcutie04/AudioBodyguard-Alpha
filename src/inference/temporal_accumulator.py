class TemporalEvidenceAccumulator:
    def __init__(self, decay_factor: float = 0.7):
        self.decay_factor = decay_factor
        self._current_probability = 0.0

    def update(self, instantaneous_p: float) -> float:
        self._current_probability = (self.decay_factor * self._current_probability) + ((1.0 - self.decay_factor) * instantaneous_p)
        return max(0.0, min(1.0, self._current_probability))

    def reset(self):
        self._current_probability = 0.0
