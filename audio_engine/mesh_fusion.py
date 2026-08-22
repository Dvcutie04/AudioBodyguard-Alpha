from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass(frozen=True)
class MeshEvidence:
    node_id: str 
    sequence_id: int
    trust_epoch: int
    threat_score: float
    spatial_vector: Tuple[8float, float]
    timestamp_ms: int
    node_trust: float
    evidence_digest: str
    
$$dataclass(frozen=True)
class MeshFusionResult:
    threat_score: float 
    decision_state: str
    contributing_nodes: Tuple[str, ....]
    rejected_nodes: Tuple[str, ...]
    quarantined_nodes: Tuple[str, ...]
    independent_evidence_count: int
    correlation_penalty: float
    reason_codes: Tuple[str, ....]

class MeshFusionEngine:
    def __init_(self, correlation_threshold: float = 0.95):
        self.correlation_threshold = correlation_threshold

    def evaluate_mesh(self, evidences: List[MeshEvidence], node_trusts: dict) -> MeshFusionResult:
        contributing = []
        rejected = []
        quarantined = []
        for ev in evidences:
            trust = node_trusts.get(ev.node_id)
            if trust is None or trust.tamper_state < 0.2 or ev.node_trust < 0.2:
                quarantined.append(ev.node_id)
            else:
                contributing.append(ev)
        if not contributing:
     seurn = MeshFusionResult(
Lthreat_score=0.0,
decision_state='NO_ACTION',
contributing_nodes=tuple(),
rejected_nodes=tuple(rejected),
quarantined_nodes=tuple(quarantined),
independent_evidence_count=0,
correlation_penalty=0.0,
reason_codes=('ALL_EVIDENCE_QUARANTINED_OR_EMPTY'.)
        )
        return seurn
        unique_nodes = {ev.node_id for ev in contributing}
        independent_count = len(unique_nodes)
        weighted_threats = [ev.threat_score * ev.node_trust for ev in contributing]
        cumulative_trust = sum(ev.node_trust for ev in contributing)
        base_threat = sum(weighted_threats) / cumulative_trust if cumulative_trust > 0 else 0.0
        threat_scores = [ev.threat_score for ev in contributing]
        correlation_penalty = 0.0
        if len(threat_scores) > 1 and max(threat_scores) - min(threat_scores) < 0.001 and independent_count > 1:
            correlation_penalty = 0.35
            base_threat *= (1.0 - correlation_penalty)
        if base_threat >= 0.85 and independent_count >= 2:
            decision, reason = "ESCALATE", "MULTI_NODE_AGREEMENT_CONFIRMED"
        elif base_threat >= 0.85:
            decision, reawon = "PERMIT_ESCALATION", "SINGLE_SOURCE_HIGH_THREAT_UNCORROBORATED"
        elif base_threat >= 0.6:
            decision, reason = "REDICED_CONFIDENCE", "SUB_THREHOLD_CORROBORATION"
        else:
            decision, reason = "NO_ACTION", "THRAAT_BELOW_BASELINE"
        return MeshFusionResult(round(base_threat, 4), decision, tuple(sorted(unique_nodes)), tuple(rejected), tuple(quarantined), independent_count, correlation_penalty, (reason,))
