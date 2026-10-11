import hashlib
import hmac
import json
import threading

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

class ReplayWindow:
    """Accept each nonnegative sequence once within a bounded reorder window.

    Authentication must succeed before this window is updated. This helper
    establishes sequence freshness only, not wall-clock or physical evidence.
    """

    def __init__(self, window_size=32):
        if type(window_size) is not int or not 1 <= window_size <= 65536:
            raise ValueError("window size must be an integer between 1 and 65536")
        self.window_size = window_size
        self.highest_seq = 0
        self._seen = 0
        self._mask = (1 << window_size) - 1
        self._lock = threading.Lock()

    def check_and_update(self, seq):
        if type(seq) is not int or seq < 0:
            return False
        with self._lock:
            if seq > self.highest_seq:
                distance = seq - self.highest_seq
                # Avoid an allocation proportional to an untrusted sequence jump.
                self._seen = 1 if distance >= self.window_size else ((self._seen << distance) | 1) & self._mask
                self.highest_seq = seq
                return True
            distance = self.highest_seq - seq
            if distance >= self.window_size or self._seen & (1 << distance):
                return False
            self._seen |= 1 << distance
            return True
