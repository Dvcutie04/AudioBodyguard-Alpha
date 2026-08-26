from unittest import TestCase
from src.omotenashi.hypothesis_gate import (
    HypothesisGateResult,
    GateDecision,
    Hypothesis
)
from src.omotenashi.conversation_policy import (
    ConversationPolicy,
    PolicyAction
)

class TestConversationPolicy(TestCase):
    def setUp(self):
        self.policy = ConversationPolicy(
            default_attenuation=0.0,
            protected_attenuation=0.85
        )

    def test_policy_activates_protection_on_propose(self):
        gate_result = HypothesisGateResult(
            decision=GateDecision.PROPOSE,
            conversation_probability=0.90,
            competing_hypothesis=Hypothesis.MEDIA_DIALOGUE,
            competing_probability=0.20,
            confidence_margin=0.70
        )
        evaluation = self.policy.evaluate(gate_result)
        self.assertEqual(evaluation.action, PolicyAction.ACTIVATE_PROTECTION)
        self.assertEqual(evaluation.attenuation_level, 0.85)

    def test_policy_maintains_baseline_on_suppress(self):
        gate_result = HypothesisGateResult(
            decision=GateDecision.SUPPRESS,
            conversation_probability=0.50,
            competing_hypothesis=Hypothesis.MEDIA_DIALOGUE,
            competing_probability=0.60,
            confidence_margin=-0.10
        )
        evaluation = self.policy.evaluate(gate_result)
        self.assertEqual(evaluation.action, PolicyAction.MAINTAIN_BASELINE)
        self.assertEqual(evaluation.attenuation_level, 0.0)

    def test_invalid_attenuation_bounds(self):
        with self.assertRaises(ValueError):
            ConversationPolicy(default_attenuation=1.5)
        with self.assertRaises(ValueError):
            ConversationPolicy(protected_attenuation=-0.1)

if __name__ == "__main__":
    import unittest
    unittest.main()
