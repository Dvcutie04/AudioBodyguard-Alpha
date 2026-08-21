import time
import uuid
from src.engine.schemas import CommitteeProposal, QuantumResearchJob

class ExperimentPolicyEngine:
    def __init__(self, max_shots=4096, max_qubits=8):
        self.max_shots = max_shots
        self.max_qubits = max_qubits

    def validate_and_build_job(self, proposal: CommitteeProposal) -> QuantumResearchJob:
        if proposal.proposal_type != "QUANTUM_EXPERIMENT":
            raise ValueError(f"Unauthorized proposal type: {proposal.proposal_type}")
        shots = min(proposal.constraints.get("max_shots", 1024), self.max_shots)
        qubits = proposal.constraints.get("max_qubits", 2)
        if qubits > self.max_qubits:
            raise ValueError(f"Requested qubits ({qubits}) exceeds hardware ceiling ({self.max_qubits})")
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        return QuantumResearchJob(job_id=job_id, experiment=proposal.objective, circuit_spec={"type": "feature_map", "qubits": qubits}, shots=shots, created_ns=time.time_ns())