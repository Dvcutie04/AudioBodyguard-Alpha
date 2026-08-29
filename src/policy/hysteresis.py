"""
Hysteresis and State Thresholding Engine
Prevents rapid oscillations across policy states by enforcing rising/falling margins.
"""

from typing import Any, Dict, Optional


class HysteresisGate:
    """
    Tracks dynamic threshold state to prevent policy flickering around decision boundaries.
    """

    def __init__(
        self,
        high_threshold: float = 0.8,
        low_threshold: float = 0.3,
        initial_state: bool = False,
    ):
        """
        Initialize the hysteresis gate.

        :param high_threshold: Upper boundary to transition to ACTIVE (True).
        :param low_threshold: Lower boundary to transition to INACTIVE (False).
        :param initial_state: Starting binary state of the gate.
        """
        if low_threshold >= high_threshold:
            raise ValueError("low_threshold must be strictly less than high_threshold")

        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.state = initial_state

    def update(self, value: float) -> bool:
        """
        Update state based on input value using hysteresis bounds.

        :param value: New numerical score to evaluate.
        :return: Updated binary state (True = active, False = inactive).
        """
        if self.state:
            if value < self.low_threshold:
                self.state = False
        else:
            if value > self.high_threshold:
                self.state = True

        return self.state

    def get_state(self) -> bool:
        """
        Return current state of the gate.
        """
        return self.state

    def reset(self, state: bool = False) -> None:
        """
        Reset gate to specified state.
        """
        self.state = state
