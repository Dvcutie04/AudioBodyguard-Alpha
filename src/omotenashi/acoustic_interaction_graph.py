from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

@dataclass(frozen=True)
class AcousticEvent:
    event_id: str
    timestamp_ns: int
    source_class: str
    spatial_sector: int
    speech_probability: float
    energy: float
    duration_ms: int

@dataclass(frozen=True)
class InteractionEdge:
    source_event_id: str
    target_event_id: str
    temporal_delta_ms: int
    spatial_delta: float
    correlation: float
    turn_transition_score: float

class AcousticInteractionGraph:
    def __init__(self):
        self.events: Dict[str, AcousticEvent] = {}
        self.edges: List[InteractionEdge] = []

    def add_event(self, event: AcousticEvent) -> None:
        self.events[event.event_id] = event

    def add_edge(self, edge: InteractionEdge) -> None:
        if edge.source_event_id in self.events and edge.target_event_id in self.events:
            self.edges.append(edge)

    def get_neighbors(self, event_id: str) -> List[InteractionEdge]:
        return [edge for edge in self.edges if edge.source_event_id == event_id or edge.target_event_id == event_id]

    def clear(self) -> None:
        self.events.clear()
        self.edges.clear()
