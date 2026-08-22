class PolicyGovernor:
    def __init__(self, min_trust_threshold=0.85):
        self.min_trust_threshold = min_trust_threshold
        self._seen_nonces = set()

    def evaluate(self, envelope) -> tuple[bool, str]:
        # 1. Check expiration deadline
        if envelope.is_expired():
            return False, "REJECTED: Deadline exceeded"

        # 2. Check replay prevention via nonce uniqueness
        if envelope.nonce in self._seen_nonces:
            return False, "REJECTED: Replay attack detected (duplicate nonce)"

        # 3. Check trust threshold
        if envelope.trust_score < self.min_trust_threshold:
            return False, f"REJECTED: Trust score {envelope.trust_score} below threshold {self.min_trust_threshold}"

        # Mark nonce as processed
        self._seen_nonces.add(envelope.nonce)
        return True, "AUTHORIZED"
