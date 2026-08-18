try:
    from qiskit import QuantumCircuit, transpile
    from qiskit.primitives import StatevectorSampler
except ImportError:
    QuantumCircuit = transpile = StatevectorSampler = None
"""
Phase-2 IBM Hardware Execution Engine (AQSS-36-OMEGA)
Handles Qiskit Runtime V2 execution with automated local simulation fallback.
"""

import os
from typing import List, Dict, Any, Tuple
import numpy as np

try:
    from qiskit import QuantumCircuit, transpile
except ImportError:
    QuantumCircuit = None
    transpile = None

class IBMHardwareRunner:
    def __init__(self, backend_name: str = "ibm_brisbane", shots: int = 4096):
        self.backend_name = backend_name
        self.shots = shots
        self.token = os.getenv("QISKIT_IBM_TOKEN", None)
        self.backend = None
        self.mode = "LOCAL_SIMULATION"
        
        self._initialize_backend()

    def _initialize_backend(self):
        """Initializes IBM Quantum Service or falls back to local statevector execution."""
        if self.token:
            try:
                from qiskit_ibm_runtime import QiskitRuntimeService
                service = QiskitRuntimeService(channel="ibm_quantum", token=self.token)
                self.backend = service.least_busy(operational=True, simulator=False)
                self.mode = f"HARDWARE:{self.backend.name}"
            except Exception as e:
                print(f"[WARN] Failed to connect to IBM Hardware ({e}). Falling back to Local Simulation.")
                self.mode = "LOCAL_SIMULATION"
        else:
            print("[INFO] No QUSKIT_IBM_TOKEN detected. Running in Local Simulation Mode.")
            self.mode = "LOCAL_SIMULATION"

    def execute_kernel_circuits(self, circuits: List[QuantumCircuit]) -> np.ndarray:
        """
        Executes a batch of fidelity kernel circuits using Qiskit V2 Primitive workflows.
        """
        if self.mode.startswith("HARDWARE"):
            from qiskit_ibm_runtime import SamplerV2 as Sampler
            transpiled_circuits = transpile(circuits, backend=self.backend, optimization_level=3)
            sampler = Sampler(mode=self.backend)
            job = sampler.run(transpiled_circuits, shots=self.shots)
            result = job.result()
            fidelities = [pub_res.data.meas.get_counts().get('0'*c.num_qubits, 0) / self.shots for pub_res, c in zip(result, transpiled_circuits)]
            return np.ndarray(fidelities)
        else:
            sampler = StatevectorSampler()
            job = sampler.run(circuits, shots=self.shots)
            result = job.result()
            fidelities = []
            for pub_res, c in zip(result, circuits):
                counts = pub_res.data.meas.get_counts() if hasattr(pub_res.data, 'meas') else pub_res.data.c.get_counts()
                target_bitstring = '0' * c.num_qubits
                fidelities.append(counts.get(target_bitstring, 0) / self.shots)
            return np.ndarray(fidelities)

if __name__ == "__main__":
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    
    runner = IBMHardwareRunner()
    print(f"Runner Initialized. Mode: {runner.mode}")
    print(",Executing hardware verification test...")
    results = runner.execute_kernel_circuits([qc])
    print(f"Execution complete. Fidelity output: {results}")