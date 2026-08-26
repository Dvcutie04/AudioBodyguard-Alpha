import hashlib
import json
from dataclasses import dataclass

@dataclass
class AttestationRecord:
    node_id: str
    sequence: int
    event_id: str
    timestamp: float
    parent_digest: str
    evidence_digest: str
    inference_digest: str
    policy_digest: str
    action_digest: str
    model_version: str
    attestation_digest: str = ""

class CausalAttestationChain:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.chain = []
    
    def compute_digest(self, record: AttestationRecord, parent_digest: str) -> str:
        payload = f"{parent_digest}|{record.evidence_digest}|{record.inference_digest}|{record.policy_digest}|{record.action_digest}"
        return hashlib.sha256(payload.encode()).hexdigest()
    
    def append(self, event_id, evidence, inference, policy, action, model_version, timestamp):
        parent = self.chain[-1].attestation_digest if self.chain else "0" * 64
        seq = len(self.chain) + 1
        ev_dig = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
        inf_dig = hashlib.sha256(json.dumps(inference, sort_keys=True).encode()).hexdigest()
        pol_dig = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
        act_dig = hashlib.sha256(json.dumps(action, sort_keys=True).encode()).hexdigest()
        
        partial_record = AttestationRecord(
            node_id=self.node_id, sequence=seq, event_id=event_id, timestamp=timestamp,
            parent_digest=parent, evidence_digest=ev_dig, inference_digest=inf_dig,
            policy_digest=pol_dig, action_digest=act_dig, model_version=model_version
        )
        partial_record.attestation_digest = self.compute_digest(partial_record, parent)
        self.chain.append(partial_record)
        return partial_record

def verify_attestation_chain(chain):
    if not chain:
        return True
    for i, record in enumerate(chain):
        expected_parent = "0" * 64 if i == 0 else chain[i-1].attestation_digest
        if record.parent_digest != expected_parent or record.sequence != i + 1:
            return False
        payload = f"{record.parent_digest}|{record.evidence_digest}|{record.inference_digest}|{record.policy_digest}|{record.action_digest}"
        if record.attestation_digest != hashlib.sha256(payload.encode()).hexdigest():
            return False
    return True
