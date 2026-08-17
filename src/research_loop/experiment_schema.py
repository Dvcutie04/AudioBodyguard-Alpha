import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class QPUExperimentContract:
    experiment_id: str
    backend_name: str
    circuit_hash: str
    shots: int
    classical_baseline_ms: float
    observable_def={"boundary_threshold": 0.40}
    mitigation_config={"unfolding": True}
    job_id: Optional[str] = None
    spatial_payload_result: Optional[Dict[str, Any]] = None
    verdict: str = "PENDING_EXECUTION"

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

if __name__ == '__main__':
    contract = QPUExperimentContract(
        experiment_id="EXP-20260817-001",
        backend_name="ibmq_qpu_simulator",
        circuit_hash="a1b2c3d4",
        shots=1024,
        classical_baseline_ms=0.024
    )
    print(contract.to_json())
