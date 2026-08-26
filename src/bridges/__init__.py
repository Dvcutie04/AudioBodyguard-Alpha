"""
Bridges Module for AQSS-36-OMEGA.
Provides canonical versioned protocols, transport envelopes, codecs, and validators.
"""

from src.bridges.codec import CanonicalCodec
from src.bridges.envelope import ObservationEnvelope
from src.bridges.protocol import MessageType, ProtocolVersion
from src.bridges.validator import EnvelopeValidator

__all__ = [
    "ProtocolVersion",
    "MessageType",
    "ObservationEnvelope",
    "CanonicalCodec",
    "EnvelopeValidator",
]
