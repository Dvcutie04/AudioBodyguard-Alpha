from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass(frozen=True)
class StabilityMetrics:
    policy_velocity: float
    policy_acceleration: float
    oscillation_index: float
    governor_override_rate: float
    feedback_entropy: float
    circuit_breaker_tripped: bool
    controller_status: str

class PolicyStabilityMonitor:
    def __init__(self, velocity_limit: float = 15.0, oscillation_limit: float = 0.7, override_limit: float = 0.5):
        self.velocity_limit = velocity_limit
        self.oscillation_limit = oscillation_limit
        self.override_limit = override_limit
        self.history: List[float] = []
        self.directions: List[int] = []
        self.governor_overrides_count = 0
        self.total_policy_actions = 0
        self.is_tripped = False

    def record_step(self, policy_value: float, governor_overrode: bool = False, feedback_type: str = "AGREE") -> StabilityMetrics:
        self.total_policy_actions += 1
        if governor_overrode:
            self.governor_overrides_count += 1
        self.history.append(policy_value)
        velocity, acceleration, oscillation = 0.0, 0.0, 0.0
        if len(self.history) >= 2:
            velocity = abs(self.history[-1] - self.history[-2])
            direction = 1 if self.history[-1] > self.history[-2] else (-1 if self.history[-1] < self.history[-2] else 0)
            if direction != 0:
                self.directions.append(direction)
        if len(self.history) >= 3:
            prev_velocity = abs(self.history[-2] - self.history[-3])
            acceleration = velocity - prev_velocity
        if len(self.directions) >= 3:
            reversals = sum(1 for i in range(1, len(self.directions)) if self.directions[i] != self.directions[i-1])
            oscillation = reversals / (len(self.directions) - 1)
        override_rate = (self.governor_overrides_count / self.total_policy_actions) if self.total_policy_actions > 0 else 0.0
        entropy = 0.5
        if velocity > self.velocity_limit or oscillation > self.oscillation_limit or override_rate > self.override_limit:
            self.is_tripped = True
        status = "ADAPTATION_PAUSED" if self.is_tripped else ("UNSTABLE" if velocity > self.velocity_limit*0.7 or oscillation > self.oscillation_limit*0.7 else ("WATCH" if velocity > self.velocity_limit*0.4 else "STABLE"))
        return StabilityMetrics(velocity, acceleration, oscillation, override_rate, entropy, self.is_tripped, status)

    def reset_breaker(self):
        self.is_tripped = False
        self.governor_overrides_count = 0
        self.total_policy_actions = 0
        self.directions.clear()
