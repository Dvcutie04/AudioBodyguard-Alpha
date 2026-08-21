import json
from pathlib import Path
from .quantum_work_item import QuantumWorkItem
from .executor import execute_work_item
from .backend import QuantumBackend, DeterministicBackend


def run_batch(items, backend: QuantumBackend | None = None):
    active_backend = backend if backend is not None else DeterministicBackend()
    results = [execute_work_item(item, active_backend) for item in items]
    audit = Path("research_loop_audit.jsonl")
    with audit.open("a", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, sort_keys=True) + "\n")
    return results


if __name__ == "__main__":
    items = [QuantumWorkItem.from_features(f"smoke-{i:03d}",[0.1*i,0.2*i,0.3*i],"v1","aqss_bayesian_v1","0.1.0") for i in range(1,4)]
    results = run_batch(items)
    print("RUNNER_BACKEND_OK")
    print("ITEMS=",len(results))
    print("BACKENDS=",[r["backend"] for r in results])
    print("STATUSES=",[r["status"] for r in results])
