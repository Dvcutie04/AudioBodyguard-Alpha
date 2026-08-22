"""
 Unit tests for Phase-2 IBM Hardware Runner (A-Shell Compatible Mock)
"""
import unittest
from unittest.mock import Mock, patch
import numpy as np

class TestIBMHardwareRunner(unittest.TestCase):
    @patch('os.getenv', return_value=None)
    def test_initialization_local_fallback(self, mock_getenv):
        # Verify fallback to LOCAL_SIMULATION when no token is provided
        from src.research_loop.ibm_hardware_phase2 import IBMHardwareRunner
        runner = IBMHardwareRunner()
        self.assertEqual(runner.mode, "LOCAL_SIMULATION")
        self.assertIsNone(runner.backend)

if __name__ == '__main__':
    unittest.main()
