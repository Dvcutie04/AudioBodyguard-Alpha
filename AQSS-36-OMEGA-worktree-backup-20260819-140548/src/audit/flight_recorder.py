import hashlib, json, time, uuid

class FlightRecorder:
    def __init__(self):
        self.chain = []
        self.last_hash = "0" * 64

    def record_event(self, proposal_id: str, sequence_num: int, system_state: str, sensor_health: dict, decision: str, confidence: float, risk_state: str, policy_version: str, auth_result: bool, interlock_state: bool, exec_result: str, rejection_reason: str = "NONE") -> dict:
        event_id = str(uuid.uuid4())
        timestamp_ns = time.time_ns()
        
        payload = {
            "event_id": event_id,
            "prev_hash": self.last_hash,
            "proposal_id": proposal_id,
            "sequence_num": sequence_num,
            "system_state": system_state,
            "sensor_health": sensor_health,
            "decision": decision,
            "confidence": round(confidence, 4),
            "risk_state": risk_state,
            "policy_version": policy_version,
            "auth_result": auth_result,
            "interlock_state": interlock_state,
            "exec_result": exec_result,
            "rejection_reason": rejection_reason,
            "timestamp_ns": timestamp_ns
        }
        
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        current_hash = hashlib.sha256(serialized).hexdigest()
        payload["hash"] = current_hash
        
        self.chain.append(payload)
        self.last_hash = current_hash
        return payload

    def verify_chain_integrity(self) -> bool:
        expected_prev = "0" * 64
        for entry in self.chain:
            record_copy = dict(entry)
            entry_hash = record_copy.pop("hash")
            if record_copy["prev_hash"] != expected_prev:
                return False
            serialized = json.dumps(record_copy, sort_keys=True).encode("utf-8")
            if hashlib.sha256(serialized).hexdigest() != entry_hash:
                return False
            expected_prev = entry_hash
        return True
