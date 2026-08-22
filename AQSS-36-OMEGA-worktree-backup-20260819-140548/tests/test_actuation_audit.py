import unittest, json, hmac, hashlib
from src.actuation.gateway import ActuatorGateway
from src.audit.flight_recorder import FlightRecorder
from src.crypto.attestation import ActionAttestor

class TestActuationAndAuditEdges(unittest.TestCase):
    def test_gateway_software_and_policy_mismatch(self):
        key = b"secret_key_123456"
        attestor = ActionAttestor(key)
        gw = ActuatorGateway(secret_key=key, expected_software_id="v1.0", expected_policy_ver="1.0")
        att_sw = attestor.generate_attestation("PASS", confidence=0.99, state_version="1.0")
        att_sw["payload"]["software_identity"] = "v2.0"
        serialized = json.dumps(att_sw["payload"], sort_keys=True).encode("utf-8")
        att_sw["signature"] = hmac.new(key, serialized, hashlib.sha256).hexdigest()
        ok, reason = gw.process_action_proposal(att_sw)
        self.assertFalse(ok)
        self.assertEqual(reason, "REJECTED_SOFTWARE_MISMATCH")
        att_pol = attestor.generate_attestation("PASS", confidence=0.99, state_version="1.0")
        att_pol["payload"]["software_identity"] = "v1.0"
        att_pol["payload"]["policy_version"] = "2.0"
        serialized_pol = json.dumps(att_pol["payload"], sort_keys=True).encode("utf-8")
        att_pol["signature"] = hmac.new(key, serialized_pol, hashlib.sha256).hexdigest()
        ok, reason = gw.process_action_proposal(att_pol)
        self.assertFalse(ok)
        self.assertEqual(reason, "REJECTED_POLICY_MISMATCH")

    def test_flight_recorder_tamper(self):
        fr = FlightRecorder()
        fr.record_event("prop-001", 1, "NOMINAL", {"mic": "OK"}, "PASS", 0.99, "LOW", "1.0", True, False, "SUCCESS")
        fr.record_event("prop-002", 2, "NOMINAL", {"mic": "OK"}, "PASS", 0.99, "LOW", "1.0", True, False, "SUCCESS")
        self.assertTrue(fr.verify_chain_integrity())
        fr.chain[0]["prev_hash"] = "corrupted"
        self.assertFalse(fr.verify_chain_integrity())
        fr.chain[0]["prev_hash"] = "0" * 64
        fr.chain[0]["decision"] = "TAMPERED"
        self.assertFalse(fr.verify_chain_integrity())
