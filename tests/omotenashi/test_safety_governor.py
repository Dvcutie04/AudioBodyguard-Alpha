from unittest import TestCase
from src.omotenashi.conversation_policy import ConversationPolicyEvaluation, PolicyAction
from src.omotenashi.safety_governor import SafetyGovernor, GovernorDecision

class TestSafetyGovernor(TestCase):
    def setUp(self):
        self.governor = SafetyGovernor(max_allowed_attenuation=0.95)

    def test_governor_permits_valid_protection(self):
        eval_policy = ConversationPolicyEvaluation(
            action=PolicyAction.ACTIVATE_PROTECTION,
            attenuation_level=0.85,
            reason="Test proposal"
        )
        result = self.governor.enforce(eval_policy)
        self.assertEqual(result.decision, GovernorDecision.PERMIT)
        self.assertEqual(result.approved_action, PolicyAction.ACTIVATE_PROTECTION)
        self.assertEqual(result.attenuation_level, 0.85)
        self.assertTrue(len(result.audit_trail) > 0)

    def test_governor_blocks_excessive_attenuation(self):
        eval_policy = ConversationPolicyEvaluation(
            action=PolicyAction.ACTIVATE_PROTECTION,
            attenuation_level=0.99, # Exceeds max_allowed_attenuation of 0.95
            reason="Unsafe high attenuation"
        )
        result = self.governor.enforce(eval_policy)
        self.assertEqual(result.decision, GovernorDecision.BLOCK)
        self.assertEqual(result.approved_action, PolicyAction.MAINTAIN_BASELINE)
        self.assertEqual(result.attenuation_level, 0.0)

    def test_governor_permits_baseline(self):
        eval_policy = ConversationPolicyEvaluation(
            action=PolicyAction.MAINTAIN_BASELINE,
            attenuation_level=0.0,
            reason="Suppressed conversation"
        )
        result = self.governor.enforce(eval_policy)
        self.assertEqual(result.decision, GovernorDecision.PERMIT)
        self.assertEqual(result.approved_action, PolicyAction.MAINTAIN_BASELINE)

if __name__ == "__main__":
    import unittest
    unittest.main()
