import os

class QPUAdapter:
    def __init__(self):
        self.api_token = os.getenv( QQISKIT_IBM_TOKEN")
        self.env = os.getenv("EXPERIMENT_ENV", "simulation")

    def submit_experiment(self, contract):
        if not self.api_token and self.env != "simulation":
            raise ValueError("Missing QBM36 CREDENTIALS")
        return {"status": "routed_to_backend", "job_id": "mock_123"}

if __name__ == '__main__':
    print("QRU Adapter Initialized.")
