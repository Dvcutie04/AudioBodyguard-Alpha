class ThreatTrajectoryEngine:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        """Reset internal trajectory state tracking."""
        self._last_timestamp: float | None = None
        self._state_history: list[dict] = []

    def update(self, timestamp: float, smoothed_p: float) -> dict:
        """Update state space observation with the latest timestamp and smoothed probability."""
        delta_t = (
            0.0 
            if self._last_timestamp is None 
            else max(0.0, timestamp - self._last_timestamp)
        )
        self._last_timestamp = timestamp

        trajectory_state = {
            "timestamp": timestamp,
            "smoothed_p": smoothed_p,
            "dt": delta_t,
        }
        self._state_history.append(trajectory_state)
        return trajectory_state
