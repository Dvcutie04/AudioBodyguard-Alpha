import unittest
from src.shadow.shadow_policy import ShadowPolicyEngine
from src.shadow.rollback_manager import RollbackManager

class TestShadowAndRollback(unittest.TestCase):
    def test_shadow_side_effect_free(self):
        engine = ShadowPolicyEngine()
        curr = {"version": 1, "action": "monitor"}
        cand = {"version": 2, "action": "monitor"}
        deltas = {"notification": 0.0, "haptics": 0.0}
        
        result = engine.evaluate_shadow(curr, cand, deltas)
        self.assertFalse(result.action_changed)
        self.assertEqual(result.recommendation, "NO_MEANINGFUL_DIFFERENCE")

    def test_high_blast_radius_rejection(self):
        engine = ShadowPolicyEngine()
        curr = {"version": 1, "action": "monitor"}
        cand = {"version": 2, "action": "automate"}
        # Weights: notification=0.4, haptics=0.2, attenuation=0.2, automation=0.2
        # 0.4*20 + 0.2*20 = 8 + 4 = 12 > 10.0 threshold
        deltas = {"notification": 20.0, "automation": 20.0}
        
        result = engine.evaluate_shadow(curr, cand, deltas)
        self.assertEqual(result.recommendation, "REJECT_HIGH_BLAST_RADIUS")

    def test_rollback_preserves_history(self):
        manager = RollbackManager()
        s1 = manager.commit_version(1, {"sensitivity": 50}, "Initial")
        s2 = manager.commit_version(2, {"sensitivity": 70}, "First update")
        
        # Rollback P2 to P1 by creating P3
        s3 = manager.rollback_to(target_version=1, new_version=3)
        self.assertEqual(s3.version, 3)
        self.assertEqual(s3.parameters["sensitivity"], 50)
        self.assertEqual(len(manager.history), 3)  # P1, P2, and P3 preserved

if __name__ == "__main__":
    unittest.main()
