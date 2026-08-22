import time
import json
from dataclasses import dataclass
from enum import Enum, auto

class Pattern(Enum):
    SINGLE = auto()
    DOUBLE = auto()
    INVALID = auto()

@dataclass(frozen=True)
class Pulse:
    timestamp_ns: int
    confidence: float

class TriggerFSM:
    def __init__(self, config_path="config/settings.json"):
        with open(config_path, "r") as f:
            self.cfg = json.load(f)
        self.last_trigger_ns = 0
        self.last_dispatch_ns = 0
        self.pulse_buffer = []

    def accept(self, confidence: float) -> bool:
        now_ns = time.monotonic_ns()
        if confidence < self.cfg["trigger_confidence"]:
            return False
        dt_trigger_ms = (now_ns - self.last_trigger_ns) / 1_000_000
        if dt_trigger_ms < self.cfg["debounce_ms"]:
            return False
        dt_dispatch_ms = (now_ns - self.last_dispatch_ns) / 1_000_000
        if dt_dispatch_ms < self.cfg["cooldown_ms"]:
            return False
        self.last_trigger_ns = now_ns
        self.pulse_buffer.append(Pulse(timestamp_ns=now_ns, confidence=confidence))
        return True

    def evaluate_pattern(self) -> Pattern:
        if not self.pulse_buffer:
            return Pattern.INVALID
        now_ns = time.monotonic_ns()
        first_pulse_ms = (now_ns - self.pulse_buffer[0].timestamp_ns) / 1_000_000
        if len(self.pulse_buffer) == 1:
            if first_pulse_ms >= self.cfg["pattern_timeout_ms"]:
                self.pulse_buffer.clear()
                self.last_dispatch_ns = now_ns
                return Pattern.SINGLE
            return Pattern.INVALID
        if len(self.pulse_buffer) >= 2:
            dt_ms = (self.pulse_buffer[1].timestamp_ns - self.pulse_buffer[0].timestamp_ns) / 1_000_000
            self.pulse_buffer.clear()
            self.last_dispatch_ns = now_ns
            if self.cfg["double_pulse_min_ms"] <= dt_ms <= self.cfg["double_pulse_max_ms"]:
                return Pattern.DOUBLE
            return Pattern.INVALID
        return Pattern.INVALID
