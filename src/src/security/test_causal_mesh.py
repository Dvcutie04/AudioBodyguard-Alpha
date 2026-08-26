from unittest import TestCase
from src.security.causal_attestation import CausalAttestationChain
from src.security.causal_mesh import CausalAttestationMesh

class TestCausalMesh(TestCase):
    def test_mesh_audit_valid_node(self):
        mesh = CausalAttestationMesh()
        c = CausalAttestationChain("Node-B")
        c.append("evt_10", {"sensor": 0.95}, {"inf": "ok"}, {"pol": "pass"}, {"act": "exec"}, "v1.0.0", 5000.0)
        mesh.register_node("Node-B", c.chain)
        audit = mesh.audit_node("Node-B", 1.0, 0.9, 0.9)
        self.assertTrue(audit["verified"])
        self.assertGreater(audit["trust_score"], 0.0)

if __name__ == "__main__":
    import unittest
    unittest.main()
