from unittest import TestCase
from src.omotenashi.hypothesis_gate import (
    HypothesisGate,
    Hypothesis,
    GateDecision
)

class TestHypothesisGate(TestCase):
    def setUp(self):
        self.gate = HypothesisGate(enter_threshold=0.70, minimum_margin=0.15)

    def test_propose_on_strong_conversation(self):
        probs = {
            Hypothesis.CONVERSATION: 0.90,
            Hypothesis.MEDIA_DIALOGUE: 0.20,
            Hypothesis.AMBIENT_SPEECH: 0.10
        }
        result = self.gate.evaluate(probs)
        self.assertEqual(result.decision, GateDecision.PROPOSE)
        self.assertEqual(result.confidence_margin, 0.70)

    def test_suppress_on_insufficient_margin(self):
        probs = {
            Hypothesis.CONVERSATION: 0.72,
            Hypothesis.MEDIA_DIALOGUE: 0.68,
        }
        result = self.gate.evaluate(probs)
        self.assertEqual(result.decision, GateDecision.SUPPRESS)

    def test_suppress_when_competitor_dominates(self):
        probs = {
            Hypothesis.CONVERSATION: 0.40,
            Hypothesis.MEDIA_DIALOGUE: 0.80,
        }
        result = self.gate.evaluate(probs)
        self.assertEqual(result.decision, GateDecision.SUPPRESS)
        self.assertEqual(result.competing_hypothesis, Hypothesis.MEDIA_DIALOGUE)

    def test_suppress_on_missing_conversation(self):
        probs = {
            Hypothesis.MEDIA_DIALOGUE: 0.90,
            Hypothesis.AMBIENT_SPEECH: 0.40,
        }
        result = self.gate.evaluate(probs)
        self.assertEqual(result.decision, GateDecision.SUPPRESS)
        self.assertEqual(result.conversation_probability, 0.0)

    def test_invalid_probabilities_rejection(self):
        with self.assertRaises(ValueError):
            self.gate.evaluate({Hypothesis.CONVERSATION: float('nan')})
        with self.assertRaises(ValueError):
            self.gate.evaluate({Hypothesis.CONVERSATION: 1.25})
        with self.assertRaises(ValueError):
            self.gate.evaluate({Hypothesis.CONVERSATION: -0.1})
        with self.assertRaises(TypeError):
            self.gate.evaluate({Hypothesis.CONVERSATION: "high"})

    def test_empty_hypothesis_set(self):
        result = self.gate.evaluate({})
        self.assertEqual(result.decision, GateDecision.SUPPRESS)
        self.assertEqual(result.conversation_probability, 0.0)

if __name__ == "__main__":
    import unittest
    unittest.main()
