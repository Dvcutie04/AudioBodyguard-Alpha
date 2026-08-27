from dataclasses import dataclass


@dataclass
class ChangePointEvidence:
    timestamp: float = 0.0
    change_score: float = 0.0


class BayesianAdapter:
    def __init__(self):
        self.prior = 0.5

    def update(self, evidence: ChangePointEvidence) -> float:
        return self.prior
