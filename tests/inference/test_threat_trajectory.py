import unittest
from src.inference.threat_trajectory import ThreatTrajectoryEngine

class TestThreatTrajectoryEngine(unittest.TestCase):
    def test_stationary_probability(self):
        engine = ThreatTrajectoryEngine()
        s1 = engine.update(1000.0, 0.2)
        s2 = engine.update(1001.0, 0.2)
        self.assertAlmostEqual(s2.probability_velocity, 0.0)
        self.assertAlmostEqual(s2.probability_acceleration, 0.0)
        self.assertEqual(s2.current_probability, 0.2)

    def test_rising_probability(self):
        engine = ThreatTrajectoryEngine()
        engine.update(1000.0, 0.2)
        s2 = engine.update(1001.0, 0.5)
        self.assertGreater(s2.probability_velocity, 0.0)
        self.assertGreater(s2.escalation_score, 0.0)

    def test_timestamp_irregularity_and_zero_dt(self):
        engine = ThreatTrajectoryEngine()
        engine.update(1000.0, 0.2)
        # Zero dt check
        s2 = engine.update(1000.0, 0.4)
        self.assertEqual(s2.current_probability, 0.4)
        
        # Negative dt check
        s3 = engine.update(999.0, 0.5)
        self.assertEqual(s3.current_probability, 0.5)

    def test_invalid_probabilities_and_nans(self):
        engine = ThreatTrajectoryEngine()
        engine.update(1000.0, 0.3)
        
        # NaN input
        s_nan = engine.update(1001.0, float('nan'))
        self.assertEqual(s_nan.current_probability, 0.3) # Falls back safely
        
        # Out-of-bounds probability
        s_out = engine.update(1002.0, 1.5)
        self.assertEqual(s_out.current_probability, 0.3)

    def test_reset_isolation(self):
        engine = ThreatTrajectoryEngine()
        engine.update(1000.0, 0.8)
        engine.update(1001.0, 0.9)
        
        engine.reset()
        s_reset = engine.update(1002.0, 0.1)
        self.assertAlmostEqual(s_reset.probability_velocity, 0.0)
        self.assertEqual(s_reset.current_probability, 0.1)

    def test_deterministic_replay(self):
        sequence = [(1000.0 + i * 100, 0.1 * i) for i in range(5)]
        
        engine1 = ThreatTrajectoryEngine()
        res1 = [engine1.update(t, p) for t, p in sequence]
        
        engine2 = ThreatTrajectoryEngine()
        res2 = [engine2.update(t, p) for t, p in sequence]
        
        for r1, r2 in zip(res1, res2):
            self.assertEqual(r1.current_probability, r2.current_probability)
            self.assertEqual(r1.probability_velocity, r2.probability_velocity)
            self.assertEqual(r1.escalation_score, r2.escalation_score)

if __name__ == "__main__":
    unittest.main()
