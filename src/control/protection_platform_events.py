from dataclasses import replace
from enum import Enum

from .protection_evidence import ProtectionEvidence,ProtectionRuntimeMode
from .protection_evidence_dispatcher import ProtectionEvidenceEventDispatcher
from .protection_evidence_source import ProtectionEvidenceSource
from .protection_supervisor import ProtectionState


class ProtectionPlatformEvent(Enum):
    APPLE_AUDIO_INTERRUPTION_BEGAN="APPLE_AUDIO_INTERRUPTION_BEGAN"
    APPLE_AUDIO_ROUTE_CHANGED="APPLE_AUDIO_ROUTE_CHANGED"
    APPLE_AUDIO_INTERRUPTION_ENDED="APPLE_AUDIO_INTERRUPTION_ENDED"
    ANDROID_AUDIO_FOCUS_LOSS="ANDROID_AUDIO_FOCUS_LOSS"
    ANDROID_AUDIO_FOCUS_LOSS_TRANSIENT="ANDROID_AUDIO_FOCUS_LOSS_TRANSIENT"
    ANDROID_AUDIO_FOCUS_GAIN="ANDROID_AUDIO_FOCUS_GAIN"


class ProtectionPlatformEventAdapter:
    def __init__(self, source: ProtectionEvidenceSource, dispatcher: ProtectionEvidenceEventDispatcher) -> None:
        if not isinstance(source,ProtectionEvidenceSource):
            raise TypeError("source must be ProtectionEvidenceSource")
        if not isinstance(dispatcher,ProtectionEvidenceEventDispatcher):
            raise TypeError("dispatcher must be ProtectionEvidenceEventDispatcher")
        self._source=source
        self._dispatcher=dispatcher

    def apply(self, event: ProtectionPlatformEvent, *, observed_at: float, observed_monotonic: float) -> ProtectionState:
        if not isinstance(event,ProtectionPlatformEvent):
            return self._dispatcher.apply(object())
        if event in (ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_BEGAN,ProtectionPlatformEvent.APPLE_AUDIO_ROUTE_CHANGED,ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_ENDED,ProtectionPlatformEvent.ANDROID_AUDIO_FOCUS_LOSS,ProtectionPlatformEvent.ANDROID_AUDIO_FOCUS_LOSS_TRANSIENT,ProtectionPlatformEvent.ANDROID_AUDIO_FOCUS_GAIN):
            current=self._source.snapshot()
            suspended=replace(current,runtime_mode=ProtectionRuntimeMode.SUSPENDED,observed_at=observed_at,observed_monotonic=observed_monotonic)
            return self._dispatcher.apply(suspended)
        return self._dispatcher.apply(object())
