import numpy as np
from src.research_loop.ibm_hardware_phase2 import IBMHardwareRunner

class ResearchPipeline:
    def __init__(self):
        self.runner = IBMHardwareRunner()
        print(f"Pipeline initialized with mode: {self.runner.mode}")

    def run_pipeline(self, circuits):
        return self.runner.execute_kernel_circuits(circuits)