"""
Unit tests for QuantumStateMapper state vector encoding and expectation values.
"""

import pytest
import math
from src.quantum.quantum_state_mapping import QuantumStateMapper, QuantumStateVector


def test_quantum_state_mapper_normalization():
    mapper = QuantumStateMapper(num_qubits=2)
    state = mapper.encode_telemetry_to_state(ambient_db=75.0, spectrum_energy=50.0)
    
    assert state.num_qubits == 2
    assert len(state.amplitudes) == 4
    assert state.is_normalized() is True


def test_out_of_bounds_telemetry_clamped_and_normalized():
    mapper = QuantumStateMapper(num_qubits=2)
    # Test extreme noise levels exceeding standard operating bounds
    state_high = mapper.encode_telemetry_to_state(ambient_db=150.0, spectrum_energy=200.0)
    state_low = mapper.encode_telemetry_to_state(ambient_db=10.0, spectrum_energy=-50.0)
    
    assert state_high.is_normalized() is True
    assert state_low.is_normalized() is True


def test_compute_expectation_z_range():
    mapper = QuantumStateMapper(num_qubits=2)
    state = mapper.encode_telemetry_to_state(ambient_db=60.0, spectrum_energy=30.0)
    exp_z = mapper.compute_expectation_z(state)
    
    # Expectation value must strictly fall in [-1.0, 1.0]
    assert -1.0 <= exp_z <= 1.0
