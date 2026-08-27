from dataclasses import dataclass


@dataclass
class TrajectoryState:
    timestamp: float
    smoothed_p: float
    dt: float


class ThreatTrajectoryEngine:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        """Reset internal trajectory state."""
        self._last_timestamp: float | None = None
        self._state_history: list = []

    def update(self, timestamp: float, smoothed_p: float) -> TrajectoryState:
        """Update trajectory state observation."""
        delta_t = 0.0 if self._last_timestamp is None else max(0.0, timestamp - self._last_timestamp)
        self._last_timestamp = timestamp
        
        state = TrajectoryState(
            timestamp=timestamp,
            smoothed_p=smoothed_p,
            dt=delta_t,
        )
        self._state_history.append(state)
        return state
