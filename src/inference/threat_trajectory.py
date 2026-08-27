"""
Threat Trajectory Engine for AQSS-36-OMEGA.
Models dynamic threat progression, state transitions, and temporal trajectory estimation.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class TrajectoryState(Enum):
    STABLE = auto()
    ELEVATING = auto()
    CRITICAL = auto()
    DEESCALATING = auto()


@dataclass
class TrajectoryPoint:
    timestamp: float
    threat_level: float
    confidence: float
    state: TrajectoryState


class ThreatTrajectoryEngine:
    def __init__(self, history_window: int = 50, smoothing_factor: float = 0.2):
        self.history_window = history_window
        self.smoothing_factor = smoothing_factor
        self.points: List[TrajectoryPoint] = []
        self.current_state: TrajectoryState = TrajectoryState.STABLE

    def calculate_velocity(self) -> float:
        if len(self.points) < 2:
            return 0.0
        
        recent = self.points[-1]
        previous = self.points[-2]
        dt = recent.timestamp - previous.timestamp
        
        if dt <= 0:
            return 0.0
            
        return (recent.threat_level - previous.threat_level) / dt

    def update_trajectory(
        self, 
        threat_level: float, 
        confidence: float = 1.0, 
        timestamp: Optional[float] = None
    ) -> TrajectoryState:
        if timestamp is None:
            timestamp = time.time()

        # Determine trajectory state based on smoothed delta dynamics
        if not self.points:
            state = TrajectoryState.STABLE
        else:
            prev_level = self.points[-1].threat_level
            delta = threat_level - prev_level

            if delta > 0.15:
                state = TrajectoryState.CRITICAL if threat_level > 0.75 else TrajectoryState.ELEVATING
            elif delta < -0.10:
                state = TrajectoryState.DEESCALATING
            else:
                state = TrajectoryState.STABLE

        point = TrajectoryPoint(
            timestamp=timestamp,
            threat_level=threat_level,
            confidence=confidence,
            state=state
        )

        self.points.append(point)
        if len(self.points) > self.history_window:
            self.points.pop(0)

        self.current_state = state
        return self.current_state

    def predict_next_threat_level(self, horizon_seconds: float = 1.0) -> float:
        if not self.points:
            return 0.0

        current = self.points[-1].threat_level
        velocity = self.calculate_velocity()
        predicted = current + (velocity * horizon_seconds)
        
        return float(max(0.0, min(1.0, predicted)))
