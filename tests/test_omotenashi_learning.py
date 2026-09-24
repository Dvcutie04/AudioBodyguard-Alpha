import sys, os
sys.path.insert(0, os.path.abspath("."))
import unittest
from src.omotenashi.learning_engine import OmotenashiLearningEngine, UserPreferenceState

class TestOmotenashiLearning(unittest.TestCase):
    def setUp(self):
        self.initial_state = UserPreferenceState(preferred_db_drop=8.0, detection_sensitivity=0.85, auto_skip_intros=True, auto_skip_ads=True)
        self.engine = OmotenashiLearningEngine(self.initial_state)

    def test_default_initialization(self):
        self.assertEqual(self.engine.state.preferred_db_drop, 8.0)
        self.assertEqual(self.engine.state.detection_sensitivity, 0.85)

    def test_positive_reduce_volume_feedback(self):
        self.engine.register_feedback("REDUCE_VOLUME", positive=True)
        self.assertEqual(self.engine.state.preferred_db_drop, 8.05)
        self.assertEqual(self.engine.state.detection_sensitivity, 0.85)

    def test_negative_reduce_volume_feedback(self):
        self.engine.register_feedback("REDUCE_VOLUME", positive=False)
        self.assertEqual(self.engine.state.preferred_db_drop, 7.95)

    def test_lower_bound_enforcement(self):
        self.engine.state = UserPreferenceState(preferred_db_drop=3.0)
        self.engine.register_feedback("REDUCE_VOLUME", positive=False)
        self.assertEqual(self.engine.state.preferred_db_drop, 3.0)

    def test_upper_bound_enforcement(self):
        self.engine.state = UserPreferenceState(preferred_db_drop=18.0)
        self.engine.register_feedback("REDUCE_VOLUME", positive=True)
        self.assertEqual(self.engine.state.preferred_db_drop, 18.0)

    def test_negative_skip_intro_feedback(self):
        self.engine.register_feedback("SKIP_INTRO", positive=False)
        self.assertEqual(self.engine.state.detection_sensitivity, 0.88)
        self.assertTrue(self.engine.state.auto_skip_intros)

    def test_sensitivity_ceiling_enforcement(self):
        self.engine.state = UserPreferenceState(detection_sensitivity=0.97)
        self.engine.register_feedback("SKIP_INTRO", positive=False)
        self.assertEqual(self.engine.state.detection_sensitivity, 0.98)

    def test_unrelated_action_type_mutation(self):
        self.engine.register_feedback("UNKNOWN_ACTION", positive=True)
        self.assertEqual(self.engine.state.preferred_db_drop, 8.0)
        self.assertEqual(self.engine.state.detection_sensitivity, 0.85)

if __name__ == "__main__":
    unittest.main()
