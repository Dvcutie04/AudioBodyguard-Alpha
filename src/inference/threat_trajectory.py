from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class TrajectoryState:
    current_probability: float
    probability_velocity: float
    probability_acceleration: float
    persistence: float
    escalation_score: float
    projected_probability: float
    horizon_ms: float
    confidence: float

class ThreatTrajectoryEngine:
    def __init__(
        self, 
        beta_v: float = 0.6, 
        beta_a: float = 0.6, 
        max_horizon_ms: float = 500.0,
        w_v: float = 0.4,
        w_a: float = 0.2,
        w_p: float = 0.4
    ):
        self.beta_v = beta_v
        self.beta_a = beta_a
        self.max_horizon_ms = max_horizon_ms
        self.w_v = w_v
        self.w_a = w_a
        self.w_p = w_p
        
        self._last_time: Optional[float] = None
        self._last_prob: float = 0.0
        self._velocity: float = 0.0
        self._acceleration: float = 0.0
        self._persistence_count: int = 0
        self._total_observations: int = 0

    def reset(self):
        self._last_time = None
        self._last_prob = 0.0
        self._velocity = 0.0
        self._acceleration = 0.0
        self._persistence_count = 0
        self._total_observations = 0

    def update(self, timestamp: float, probability: float, horizon_ms: float = 500.0) -> TrajectoryState:
        # Validate inputs against malformed data
        if (
            timestamp is None 
            or probability is None
            isinstance(timestamp, bool) or isinstance(probability, bool)
            or not (0.0 <= probability <= 1.0)
            # Check for NaN / Infinity
            or timestamp != timestamp or probability != probability
            or timestamp == float('inf') or timestamp == float('-inf')
        ):
            # Fall back to safe defaults or preserve state on malformed input
            return TrajectoryState(
                current_probability=self._last_prob,
                probability_velocity=self._velocity,
                probability_acceleration=self._acceleration,
                persistence=self._calculate_persistence(),
                escalation_score=0.0,
                projected_probability=self._last_prob,
                horizon_ms=min(horizon_ms, self.max_horizon_ms),
                confidence=0.1
            )

        dt = 0.0
        if self._last_time is not None:
            dt = timestamp - self._last_time

        raw_v = 0.0
        if dt > 0.0:
            raw_v = (probability - self._last_prob) / dt
        elif dt < 0.0:
            # Handle out-of-order or duplicate timestamps safely
            dt = 0.0

        # Smooth velocity
        if self._last_time is not None and dt > 0.0:
            new_v = (self.beta_v * self._velocity) + ((1.0 - self.beta_v) * raw_v)
            raw_a = (new_v - self._velocity) / dt
            new_a = (self.beta_a * self._acceleration) + ((1.0 - self.beta_a) * raw_a)
        else:
            new_v = self._velocity
            new_a = self._acceleration

        self._velocity = new_v
        self._acceleration = new_a
        
        # Track persistence (fraction of recent samples showing elevated activity or continuity)
        if probability >= 0.35:
            self._persistence_count += 1
        self._total_observations += 1
        
        persistence = self._calculate_persistence()
        
        # Escalation score calculation
        esc_score = (
            self.w_v * max(0.0, min(1.0, self._velocity)) +
            self.w_a * max(0.0, min(1.0, self._acceleration)) +
            self.w_p * persistence
        )
        esc_score = max(0.0, min(1.0, esc_score))

        # Projected probability bounded by max horizon
        bounded_horizon = min(max(0.0, horizon_ms), self.max_horizon_ms)
        horizon_sec = bounded_horizon / 1000.0
        
        projected = probability + (self._velocity * horizon_sec) + (0.5 * self._acceleration * (horizon_sec ** 2))
        projected = max(0.0, min(1.0, projected))

        self._last_time = timestamp
        self._last_prob = probability

        confidence = min(1.0, max(0.1, 1.0 - abs(probability - 0.5)))

        return TrajectoryState(
            current_probability=probability,
            probability_velocity=self._velocity,
            probability_acceleration=self._acceleration,
            persistence=persistence,
            escalation_score=esc_score,
            projected_probability=projected,
            horizon_ms=bounded_horizon,
            confidence=confidence
        )

    def _calculate_persistence(self) -> float:
        if self._total_observations == 0:
            return 0.0
        return float(self._persistence_count) / float(self._total_observations)
