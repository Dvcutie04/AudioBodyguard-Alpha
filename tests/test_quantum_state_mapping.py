import sys, os
sys.path.insert(0, os.path.abspath("."))
import math
import unittest
from src.quantum.vqc_classifier import TwoQubitQuantumClassifier

class TestQuantumStateMapping(unittest.TestCase):
    def setUp(self):
        self.classifier = TwoQubitQuantumClassifier(theta_bias=0.0)

    def test_probability_normalization_and_bounds(self):
        test_cases = [(0.2, 0.8), (0.5, 0.5), (0.9, 0.1), (1.0, 1.0), (0.0, 0.0)]
        for spl, flatness in test_cases:
            _, probs = self.classifier.evaluate_acoustic_state(spl, flatness)
            total_prob = sum(probs.values())
            self.assertAlmostEqual(total_prob, 1.0, places=5)
            for p in probs.values():
                self.assertTrue(0.0 <= p <= 1.0)

    def test_argmax_classification(self):
        state, probs = self.classifier.evaluate_acoustic_state(0.7, 0.3)
        expected_state = max(probs, key=probs.get)
        self.assertEqual(state, expected_state)

    def test_boundary_conditions_zero(self):
        state, probs = self.classifier.evaluate_acoustic_state(0.0, 0.0)
        self.assertAlmostEqual(probs["PROGRAM_NORMAL"], 1.0, places=5)
        self.assertEqual(state, "PROGRAM_NORMAL")

    def test_boundary_conditions_one(self):
        state, probs = self.classifier.evaluate_acoustic_state(1.0, 1.0)
        self.assertAlmostEqual(probs["STREAMING_AD"], 1.0, places=5)
        self.assertEqual(state, "STREAMING_AD")

    def test_determinism_with_bias(self):
        biased_classifier = TwoQubitQuantumClassifier(theta_bias=math.pi / 4)
        state_1, probs_1 = biased_classifier.evaluate_acoustic_state(0.5, 0.5)
        state_2, probs_2 = biased_classifier.evaluate_acoustic_state(0.5, 0.5)
        self.assertEqual(state_1, state_2)
        self.assertEqual(probs_1, probs_2)

if __name__ == "__main__":
    unittest.main()
