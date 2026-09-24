import unittest
from src.inference.threat_inference import ThreatInferenceEngine
from src.inference.evidence_vector import EvidenceVector
class TestThreatInference(unittest.TestCase):
    def test_all(self):
        engine = ThreatInferenceEngine()
        ev = EvidenceVector(0.5, 0.2, 0.1, 0.5, 0.5, 0.1, 0.1, 0.2)
        stats = {"clipping_ratio": 0.0, "acoustic_energy": 0.5}
        
        r1 = engine.evaluate("e1", 1000.0, stats, ev)
        engine.accumulator.reset()
        r2 = engine.evaluate("e1", 1000.0, stats, ev)
        self.assertEqual(r1.threat_probability, r2.threat_probability)
        
        bad = engine.evaluate("e2", 1000.0, {"clipping_ratio": 0.2}, ev)
        self.assertFalse(bad.sensor_quality_ok)
if __name__ == "__main__":
    unittest.main()
