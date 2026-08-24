import unittest
from src.inference.threat_inference import ThreatInferenceEngine
from src.inference.evidence_vector import EvidenceVector

class TestThreatInference(unittest.TestCase):
    def test_deterministic_inference(self):
        engine = ThreatInferenceEngine()
        ev = EvidenceVector(0.5, 0.2, 0.1, 0.5, 0.5, 0.1, 0.1, 0.2)
        stats = {"clipping_ratio": 0.0, "acoustic_energy": 0.5}
        
        r1 = engine.evaluate("e1", 1000.0, stats, ev)
        engine.accumulator.reset()
        r2 = engine.evaluate("e1", 1000.0, stats, ev)
        self.assertEqual(r1.threat_probability, r2.threat_probability)
        self.assertEqual(r1.semantic_state, r2.semantic_state)

    def test_sensor_failure_gate(self):
        engine = ThreatInferenceEngine()
        ev = EvidenceVector(0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9)
        bad_stats = {"clipping_ratio": 0.2, "acoustic_energy": 0.5}
        res = engine.evaluate("e2", 1000.0, bad_stats, ev)
        self.assertFalse(res.sensor_quality_ok)
        self.assertEqual(res.semantic_state, "UNKNOWN")

    def test_temporal_continuity(self):
        engine = ThreatInferenceEngine()
        ev_normal = EvidenceVector(0.1, 0.1, 0.1, 0.5, 0.5, 0.1, 0.0, 0.1)
        ev_spike = EvidenceVector(0.9, 0.9, 0.9, 0.5, 0.5, 0.9, 0.9, 0.9)
        stats = {"clipping_ratio": 0.0, "acoustic_energy": 0.5}
        
        engine.accumulator.reset()
        r_norm = engine.evaluate("e3", 1000.0, stats, ev_normal)
        r_spike_1 = engine.evaluate("e4", 1001.0, stats, ev_spike)
        self.assertLess(r_spike_1.threat_probability, 0.9)

if __name__ == "__main__":
    unittest.main()
