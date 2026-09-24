class PolicyHysteresisFilter:
    def __init__(self, upper_threshold: float = 0.75, lower_threshold: float = 0.25):
        self.upper_threshold = upper_threshold
        self.lower_threshold = lower_threshold
        self._state_elevated = False
    def evaluate_transition(self, evidence_score: float) -> bool:
        if not self._state_elevated and evidence_score >= self.upper_threshold:
            self._state_elevated = True
        elif self._state_elevated and evidence_score <= self.lower_threshold:
            self._state_elevated = False
        return self._state_elevated
