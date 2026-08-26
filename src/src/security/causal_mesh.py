from src.security.causal_attestation import verify_attestation_chain
from src.security.causal_trust import CausalTrustEvaluator

class CausalAttestationMesh:
    def __init__(self):
        self.nodes = {}
        self.evaluator = CausalTrustEvaluator()

    def register_node(self, node_id: str, chain):
        self.nodes[node_id] = chain

    def audit_node(self, node_id: str, freshness: float, sensor_q: float, history: float):
        if node_id not in self.nodes:
            return {"verified": False, "trust_score": 0.0}
        is_valid = verify_attestation_chain(self.nodes[node_id])
        trust_score = self.evaluator.evaluate(freshness, sensor_q, history) if is_valid else 0.0
        return {"verified": is_valid, "trust_score": trust_score}
