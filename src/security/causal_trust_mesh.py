"""
AQSS-36-OMEGA Causal Trust Mesh

Evaluates multi-node observation consensus and quantum expectation values
to dynamic trust scores for active edge nodes.
"""

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class NodeTrustProfile:
    node_id: str
    trust_score: float = 1.0
    violation_count: int = 0
    is_quarantined: bool = False


class CausalTrustMesh:
    """
    Manages node trust vectors and dynamic quarantine states based on causal attestations.
    """
    def __init__(self, trust_threshold: float = 0.5):
        self.trust_threshold = trust_threshold
        self.nodes: Dict[str, NodeTrustProfile] = {}

    def register_node(self, node_id: str) -> NodeTrustProfile:
        """Registers a new node in the trust mesh."""
        profile = NodeTrustProfile(node_id=node_id)
        self.nodes[node_id] = profile
        return profile

    def record_attestation_failure(self, node_id: str, severity: float = 0.2) -> float:
        """
        Penalizes node trust score upon integrity or verification failure.
        Quarantines node if trust drops below threshold.
        """
        if node_id not in self.nodes:
            self.register_node(node_id)
            
        profile = self.nodes[node_id]
        profile.violation_count += 1
        profile.trust_score = max(0.0, profile.trust_score - severity)
        
        if profile.trust_score < self.trust_threshold:
            profile.is_quarantined = True
            
        return profile.trust_score

    def evaluate_consensus_trust(self, node_ids: List[str]) -> float:
        """Returns aggregate mesh trust score for a cluster of nodes."""
        if not node_ids:
            return 0.0
        
        active_scores = [
            self.nodes[nid].trust_score for nid in node_ids
            if nid in self.nodes and not self.nodes[nid].is_quarantined
        ]
        
        if not active_scores:
            return 0.0
            
        return sum(active_scores) / len(active_scores)
