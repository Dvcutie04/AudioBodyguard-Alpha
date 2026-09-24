from typing import List, Dict
from inference.hypothesis import Hypothesis

class HypothesisReservoir:
    def __init__(self, max_size: int = 6):
        self.max_size = max_size
        self._hypotheses = {"H1": Hypothesis("H1", "Benign", 0.2), "H2": Hypothesis("H2", "Mechanical", 0.2), "H3": Hypothesis("H3", "Human", 0.2), "H4": Hypothesis("H4", "Anomalous", 0.2), "H5": Hypothesis("H5", "Unknown", 0.2)}
        self._normalize()
    def _normalize(self):
        total = sum(h.probability for h in self._hypotheses.values())
        if total > 0:
            for h in self._hypotheses.values(): h.probability /= total
    def update(self, likelihoods: Dict[str, float]):
        for hid, l_val in likelihoods.items():
            if hid in self._hypotheses: self._hypotheses[hid].probability *= max(0.0, l_val)
        self._normalize()
    def get_ranked(self) -> List[Hypothesis]:
        return sorted(self._hypotheses.values(), key=lambda h: h.probability, reverse=True)
    def top(self) -> Hypothesis:
        return self.get_ranked()[0]
