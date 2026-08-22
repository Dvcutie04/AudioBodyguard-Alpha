from .quantum_work_item import QuantumWorkItem
from .backend import QuantumBackend, DeterministicBackend

def execute_work_item(item: QuantumWorkItem, backend: QuantumBackend | None = None) -> dict:
    active_backend = backend if backend is not None else DeterministicBackend()
    return active_backend.execute(item)
