from dataclasses import dataclass, field
from typing import List

@dataclass
class TelemetryEnvelope:
    node_id: str
    sequence_id: int
    decision_state: str
    evidence_digest: str
    trust_epoch: int = 1
    effective_trust: float = 1.0
    trust_reason_codes: List[str] = field(default_factory=list)

@dataclass
class NodeTrust:
    identity: float
    tamper_state: float

class NodeSimulator:
    def __init__(self, node_id, key, sequence_id, location):
        self.node_id = node_id
        self.key = key
        self.sequence_id = sequence_id
        self.location = location

    def generate_telemetry(self, decision_state, metric, evidence_digest):
        env = TelemetryEnvelope(
            node_id=self.node_id,
            sequence_id=self.sequence_id,
            decision_state=decision_state,
            evidence_digest=evidence_digest,
            trust_epoch=1,
            effective_trust=1.0,
            trust_reason_codes=[]
        )
        from audio_engine.symmetric_auth import SymmetricAuthenticator
        auth = SymmetricAuthenticator(self.key)
        tag = auth.sign(env)
        return env, tag

    def get_node_trust(self):
        return NodeTrust(1.0, 1.0)
