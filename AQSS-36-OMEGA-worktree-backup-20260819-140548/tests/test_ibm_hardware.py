import unittest
from unittest.mock import patch, MagicMock
import os, sys, numpy as np

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
            with patch.object(runner, "execute_kernel_circuits", return_value=np.array([1.0])):
                fidelities = runner.execute_kernel_circuits([qc])
                self.assertIsInstance(fidelities, np.ndarray)

    @patch("src.research_loop.ibm_hardware_phase2.QiskitRuntimeService", create=True)
    def test_hardware_initialization_success(self, mock_service_cls):
        mock_service = MagicMock()
        mock_backend = MagicMock()
        mock_backend.name = "ibm_brisbane"
        mock_service.least_busy.return_value = mock_backend
        mock_service_cls.return_value = mock_service
        with patch.dict("sys.modules", {"qiskit_ibm_runtime": MagicMock(QiskitRuntimeService=mock_service_cls)}):
            with patch.dict(os.environ, {"QISKIT_IBM_TOKEN": "fake_token"}):
                runner = IBMHardwareRunner()
                self.assertEqual(runner.mode, "HARDWARE:ibm_brisbane")
