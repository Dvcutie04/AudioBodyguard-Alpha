import unittest
from src.safety.policy_stability_monitor import PolicyStabilityMonitor
from src.safety.architecture_invariants import ArchitectureInvariants

class TestAdaptiveResilience(unittest.TestCase):
    def test_stability_monitor_trip(self):
        monitor = PolicyStabilityMonitor(velocity_limit=10.0)
        monitor.record_step(50.0)
        monitor.record_step(52.0)
        metrics = monitor.record_step(75.0)
        self.assertTrue(metrics.circuit_breaker_tripped)
        self.assertEqual(metrics.controller_status, "ADAPTATION_PAUSED")

    def test_architecture_invariants(self):
        self.assertTrue(ArchitectureInvariants.assert_bounds(50.0))
        self.assertFalse(ArchitectureInvariants.assert_bounds(105.0))
        self.assertTrue(ArchitectureInvariants.assert_safety_retention(50.0, 50.0))
        self.assertTrue(ArchitectureInvariants.assert_monotonic_version(1, 2))
        self.assertTrue(ArchitectureInvariants.assert_side_effect_free(False))

if __name__ == "__main__":
    unittest.main()
