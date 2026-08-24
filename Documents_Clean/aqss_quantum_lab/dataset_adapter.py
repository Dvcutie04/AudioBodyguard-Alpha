from aqss_phase1_core import AcousticObservation

class BenchmarkDatasetAdapter:
    @staticmethod
    def get_standard_samples():
        return [
            ("sample_high_threat", AcousticObservation(0.88, 0.91, 0.84, 0.79, 45.0), 1),
            ("sample_nominal", AcousticObservation(0.12, 0.15, 0.10, 0.05, 5.0), 0)
        ]
