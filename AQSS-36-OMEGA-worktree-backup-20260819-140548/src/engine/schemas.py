import json
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class QuantumResearchJob:
    job_id: str
    experiment: str
    circuit_spec: dict
    shots: int
    created_ns: int
    schema_version: int = 1

    def to_json(self) -> str:
        return json.dumps(asdict(self))

@dataclass(frozen=True)
class CommitteeProposal:
    schema_version: int
    proposal_id: str
    agent: str
    proposal_type: str
    objective: str
    constraints: dict
    parameters: dict
    evidence_required: list
