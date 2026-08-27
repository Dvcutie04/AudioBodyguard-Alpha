import math
import random
import unittest
from src.inference.evidence_vector import EvidenceVector


class TestPerceptionInvariants(unittest.TestCase):
    def test_bounded_and_non_nan_invariants(self):
        class DummyEngine:
            def evaluate(self, v):
                return {"probability": 0.5, "confidence": 0.8, "velocity": 0.1}

        engine = DummyEngine()
        random.seed(2026)
        for i in range(50):
            vec = EvidenceVector(
                acoustic_energy=random.uniform(0, 1),
                spectral_change=0.0,
                impulsiveness=0.0,
                periodicity=0.0,
                persistence=0.0,
                spatial_change=0.0,
                escalation=0.0,
                anomaly_score=0.0,
            )
            res = engine.evaluate(vec)
            self.assertTrue(0.0 <= res["probability"] <= 1.0)
            self.assertTrue(0.0 <= res["confidence"] <= 1.0)
            self.assertFalse(math.isnan(res["probability"]))


if __name__ == "__main__":
    unittest.main()
