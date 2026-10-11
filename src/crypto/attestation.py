import hmac, hashlib, json, time, uuid

class ActionAttestor:
    def __init__(self, secret_key: bytes, software_id: str = "AQSS-36-OMEGA-v7.3", policy_ver: str = "POL-2026.08"):
        self.secret_key = secret_key
        self.software_id = software_id
        self.policy_ver = policy_ver
        self.sequence_num = 0

    def generate_attestation(self, decision: str, confidence: float, state_version: str) -> dict:
        self.sequence_num += 1
        proposal_id = str(uuid.uuid4())
        nonce = str(uuid.uuid4().hex[:16])
        timestamp_ns = time.time_ns()

        canonical_payload = {
            "proposal_id": proposal_id,
            "sequence_num": self.sequence_num,
            "state_version": state_version,
            "decision": decision,
            "confidence": round(confidence, 4),
            "policy_version": self.policy_ver,
            "software_identity": self.software_id,
            "timestamp_ns": timestamp_ns,
            "nonce": nonce
        }

        serialized = json.dumps(canonical_payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(self.secret_key, serialized, hashlib.sha256).hexdigest()
        return {"payload": canonical_payload, "signature": signature}

    @staticmethod
    def verify_attestation(attestation: dict, secret_key: bytes) -> bool:
        if type(attestation) is not dict or set(attestation) != {"payload", "signature"}:
            return False
        payload = attestation["payload"]
        signature = attestation["signature"]
        fields = {"proposal_id", "sequence_num", "state_version", "decision", "confidence", "policy_version", "software_identity", "timestamp_ns", "nonce"}
        if type(payload) is not dict or set(payload) != fields:
            return False
        if type(signature) is not str or len(signature) != 64 or any(c not in "0123456789abcdef" for c in signature):
            return False
        if any(type(payload[k]) is not str or not payload[k].strip() or len(payload[k]) > 256 for k in fields - {"sequence_num", "timestamp_ns", "confidence"}):
            return False
        if any(type(payload[k]) is not int or not 0 < payload[k] < 2**63 for k in ("sequence_num", "timestamp_ns")):
            return False
        if type(payload["confidence"]) not in (int, float) or not 0 <= payload["confidence"] <= 1:
            return False
        try:
            serialized = json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
            expected_sig = hmac.new(secret_key, serialized, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected_sig, signature)
        except (TypeError, ValueError, UnicodeError):
            return False
