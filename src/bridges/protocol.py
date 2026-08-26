from enum import Enum


class ProtocolVersion(Enum):
    AQSS_EDGE_OBSERVATION_V1 = "AQSS_EDGE_OBSERVATION_V1"


class MessageType(Enum):
    ACOUSTIC_OBSERVATION = "ACOUSTIC_OBSERVATION"
