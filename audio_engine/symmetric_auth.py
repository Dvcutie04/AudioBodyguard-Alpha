import hashlib
import hmac
import json

class SymmetricAuthenticator:
    def __init__(self, key):
        if not isinstance(key, (bytes, bytearray)) or len(key) < 16:
            raise ValueError("authentication key must contain at least 16 bytes")
        self.key = bytes(key)
        self.highest_sequence = {}

    def _canonical(self, envelope):
        data = {
            "node_id": envelope.node_id,
            "sequence_id": envelope.sequence_id,
            "trust_epoch": envelope.trust_epoch,
            "decision_state": envelope.decision_state,
            "effective_trust": envelope.effective_trust,
            "trust_reason_codes": list(envelope.trust_reason_codes),
            "evidence_digest": envelope.evidence_digest,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    def sign(self, envelope):
        return hmac.new(self.key, self._canonical(envelope), hashlib.sha256).hexdigest()

    def verify(self, envelope, tag):
        if not isinstance(tag, str):
            return False
        expected = self.sign(envelope)
        return hmac.compare_digest(expected, tag)

    def admit(self, envelope, tag, current_epoch):
        if not self.verify(envelope, tag):
            return "REJECT_AUTH"
        node = envelope.node_id
        sequence = int(envelope.sequence_id)
        previous = self.highest_sequence.get(node, -1)
        if sequence <= previous:
            return "REJECT_REPLAY"
        if int(envelope.trust_epoch) < int(current_epoch):
            return "REJECT_STALE_EPOCH"
        self.highest_sequence[node] = sequence
        return "ACCEPT"

# TODO: Implement replay window check using sequence_id and timestamp freshness

class ReplayWindow:
    def __init__(self, window_size=32):
        self.window_size = window_size
        self.highest_seq = 0
    def check_and_update(self, seq):
        if seq <= self.highest_seq - self.window_size:
            return False
        if seq > self.highest_seq:
            self.highest_seq = seq
        return True
import hashlib
import hmac
import json

class SymmetricAuthenticator:
    def __init__(self, key):
        if not isinstance(key, (bytes, bytearray)) or len(key) < 16:
            raise ValueError("authentication key must contain at least 16 bytes")
        self.key = bytes(key)
        self.highest_sequence = {}

    def _canonical(self, envelope):
        data = {
            "node_id": envelope.node_id,
            "sequence_id": envelope.sequence_id,
            "trust_epoch": envelope.trust_epoch,
            "decision_state": envelope.decision_state,
            "effective_trust": envelope.effective_trust,
            "trust_reason_codes": list(envelope.trust_reason_codes),
            "evidence_digest": envelope.evidence_digest,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    def sign(self, envelope):
        return hmac.new(self.key, self._canonical(envelope), hashlib.sha256).hexdigest()

    def verify(self, envelope, tag):
        if not isinstance(tag, str):
            return False
        expected = self.sign(envelope)
        return hmac.compare_digest(expected, tag)

    def admit(self, envelope, tag, current_epoch):
        if not self.verify(envelope, tag):
            return "REJECT_AUTH"
        node = envelope.node_id
        sequence = int(envelope.sequence_id)
        previous = self.highest_sequence.get(node, -1)
        if sequence <= previous:
            return "REJECT_REPLAY"
        if int(envelope.trust_epoch) < int(current_epoch):
            return "REJECT_STALE_EPOCH"
        self.highest_sequence[node] = sequence
        return "ACCEPT"

# TODO: Implement replay window check using sequence_id and timestamp freshness

class ReplayWindow:
    def __init__(self, window_size=32):
        self.window_size = window_size
        self.highest_seq = 0
    def check_and_update(self, seq):
        if seq <= self.highest_seq - self.window_size:
            return False
        if seq > self.highest_seq:
            self.highest_seq = seq
        return True
