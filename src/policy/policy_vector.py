import time
from dataclasses import dataclass, field, replace
from typing import Optional

@dataclass(frozen=True)
class PolicyState:
    global_sensitivity: float = 69.0
    detection_preference: float = 50.0
    alert_preference: float = 50.0
    attenuation_preference: float = 50.0
    automation_preference: float = 50.0
    transparency: float = 30.0
    version: int = 0
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class PolicyUpdateEvent:
    source: str
    field_name: str
    delta: Optional[float] = None
    absolute_value: Optional[float] = None

class PolicyVectorManager:
    MIN_BOUND = 0.0
    MAX_BOUND = 100.0
    def __init__(self, state=None):
        self._current_state = state or PolicyState()
        self._history = [self._current_state]
    @property
    def current_state(self): return self._current_state
    def commit_update(self, event):
        val = event.absolute_value if event.absolute_value is not None else getattr(self._current_state, event.field_name) + event.delta
        new_val = max(self.MIN_BOUND, min(self.MAX_BOUND, val))
        self._current_state = replace(self._current_state, **{event.field_name: new_val, 'version': self._current_state.version + 1, 'timestamp': time.time()})
        self._history.append(self._current_state)
        return self._current_state
