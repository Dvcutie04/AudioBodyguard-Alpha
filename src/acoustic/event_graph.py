from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class EdgeType(Enum):
    TEMPORAL_NEXT = auto()
    CONTINUES = auto()
    SUPPORTS = auto()
    CONTRADICTS = auto()


@dataclass(frozen=True)
class AcousticEvent:
    event_id: str
    node_id: str
    sequence_start: int
    sequence_end: int
    t_start_ns: int
    t_end_ns: int
    room_id: str
    event_type: str
    spl_estimate: float
    spl_variance: float
    features: Dict[str, float]
    observation_count: int
    confidence: float
    lineage_root: str
    lineage_digest: str


@dataclass(frozen=True)
class EventEdge:
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0


class BoundedAcousticEventGraph:

    def __init__(self, max_events: int = 100, max_retention_ns: int = 30_000_000_000):
        self.max_events = max_events
        self.max_retention_ns = max_retention_ns
        self.nodes: Dict[str, AcousticEvent] = {}
        self.edges: List[EventEdge] = []

    def add_event(self, event: AcousticEvent) -> None:
        self.nodes[event.event_id] = event
        self._prune()

    def add_edge(self, source_id: str, target_id: str, edge_type: EdgeType, weight: float = 1.0) -> None:
        if source_id in self.nodes and target_id in self.nodes:
            self.edges.append(EventEdge(source_id, target_id, edge_type, weight))

    def _prune(self) -> None:
        if len(self.nodes) > self.max_events:
            sorted_keys = sorted(self.nodes.keys(), key=lambda k: self.nodes[k].t_start_ns)
            overflow = len(sorted_keys) - self.max_events
            for k in sorted_keys[:overflow]:
                del self.nodes[k]
                self.edges = [e for e in self.edges if e.source_id != k and e.target_id != k]
