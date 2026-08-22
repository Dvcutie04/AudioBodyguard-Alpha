import unittest
from dataclasses import replace
from audio_engine.node_simulator import NodeSimulator
from audio_engine.symmetric_auth import SymmetricAuthenticator

class TestNodeSimulator(unittest.TestCase):
    def setUp(self):
        self.key = b"1234567890ABCDEF"
        self.sim = NodeSimulator("nodeA", self.key, 1, (0.0, 0.0))
        self.auth = SymmetricAuthenticator(self.key)

    def test_telemetry_generation_and_auth(self):
        env, tag = self.sim.generate_telemetry("OK", 0.1, "digest123")
        self.assertTrue(self.auth.verify(env, tag))
        self.assertEqual(env.sequence_id, 1)
        self.assertEqual(env.decision_state, "OK")

    def test_tamper_detection(self):
        env, tag = self.sim.generate_telemetry("OK", 0.1, "digest123")
        altered_decision = replace(env, decision_state="ALERT")
        self.assertFalse(self.auth.verify(altered_decision, tag))
        altered_digest = replace(env, evidence_digest="tampered-digest")
        self.assertFalse(self.auth.verify(altered_digest, tag))
        altered_seq = replace(env, sequence_id=999)
        self.assertFalse(self.auth.verify(altered_seq, tag))

    def test_node_trust_metrics(self):
        trust = self.sim.get_node_trust()
        self.assertEqual(trust.identity, 1.0)
        self.assertEqual(trust.tamper_state, 1.0)

if __name__ == "__main__":
    unittest.main()
