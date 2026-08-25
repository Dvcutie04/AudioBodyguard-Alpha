import unittest
from inference.evidence_envelope import EvidenceEnvelope
from inference.hypothesis_reservoir import HypothesisReservoir

class TestEvidenceAndHypothesis(unittest.TestCase):
    def test_evidence_envelope_immutability(self):
        envelope = EvidenceEnvelope(
            event_id="evt-001",
            sequence=1,
            source_id="mic-node-01",
            sensor_quality=0.95,
            feature_vector={"rms": 0.42},
            change_point_evidence=None,
            posterior_before=0.1,
            posterior_after=0.3
        )
        self.assertEqual(envelope.event_id, "evt-001")
        with self.assertRaises(AttributeError):
            envelope.sequence = 2

    def test_evidence_envelope_bounds(self):
        with self.assertRaises(ValueError):
            EvidenceEnvelope(
                event_id="evt-002", sequence=2, source_id="node-1",
                sensor_quality=1.5, feature_vector={}, change_point_evidence=None,
                posterior_before=0.1, posterior_after=0.2
            )

    def test_hypothesis_reservoir_normalization(self):
        reservoir = HypothesisReservoir()
        reservoir.update({"H4": 2.0, "H1": 0.1})
        ranked = reservoir.get_ranked()
        
        # Ensure probabilities sum to ~1.0 and H4 is now top hypothesis
        total_prob = sum(h.probability for h in ranked)
        self.assertAlmostEqual(total_prob, 1.0)
        self.assertEqual(ranked[0].hid, "H4")

if __name__ == "__main__":
    unittest.main()
