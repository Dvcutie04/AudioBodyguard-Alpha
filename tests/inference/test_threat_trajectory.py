import unittest
from src.inference.threat_trajectory import ThreatTrajectoryEngine


class TestThreatTrajectory(unittest.TestCase):
    def setUp(self):
        self.engine = ThreatTrajectoryEngine()

    def test_initial_state(self):
        state = self.engine.update(1000.0, 0.5)
        self.assertEqual(state.current_probability, 0.5)
        self.assertEqual(state.probability_velocity, 0.0)
        self.assertEqual(state.probability_acceleration, 0.0)
        self.assertEqual(state.trend, "stable")

    def test_escalation_and_deescalation(self):
        self.engine.update(1000.0, 0.2)
        state_esc = self.engine.update(1001.0, 0.8)
        self.assertGreater(state_esc.probability_velocity, 0.0)
        self.assertEqual(state_esc.trend, "escalating")

        state_deesc = self.engine.update(1002.0, 0.3)
        self.assertLess(state_deesc.probability_velocity, 0.0)
        self.assertEqual(state_deesc.trend, "de-escalating")

    def test_invalid_probabilities_and_nans(self):
        self.engine.update(1000.0, 0.3)
        
        # Test clamping upper bound (1.5 clamped to 1.0)
        s_out = self.engine.update(1002.0, 1.5)
        self.assertEqual(s_out.current_probability, 1.0)

        # Test NaN fallback to previous valid state
        s_nan = self.engine.update(1003.0, float("nan"))
        self.assertEqual(s_nan.current_probability, 1.0)

    def test_reset(self):
        self.engine.update(1000.0, 0.5)
        self.engine.update(1001.0, 0.8)
        self.engine.reset()
        
        # After reset, trajectory acts as a new sequence
        state = self.engine.update(1002.0, 0.2)
        self.assertEqual(state.probability_velocity, 0.0)
        self.assertEqual(state.trend, "stable")
