import math
from dataclasses import replace
from threading import RLock

from .protection_evidence import ProtectionEvidence,ProtectionRuntimeMode


class ProtectionEvidenceSource:
    def __init__(self, initial: ProtectionEvidence) -> None:
        if not isinstance(initial,ProtectionEvidence):
            raise TypeError("initial must be ProtectionEvidence")
        if not isinstance(initial.runtime_mode,ProtectionRuntimeMode):
            raise TypeError("initial runtime_mode must be ProtectionRuntimeMode")
        self._finite(initial.observed_at,"observed_at")
        self._finite(initial.observed_monotonic,"observed_monotonic")
        self._lock=RLock()
        self._evidence=initial

    @staticmethod
    def _finite(value,name: str) -> float:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        return float(value)

    def snapshot(self) -> ProtectionEvidence:
        with self._lock:
            return self._evidence

    def publish(self, evidence: ProtectionEvidence) -> ProtectionEvidence:
        if not isinstance(evidence,ProtectionEvidence):
            raise TypeError("evidence must be ProtectionEvidence")
        if not isinstance(evidence.runtime_mode,ProtectionRuntimeMode):
            raise TypeError("evidence runtime_mode must be ProtectionRuntimeMode")
        self._finite(evidence.observed_at,"observed_at")
        observed_monotonic=self._finite(evidence.observed_monotonic,"observed_monotonic")
        with self._lock:
            if observed_monotonic < self._evidence.observed_monotonic:
                raise ValueError("published evidence monotonic time must not regress")
            if observed_monotonic == self._evidence.observed_monotonic:
                if evidence != self._evidence:
                    raise ValueError("changed evidence requires strictly newer monotonic evidence")
                return self._evidence
            self._evidence=evidence
            return self._evidence

    def transition_runtime_mode(self, mode: ProtectionRuntimeMode, *, observed_at: float, observed_monotonic: float) -> ProtectionEvidence:
        if not isinstance(mode,ProtectionRuntimeMode):
            raise TypeError("mode must be ProtectionRuntimeMode")
        observed_at=self._finite(observed_at,"observed_at")
        observed_monotonic=self._finite(observed_monotonic,"observed_monotonic")
        with self._lock:
            if observed_monotonic < self._evidence.observed_monotonic:
                raise ValueError("runtime transition monotonic time must not regress")
            if observed_monotonic == self._evidence.observed_monotonic:
                if mode is not self._evidence.runtime_mode:
                    raise ValueError("runtime mode change requires strictly newer monotonic evidence")
                return self._evidence
            self._evidence=replace(self._evidence,runtime_mode=mode,observed_at=observed_at,observed_monotonic=observed_monotonic)
            return self._evidence
