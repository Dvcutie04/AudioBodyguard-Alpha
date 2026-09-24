from dataclasses import dataclass, field
from typing import Dict, Any
import time

@dataclass
class SignalContext:
    device_id: str
    location_zone: str
    ambient_db: float
    confidence_threshold: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RoutedObservation:
    event_id: str
    timestamp: float
    priority: int
    policy_action: str
    context: SignalContext
    raw_metrics: Dict[str, Any]
    routed: bool = True

class SignalRouter:
    def __init__(self, default_priority: int = 2):
        self.default_priority = default_priority
        self.routing_table = {"ANOMALY_CRITICAL": "dispatch_immediate", "ANOMALY_WARNING": "queue_for_review", "AMBIENT_NOISE": "suppress"}

    def evaluate_priority(self, classification: str, confidence: float, ambient_db: float) -> int:
        if classification == "ANOMALY_CRITICAL" and confidence > 0.85: return 5
        elif classification == "ANOMALY_CRITICAL": return 4
        elif classification == "ANOMALY_WARNING" and confidence > 0.75: return 3
        elif classification == "ANOMALY_WARNING": return 2
        return 1

    def route_observation(self, event_id: str, classification: str, confidence: float, raw_metrics: Dict[str, Any], context: SignalContext) -> RoutedObservation:
        priority = self.evaluate_priority(classification, confidence, context.ambient_db)
        policy_action = self.routing_table.get(classification, "queue_for_review")
        if classification == "AMBIENT_NOISE" and confidence < context.confidence_threshold:
            policy_action = "suppress"
            priority = 1
        return RoutedObservation(event_id=event_id, timestamp=time.time(), priority=priority, policy_action=policy_action, context=context, raw_metrics=raw_metrics)
