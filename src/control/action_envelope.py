import time
import uuid

class ActionEnvelope:
    def __init__(self, action, target, trust_score, evidence_mask, deadline_ms=200):
        self.event_id = str(uuid.uuid4())
        self.timestamp_ns = time.monotonic_ns()
        self.action = action
        self.target = target
        self.trust_score = trust_score
        self.evidence_mask = evidence_mask
        self.nonce = uuid.uuid4().hex
        self.deadline_ns = self.timestamp_ns + (deadline_ms * 1_000_000)

    def is_expired(self) -> bool:
        return time.monotonic_ns() >= self.deadline_ns

    def to_dict(self):
        return {
            'event_id': self.event_id,
            'timestamp_ns': self.timestamp_ns,
            'action': self.action,
            'target': self.target,
            'trust_score': self.trust_score,
            'evidence_mask': self.evidence_mask,
            'nonce': self.nonce,
            'deadline_ns': self.deadline_ns
        }
