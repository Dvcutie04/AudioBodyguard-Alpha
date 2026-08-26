from unittest import TestCase
import copy
from src.security.causal_attestation import CausalAttestationChain, verify_attestation_chain

class TestCausalAttestation(TestCase):
    def test_valid_deterministic_chain(self):
        c = CausalAttestationChain("Node-A")
        c.append("evt_01", {"sensor": 0.9}, {"inf": "safe"}, {"pol": "allow"}, {"act": "proceed"}, "v1.0.0", 1000.0)
        c.append("evt_02", {"sensor": 0.8}, {"inf": "safe"}, {"pol": "allow"}, {"act": "proceed"}, "v1.0.0", 1050.0)
        self.assertTrue(verify_attestation_chain(c.chain))

    def test_modified_evidence_rejection(self):
        c = CausalAttestationChain("Node-A")
        c.append("evt_01", {"sensor": 0.9}, {"inf": "safe"}, {"pol": "allow"}, {"act": "proceed"}, "v1.0.0", 1000.0)
        t = copy.deepcopy(c.chain)
        t[0].evidence_digest = "a" * 64
        self.assertFalse(verify_attestation_chain(t))

    def test_modified_parent_rejection(self):
        c = CausalAttestationChain("Node-A")
        c.append("evt_01", {"sensor": 0.9}, {"inf": "safe"}, {"pol": "allow"}, {"act": "proceed"}, "v1.0.0", 1000.0)
        c.append("evt_02", {"sensor": 0.8}, {"inf": "safe"}, {"pol": "allow"}, {"act": "proceed"}, "v1.0.0", 1050.0)
        t = copy.deepcopy(c.chain)
        t[1].parent_digest = "f" * 64
        self.assertFalse(verify_attestation_chain(t))

    def test_sequence_rollback_rejection(self):
        c = CausalAttestationChain("Node-A")
        c.append("evt_01", {"sensor": 0.9}, {"inf": "safe"}, {"pol": "allow"}, {"act": "proceed"}, "v1.0.0", 1000.0)
        c.append("evt_02", {"sensor": 0.8}, {"inf": "safe"}, {"pol": "allow"}, {"act": "proceed"}, "v1.0.0", 1050.0)
        t = copy.deepcopy(c.chain)
        t[1].sequence = 1
        self.assertFalse(verify_attestation_chain(t))

if __name__ == "__main__":
    import unittest
    unittest.main()
