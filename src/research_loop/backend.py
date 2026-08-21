from abc import ABC, abstractmethod
from typing import Any
from .quantum_work_item import QuantumWorkItem

class QuantumBackend(ABC):
    @abstractmethod
    def execute(self, item: QuantumWorkItem) -> dict[str, Any]:
        raise NotImplementedError

class DeterministicBackend(QuantumBackend):
    def execute(self, item: QuantumWorkItem) -> dict[str, Any]:
        return {"backend":"deterministic","work_id":item.work_id,"status":"completed","shots":item.shots,"telemetry_hash":item.telemetry_hash}
