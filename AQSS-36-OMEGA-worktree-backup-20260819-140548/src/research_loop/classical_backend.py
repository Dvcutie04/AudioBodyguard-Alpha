from __future__ import annotations
import time
from typing import Any
from .backend import QuantumBackend
from .quantum_work_item import QuantumWorkItem

class ClassicalReferenceBackend(QuantumBackend):
    """Deterministic classical reference; no quantum claim is implied."""
    def execute(self,item: QuantumWorkItem) -> dict[str,Any]:
        start=time.perf_counter_ns(); result=list(item.feature_vector); elapsed_ns=time.perf_counter_ns()-start
        return {"backend":"classical_reference","work_id":item.work_id,"status":"completed","shots":0,"qubits":0,"result":result,"classical_runtime_ns":elapsed_ns,"telemetry_hash":item.telemetry_hash}
