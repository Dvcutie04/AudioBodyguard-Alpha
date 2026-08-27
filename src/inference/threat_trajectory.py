import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class TrajectoryPoint:
    timestamp: float
    threat_level: float
    confidence: float


class ThreatTrajectoryEngine:
    def __init__(self, history_window: int = 10):
        self.history_window = history_window
        self.history: List[TrajectoryPoint] = []

    def update(self, threat_level: float, confidence: float, timestamp: float) -> Dict[str, Any]:
        point = TrajectoryPoint(timestamp=timestamp, threat_level=threat_level, confidence=confidence)
        self.history.append(point)
        if len(self.history) > self.history_window:
            self.history.pop(0)

        velocity = self.calculate_velocity()
        acceleration = self.calculate_acceleration()
        predicted_threat = min(1.0, max(0.0, threat_level + velocity))

        return {
            "trajectory_points": len(self.history),
            "velocity": velocity,
            "acceleration": acceleration,
            "predicted_threat": predicted_threat,
            "trend": "escalating" if velocity > 0.05 else ("de-escalating" if velocity < -0.05 else "stable")
        }

    def calculate_velocity(self) -> float:
        if len(self.history) < 2:
            return 0.0
        dt = self.history[-1].timestamp - self.history[-2].timestamp
        if dt <= 0:
            return 0.0
        return (self.history[-1].threat_level - self.history[-2].threat_level) / dt

    def calculate_acceleration(self) -> float:
        if len(self.history) < 3:
            return 0.0
        dt1 = self.history[-1].timestamp - self.history[-2].timestamp
        dt2 = self.history[-2].timestamp - self.history[-3].timestamp
        if dt1 <= 0 or dt2 <= 0:
            return 0.0
        v1 = (self.history[-1].threat_level - self.history[-2].threat_level) / dt1
        v2 = (self.history[-2].threat_level - self.history[-3].threat_level) / dt2
        return (v1 - v2) / dt1
