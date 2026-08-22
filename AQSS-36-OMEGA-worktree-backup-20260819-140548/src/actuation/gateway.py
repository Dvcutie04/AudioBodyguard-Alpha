from src.crypto.attestation import ActionAttestor

class ActuatorGateway:
    def __init__(self, secret_key: bytes, expected_software_id: str = "AQSS-36-OMEGA-v7.3", expected_policy_ver: str = "POL-2026.08"):
        self.secret_key = secret_key
        self.expected_software_id = expected_software_id
        self.expected_policy_ver = expected_policy_ver
        self.last_sequence_num = 0
        self.seen_sequence_nums = set()
        self.hardware_interlock_tripped = False

    def set_hardware_interlock(self, tripped: bool):
        self.hardware_interlock_tripped = tripped

    def process_action_proposal(self, attestation: dict) -> tuple[bool, str]:
        payload = attestation.get("payload", {})
        seq = payload.get("sequence_num", 0)

        if seq in self.seen_sequence_nums or seq <= self.last_sequence_num:
            return False, "REJECTED_REPLAY_ATTACK_DETECTED"

        if self.hardware_interlock_tripped:
            self.seen_sequence_nums.add(seq)
            return False, "REJECTED_HARDWARE_INTERLOCK_TRIPPED"

        if not ActionAttestor.verify_attestation(attestation, self.secret_key):
            return False, "REJECTED_INVALID_SIGNATURE"

        if payload.get("software_identity") != self.expected_software_id:
            return False, "REJECTED_SOFTWARE_MISMATCH"
        if payload.get("policy_version") != self.expected_policy_ver:
            return False, "REJECTED_POLICY_MISMATCH"

        self.seen_sequence_nums.add(seq)
        self.last_sequence_num = max(self.last_sequence_num, seq)
        return True, "EXECUTED_" + str(payload.get("decision"))
