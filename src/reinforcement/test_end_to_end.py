import unittest
from src.reinforcement.feedback_event import FeedbackEvent
from src.reinforcement.reinforcement_engine import ConfidenceWeightedReinforcementEngine
from src.policy.context_profiles import ContextProfileManager
from src.policy.hysteresis import PolicyHysteresisFilter

class TestEndtoEndReinforcementPipeline(unittest.TestCase):
    def test_full_pipeline_governor_boundary(self):
        # 1. Initialize complete stack
        engine = ConfidenceWeightedReinforcementEngine(alpha=2.0)
        context_mgr = ContextProfileManager("home")
        hysteresis_filter = PolicyHysteresisFilter(upper_threshold=0.75, lower_threshold=0.25)

        # 2. Simulate user agreeing with an action under high confidence
        event = FeedbackEvent(
            event_id="e2e_01",
            action_id="act_99",
            feedback_type="AGREE",
            action_confidence=0.90,
            context_id="home"
        )

        # 3. Inference -> Feedback -> Proposal
        proposal = engine.compute_proposal(event)
        self.assertEqual(proposal.target, "alert_preference")
        self.assertGreater(proposal.delta, 0.0)

        # 4. Validation & Policy Check (Simulating transactional admission)
        admissible = proposal.confidence >= 0.5 and proposal.delta != 0.0
        self.assertTrue(admissible)

        # 5. Safety Governor / Hysteresis Evaluation
        evidence_score = 0.85
        is_safe_elevated = hysteresis_filter.evaluate_transition(evidence_score)
        self.assertTrue(is_safe_elevated)

if __name__ == "__main__":
    unittest.main()
