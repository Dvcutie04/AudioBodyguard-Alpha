"""
Signal Router Module for AQSS-36-OMEGA.
Routes threat assessment outputs and acoustic perception envelopes to internal state processors.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from src.inference.threat_trajectory import TrajectoryState


@dataclass
class RoutedSignal:
    source_id: str
    destination: str
    payload: Dict[str, Any]
    priority: int = 1


class SignalRouter:
    def __init__(self):
        self.routing_table: Dict[str, str] = {
            "CRITICAL": "safety_governor",
            "ELEVATING": "haptic_engine",
            "DEESCALATING": "omotenashi_learning",
            "STABLE": "baseline_monitor",
        }
        self.dispatch_log: list = []

    def route_trajectory_state(
        self, state: TrajectoryState, payload: Optional[Dict[str, Any]] = None
    ) -> RoutedSignal:
        destination = self.routing_table.get(state.name, "baseline_monitor")
        signal = RoutedSignal(
            source_id="threat_inference",
            destination=destination,
            payload=payload or {"state": state.name},
            priority=2 if state == TrajectoryState.CRITICAL else 1,
        )
        self.dispatch_log.append(signal)
        return signal
