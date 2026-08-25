from typing import List, Dict
from inference.hypothesis import Hypothesis

class HypothesisReservoir:
    def __init__(self, max_size: int = 6):
        self.max_size = max_size
        self._hypotheses: Dict[str, Hypothesis] = {
            "H1": Hypothesis("H1", "Benign environmental transition", 0.2),
            "H2": Hypothesis("H2", "Mechanical source", 0.2),
            "H3": Hypothesis("H3", "Human-generated event", 0.2),
            "H4": Hypothesis("H4", "Persistent anomalous source", 0.2),
            "H5": Hypothesis("H5", "Unknown / Out-of-distribution", 0.2),
        }
        self._normalize()

    def _normalize(self):
        total = sum(h.probability for h in self._hypotheses.values())
        if total > 0:
            for h in self._hypotheses.values():
                h.probability /= total

    def update(self, likelihoods: Dict[str, float]):
        """Updates hypothesis probabilities using Bayesian likelihood weighting."""
        for hid, l_val in likelihoods.items():
            if hid in self._hypotheses:
                self._hypotheses[hid].probability *= max(0.0, l_val)
        self._normalize()

    def get_ranked(self) -> List[Hypothesis]:
        return sorted(self._hypotheses.values(), key=lambda h: h.probability, reverse=True)

    def top(self) -> Hypothesis:
        return self.get_ranked()[0]
