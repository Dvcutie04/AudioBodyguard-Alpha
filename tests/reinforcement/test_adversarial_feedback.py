import unittest
from src.reinforcement.feedback_event import FeedbackEvent
from src.reinforcement.reinforcement_engine import ConfidenceWeightedReinforcementEngine

class TestAdversarialFeedback(unittest.TestCase):
    def setUp(self):
        self.engine = ConfidenceWeightedReinforcementEngine(alpha=2.0)

    def test_feedback_flood_disagree(self):
        # 10,000 DISAGREE events must remain bounded and stable
        for i in range(10000):
            event = FeedbackEvent(event_id=f"flood_{i}", action_id="a1", feedback_type="DISAGREE", action_confidence=0.9)
            proposal = self.engine.compute_proposal(event)
            self.assertLess(proposal.delta, 0.0)

    def test_alternating_feedback(self):
        # Alternating AGREE / DISAGREE
        types = ["AGREE", "DISAGREE"] * 500
        for i, f_type in enumerate(types):
            event = FeedbackEvent(event_id=f"alt_{i}", action_id="a1", feedback_type=f_type, action_confidence=0.8)
            proposal = self.engine.compute_proposal(event)
            if f_type == "AGREE":
                self.assertGreater(proposal.delta, 0.0)
            else:
                self.assertLess(proposal.delta, 0.0)

    def test_extreme_ratings(self):
        # Extreme rating bounds check
        ratings = [1.0, 100.0, 1.0, 100.0]
        for i, r in enumerate(ratings):
            event = FeedbackEvent(event_id=f"ext_{i}", action_id="a1", feedback_type="AGREE", rating=r, action_confidence=0.8)
            proposal = self.engine.compute_proposal(event)
            self.assertGreater(proposal.delta, 0.0)

if __name__ == "__main__":
    unittest.main()
