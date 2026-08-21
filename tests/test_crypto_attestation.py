import unittest
from src.crypto.attestation import ActionAttestor

class TestActionAttestation(unittest.TestCase):
    def setUp(self):
        self.key = b"SUPER_SECRET_AQSS_KEY_36_OMEGA"
        self.attestor = ActionAttestor(secret_key=self.key)

    def test_valid_attestation(self):
        att = self.attestor.generate_attestation("RISING_THREAT", 0.9421, "epoch_hash_v12")
        self.assertTrue(ActionAttestor.verify_attestation(att, self.key))

    def test_tampered_payload_rejection(self):
        att = self.attestor.generate_attestation("RISING_THREAT", 0.9421, "epoch_hash_v12")
        att["payload"]["decision"] = "NOMINAL"
        self.assertFalse(ActionAttestor.verify_attestation(att, self.key))
