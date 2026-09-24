from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class CounterfactualResult:
    current_policy_version: int
    candidate_policy_version: int
    current_action: str
    candidate_action: str
    action_changed: bool
    sensitivity_delta: float
    confidence_delta: float
    safety_margin_delta: float
    notification_delta: float
    attenuation_delta: float
    blast_radius: float
    recommendation: str

class ShadowPolicyEngine:
    def __init__(self, blast_radius_weights: Dict[str, float] = None):
        self.weights = blast_radius_weights or {
            "notification": 0.4,
            "haptics": 0.2,
            "attenuation": 0.2,
            "automation": 0.2
        }

    def evaluate_shadow(self, current_policy: Dict[str, Any], candidate_policy: Dict[str, Any], proposal_deltas: Dict[str, float]) -> CounterfactualResult:
        curr_ver = current_policy.get("version", 1)
        cand_ver = candidate_policy.get("version", curr_ver + 1)
        
        curr_action = current_policy.get("action", "monitor")
        cand_action = candidate_policy.get("action", curr_action)
        
        s_delta = proposal_deltas.get("sensitivity", 0.0)
        c_delta = proposal_deltas.get("confidence", 0.0)
        sm_delta = proposal_deltas.get("safety_margin", 0.0)
        n_delta = proposal_deltas.get("notification", 0.0)
        a_delta = proposal_deltas.get("attenuation", 0.0)
        auto_delta = proposal_deltas.get("automation", 0.0)
        h_delta = proposal_deltas.get("haptics", 0.0)
        
        # Blast radius calculation: B = sum(w_i * |Delta A_i|)
        b_score = (
            self.weights.get("notification", 0.4) * abs(n_delta) +
            self.weights.get("haptics", 0.2) * abs(h_delta) +
            self.weights.get("attenuation", 0.2) * abs(a_delta) +
            self.weights.get("automation", 0.2) * abs(auto_delta)
        )
        
        action_changed = curr_action != cand_action
        
        if b_score > 10.0:
            recommendation = "REJECT_HIGH_BLAST_RADIUS"
        elif action_changed and s_delta > 0:
            recommendation = "BEHAVIORAL_IMPROVEMENT"
        elif not action_changed:
            recommendation = "NO_MEANINGFUL_DIFFERENCE"
        else:
            recommendation = "ACCEPTABLE"
            
        return CounterfactualResult(
            current_policy_version=curr_ver,
            candidate_policy_version=cand_ver,
            current_action=curr_action,
            candidate_action=cand_action,
            action_changed=action_changed,
            sensitivity_delta=s_delta,
            confidence_delta=c_delta,
            safety_margin_delta=sm_delta,
            notification_delta=n_delta,
            attenuation_delta=a_delta,
            blast_radius=b_score,
            recommendation=recommendation
        )
