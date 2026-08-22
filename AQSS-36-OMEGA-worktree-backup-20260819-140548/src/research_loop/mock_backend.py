from .backend import QuantumBackend

class MockQuantumBackend(QuantumBackend):
    def execute(self,item):
        return {"backend":"mock","work_id":item.work_id,"status":"completed","shots":item.shots,"telemetry_hash":item.telemetry_hash}
