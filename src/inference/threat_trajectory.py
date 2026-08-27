from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TrajectoryState:
    current_probability: float
    probability_velocity: float
    projected_probability: float

    @property
    def p_hat(self) -> float:
        return self.current_probability

    @property
    def velocity(self) -> float:
        return self.probability_velocity


class ThreatTrajectoryTracker:
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.history: List[float] = []

    def update(self, current_p: float) -> TrajectoryState:
        self.history.append(current_p)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        if len(self.history) < 2:
            velocity = 0.0
        else:
            velocity = self.history[-1] - self.history[-2]

        projected = max(0.0, min(1.0, current_p + velocity))

        return TrajectoryState(
            current_probability=current_p,
            probability_velocity=velocity,
            projected_probability=projected
        )
