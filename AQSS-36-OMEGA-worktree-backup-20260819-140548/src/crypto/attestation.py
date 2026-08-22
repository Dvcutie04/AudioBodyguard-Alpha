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
        serialized = json.dumps(attestation["payload"], sort_keys=True).encode("utf-8")
        expected_sig = hmac.new(secret_key, serialized, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, attestation["signature"])
