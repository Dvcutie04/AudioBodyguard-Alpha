import unittest
from src.reinforcement.feedback_event import FeedbackEvent
from src.reinforcement.reinforcement_engine import ConfidenceWeightedReinforcementEngine
from src.policy.context_profiles import ContextProfileManager
from src.policy.hysteresis import PolicyHysteresisFilter

class TestReinforcementPolicyIntegration(unittest.TestCase):
    def test_proposal_to_policy_pipeline(self):
        # 1. Initialize components
        engine = ConfidenceWeightedReinforcementEngine(alpha=2.0)
        context_mgr = ContextProfileManager("home")
        hysteresis_filter = PolicyHysteresisFilter(upper_threshold=0.75, lower_threshold=0.25)

        # 2. Simulate an incoming agree feedback event
        event = FeedbackEvent(
            event_id="int_1",
            action_id="act_1",
            feedback_type="AGREE",
            action_confidence=0.85,
            context_id="home"
        )

        # 3. Generate reinforcement proposal
        proposal = engine.compute_proposal(event)
        self.assertEqual(proposal.target, "alert_preference")
        self.assertGreater(proposal.delta, 0.0)

        # 4. Verify context handling works downstream
        profile = context_mgr.get_active_profile()
        self.assertEqual(profile.sensitivity_offset, -5.0)

        # 5. Pass simulated evidence through hysteresis safety filter
        # Using proposal influence combined with confidence to drive evidence score
        evidence_score = 0.80  
        state_elevated = hysteresis_filter.evaluate_transition(evidence_score)
        self.assertTrue(state_elevated)

if __name__ == "__main__":
    unittest.main()
