import unittest
from src.reinforcement.feedback_event import FeedbackEvent
from src.reinforcement.reinforcement_engine import ConfidenceWeightedReinforcementEngine

class TestReinforcementEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ConfidenceWeightedReinforcementEngine(alpha=2.0)

    def test_agree_proposal(self):
        event = FeedbackEvent(event_id="e1", action_id="a1", feedback_type="AGREE", action_confidence=0.8)
        proposal = self.engine.compute_proposal(event)
        self.assertEqual(proposal.target, "alert_preference")
        self.assertGreater(proposal.delta, 0.0)  # Positive delta for AGREE

    def test_disagree_proposal(self):
        event = FeedbackEvent(event_id="e2", action_id="a2", feedback_type="DISAGREE", action_confidence=0.8)
        proposal = self.engine.compute_proposal(event)
        self.assertLess(proposal.delta, 0.0)  # Negative delta for DISAGREE

    def test_unsure_zero_delta(self):
        event = FeedbackEvent(event_id="e3", action_id="a3", feedback_type="UNSURE", action_confidence=0.9)
        proposal = self.engine.compute_proposal(event)
        self.assertEqual(proposal.delta, 0.0)  # UNSURE must yield zero delta

if __name__ == "__main__":
    unittest.main()
