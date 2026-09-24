import unittest
from src.policy.context_profiles import ContextProfileManager
from src.policy.hysteresis import PolicyHysteresisFilter
class TestContextAndHysteresis(unittest.TestCase):
    def test_context_switching(self):
        mgr = ContextProfileManager("home")
        self.assertEqual(mgr.active_context, "home")
        profile = mgr.get_active_profile()
        self.assertEqual(profile.sensitivity_offset, -5.0)
        mgr.set_context("vehicle")
        self.assertEqual(mgr.active_context, "vehicle")
        self.assertEqual(mgr.get_active_profile().attenuation_multiplier, 1.2)
    def test_hysteresis_behavior(self):
        f = PolicyHysteresisFilter(upper_threshold=0.8, lower_threshold=0.3)
        self.assertFalse(f.evaluate_transition(0.5))
        self.assertFalse(f.evaluate_transition(0.79))
        self.assertTrue(f.evaluate_transition(0.85))
        self.assertTrue(f.evaluate_transition(0.4))
        self.assertFalse(f.evaluate_transition(0.2))
if __name__ == "__main__":
    unittest.main()
