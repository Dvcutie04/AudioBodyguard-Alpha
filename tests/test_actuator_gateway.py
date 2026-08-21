import unittest
from src.crypto.attestation import ActionAttestor
from src.actuation.gateway import ActuatorGateway

class TestActuatorGateway(unittest.TestCase):
    def setUp(self):
        self.key = b"SUPER_SECRET_AQSS_KEY_36_OMEGA"
        self.attestor = ActionAttestor(secret_key=self.key)
        self.gateway = ActuatorGateway(secret_key=self.key)

    def test_valid_execution(self):
        att = self.attestor.generate_attestation("RISING_THREAT", 0.95, "epoch_hash_v12")
        success, msg = self.gateway.process_action_proposal(att)
        self.assertTrue(success)
        self.assertEqual(msg, "EXECUTED_RISING_THREAT")

    def test_replay_attack_prevention(self):
        att = self.attestor.generate_attestation("RISING_THREAT", 0.95, "epoch_hash_v12")
        self.gateway.process_action_proposal(att)
        # Attempt to replay the same proposal
        success, msg = self.gateway.process_action_proposal(att)
        self.assertFalse(success)
        self.assertEqual(msg, "REJECTED_REPLAY_ATTACK_DETECTED")

    def test_hardware_interlock_override(self):
        att = self.attestor.generate_attestation("RISING_THREAT", 0.95, "epoch_hash_v12")
        self.gateway.set_hardware_interlock(True)
        success, msg = self.gateway.process_action_proposal(att)
        self.assertFalse(success)
        self.assertEqual(msg, "REJECTED_HARDWARE_INTERLOCK_TRIPPED")
