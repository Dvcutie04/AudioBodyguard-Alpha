import time
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AcousticObservation:
    rms: float
    peak: float
    spectral_centroid: float
    zcr: float
    db_level: float

class BayesianThreatEngine:
    def __init__(self, pr: float = 0.85):
        self.pr = pr  # Prior threat probability

    def infer(self, obs: AcousticObservation) -> Dict[str, Any]:
        # Simple Bayesian likelihood weighting based on acoustic spikes
        likelihood = min(1.0, (obs.rms * 0.4) + (obs.peak * 0.4) + (obs.db_level / 100.0 * 0.2))
        p_threat = (likelihood * self.pr) / ((likelihood * self.pr) + ((1 - likelihood) * (1 - self.pr)))
        return {"p_threat": round(float(p_threat), 4), "likelihood": round(float(likelihood), 4)}
