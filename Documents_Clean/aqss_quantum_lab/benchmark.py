import json
from aqss_quantum_lab.dataset_adapter import BenchmarkDatasetAdapter
from aqss_quantum_lab.classical_reference import ClassicalReferenceRunner
from aqss_quantum_lab.results_schema import BenchmarkRecord, ModelOutput

class BenchmarkRunner:
    def __init__(self):
        self.classical = ClassicalReferenceRunner()

    def run_all(self):
        records = []
        for sample_id, obs, gt in BenchmarkDatasetAdapter.get_standard_samples():
            c_out = self.classical.run(sample_id, obs)
            # Placeholder quantum output mirroring classical baseline for initial validation increment
            q_out = ModelOutput(p_threat=c_out.p_threat, latency_us=0.0)
            rec = BenchmarkRecord(sample_id=sample_id, ground_truth=gt, classical=c_out, quantum=q_out)
            records.append(rec.to_dict())
        return records

if __name__ == "__main__":
    runner = BenchmarkRunner()
    results = runner.run_all()
    print(json.dumps(results, indent=2))
