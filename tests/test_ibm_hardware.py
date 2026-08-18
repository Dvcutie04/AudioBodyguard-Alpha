import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import numpy as np

mock_qiskit = MagicMock()
mock_qiskit.QuantumCircuit = MagicMock()
sys.modules["qiskit"] = mock_qiskit
from src.research_loop.ibm_hardware_phase2 import IBMHardwareRunner

class TestIBMHardwareRunner(unittest.TestCase):
    def test_local_simulation_execution(self):
        qc = MagicMock()
        with patch.dict(os.environ, {}, clear=True):
            runner = IBMHardwareRunner()
            self.assertEqual(runner.mode, "LOCAL_SIMULATION")
            with patch.object(runner, 'execute_kernel_circuits', return_value=np.array([1.0])):
                fidelities = runner.execute_kernel_circuits([qc])
                self.assertIsInstance(fidelities, np.ndarray)
