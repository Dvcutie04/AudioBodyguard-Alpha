import time
from aqss_phase1_core import BayesianThreatEngine, AcousticObservation
from aqss_quantum_lab.results_schema import ModelOutput

class ClassicalReferenceRunner:
    def __init__(self, prior: float = 0.85):
        self.engine = BayesianThreatEngine(pr=prior)

    def run(self, sample_id: str, obs: AcousticObservation) -> ModelOutput:
        start_time = time.perf_counter_ns()
        inf = self.engine.infer(obs)
        elapsed_us = (time.perf_counter_ns() - start_time) / 1000.0
        return ModelOutput(p_threat=inf["p_threat"], latency_us=round(elapsed_us, 2))
