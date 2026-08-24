import unittest
from aqss_quantum_lab.benchmark import BenchmarkRunner

class TestQuantumLabBenchmark(unittest.TestCase):
    def test_benchmark_runner_contract(self):
        runner = BenchmarkRunner()
        results = runner.run_all()
        self.assertGreaterEqual(len(results), 1)
        for record in results:
            self.assertIn("sample_id", record)
            self.assertIn("classical", record)
            self.assertIn("quantum", record)
            self.assertIn("ground_truth", record)
            self.assertIn("p_threat", record["classical"])
            self.assertIn("latency_us", record["classical"])
            self.assertIn("p_threat", record["quantum"])
            self.assertIn("latency_us", record["quantum"])

if __name__ == "__main__":
    unittest.main()
