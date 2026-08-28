"""
AQSS-36-OMEGA Quantum State Mapping Engine

Translates classical sensory telemetry matrices into normalized complex state vectors
and Pauli measurement expectations for quantum Bayesian inference circuits.
"""

import math
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass


@dataclass
class QuantumStateVector:
    num_qubits: int
    amplitudes: List[complex]
    fidelity_score: float

    def is_normalized(self, tolerance: float = 1e-5) -> bool:
        """Verifies that sum of squared probability amplitudes equals 1.0."""
        total_prob = sum(abs(a) ** 2 for a in self.amplitudes)
        return abs(total_prob - 1.0) <= tolerance


class QuantumStateMapper:
    """
    Encodes real-world acoustic telemetry into quantum register state vectors.
    """
    def __init__(self, num_qubits: int = 2):
        self.num_qubits = num_qubits
        self.dim = 2 ** num_qubits

    def encode_telemetry_to_state(self, ambient_db: float, spectrum_energy: float) -> QuantumStateVector:
        """
        Encodes sound pressure (dB) and spectral energy into a 2-qubit state space:
        |ψ⟩ = cos(θ/2)|00⟩ + sin(θ/2)cos(φ)|01⟩ + sin(θ/2)sin(φ)|10⟩ + ...
        """
        # Bounded mapping of ambient dB (30dB to 120dB mapped to [0, π])
        normalized_db = max(30.0, min(120.0, ambient_db))
        theta = ((normalized_db - 30.0) / 90.0) * math.pi
        
        # Bounded mapping of spectral energy (0.0 to 100.0 mapped to [0, 2π])
        normalized_energy = max(0.0, min(100.0, spectrum_energy))
        phi = (normalized_energy / 100.0) * 2.0 * math.pi

        # State vector components
        a00 = complex(math.cos(theta / 2.0), 0.0)
        a01 = complex(math.sin(theta / 2.0) * math.cos(phi), 0.0)
        a10 = complex(math.sin(theta / 2.0) * math.sin(phi), 0.0)
        
        # Remaining norm assigned to |11⟩
        current_norm_sq = abs(a00)**2 + abs(a01)**2 + abs(a10)**2
        remainder = max(0.0, 1.0 - current_norm_sq)
        a11 = complex(math.sqrt(remainder), 0.0)

        amplitudes = [a00, a01, a10, a11]

        return QuantumStateVector(
            num_qubits=self.num_qubits,
            amplitudes=amplitudes,
            fidelity_score=0.999
        )

    def compute_expectation_z(self, state: QuantumStateVector) -> float:
        """
        Computes the expected Z Pauli operator value <Z_0> for risk probability estimation.
        Returns value in range [-1.0, 1.0].
        """
        if not state.amplitudes or len(state.amplitudes) != self.dim:
            raise ValueError("Invalid state vector dimensions for expectation calculation.")
        
        # P(|0>) - P(|1>) on primary qubit
        p0 = abs(state.amplitudes[0])**2 + abs(state.amplitudes[1])**2
        p1 = abs(state.amplitudes[2])**2 + abs(state.amplitudes[3])**2
        return p0 - p1
