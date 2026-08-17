from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class DoAFeatures:
    azimuth: float
    elevation: float
    spatial_confidence: float
    phase_differences: List[float] = field(default_factory=list)

@dataclass
class SpeakerFeatures:
    speaker_embedding: List[float]
    speix_id: str
    similarity_score: float
    embedding_confidence: float

@dataclass
class RoomFeatures:
    rt60_estimate: float
    reverberation_indicator: float
    room_fingerprint: List[float]

@dataclass
class TemporalFeatures:
    voice_activity: bool
    continuity_score: float
    trajectory: Dict[str, Any]

@dataclass
class SpatialEvidence:
    doa: DoAFeatures
    speaker: SpeakerFeatures
    room: RoomFeatures
    temporal: TemporalFeatures

@dataclass
class TargetSpeakerHypothesis:
    speaker_id: str
    zone_id: str
    confidence: float
    sector_confidence: Dict[str, float]
