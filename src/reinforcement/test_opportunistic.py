import unittest
from src.reinforcement.opportunistic_feedback import PromptingController

class TestPromptingController(unittest.TestCase):
    def setUp(self):
        self.controller = PromptingController(fatigue_threshold=2, cooldown_seconds=60.0)

    def test_should_prompt_high_score(self):
        # High impact, novelty, uncertainty should trigger a prompt
        should_ask = self.controller.should_prompt(impact=0.9, novelty=0.8, uncertainty=0.7, in_high_stress_episode=False)
        self.assertTrue(should_ask)

    def test_defer_during_high_stress(self):
        # Must defer nonessential feedback during high-stress acoustic episodes
        should_ask = self.controller.should_prompt(impact=0.9, novelty=0.9, uncertainty=0.9, in_high_stress_episode=True)
        self.assertFalse(should_ask)

    def test_fatigue_threshold_blocking(self):
        # Record prompts up to threshold
        self.controller.record_prompt()
        self.controller.record_prompt()
        
        # Next prompt should be suppressed due to user fatigue limits
        should_ask = self.controller.should_prompt(impact=0.9, novelty=0.9, uncertainty=0.9)
        self.assertFalse(should_ask)

if __name__ == "__main__":
    unittest.main()
