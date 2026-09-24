from src.reinforcement.reinforcement_engine import ConfidenceWeightedReinforcementEngine
from src.audit.policy_audit import PolicyAuditLedger, PolicyAuditRecord

class PolicyReplayEngine:
    def __init__(self, engine: ConfidenceWeightedReinforcementEngine):
        self.engine = engine

    def replay_events(self, events: list) -> list:
        proposals = []
        for event in events:
            proposal = self.engine.compute_proposal(event)
            proposals.append(proposal)
        return proposals
