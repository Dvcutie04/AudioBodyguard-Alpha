from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import time

from .protection_path_assessment import ProtectionPathAssessment,ProtectionPathReason
from .protection_supervisor import ProtectionState, ProtectionSupervisor


class ProtectionRuntimeMode(Enum):
    FOREGROUND_INTERACTIVE="FOREGROUND_INTERACTIVE"
    USER_VISIBLE_CONTINUOUS="USER_VISIBLE_CONTINUOUS"
    DEFERRED_MAINTENANCE="DEFERRED_MAINTENANCE"
    SUSPENDED="SUSPENDED"

    @property
    def protection_eligible(self) -> bool:
        return self in (ProtectionRuntimeMode.FOREGROUND_INTERACTIVE,ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)


@dataclass(frozen=True, slots=True)
class ProtectionEvidence:
    permission_granted: bool
    runtime_eligible: bool
    sensor_available: bool
    connected: bool
    authority_valid: bool
    protection_path: ProtectionPathAssessment
    observed_at: float
    observed_monotonic: float
    runtime_mode: ProtectionRuntimeMode

    @property
    def protection_path_eligible(self) -> bool:
        if not isinstance(self.protection_path,ProtectionPathAssessment):
            raise TypeError("protection_path must be ProtectionPathAssessment")
        if type(self.protection_path.eligible) is not bool or not isinstance(self.protection_path.reason,ProtectionPathReason):
            raise TypeError("protection_path assessment is malformed")
        if self.protection_path.eligible is not (self.protection_path.reason is ProtectionPathReason.ELIGIBLE):
            raise ValueError("protection_path assessment is inconsistent")
        return self.protection_path.eligible

    @property
    def protection_path_reason(self) -> ProtectionPathReason:
        self.protection_path_eligible
        return self.protection_path.reason


class ProtectionEvidenceCoordinator:
    def __init__(self, supervisor: ProtectionSupervisor, provider: Callable[[], ProtectionEvidence], *, wall_clock: Callable[[], float] = time.time, monotonic_clock: Callable[[], float] = time.monotonic):
        self._supervisor = supervisor
        self._provider = provider
        self._wall_clock = wall_clock
        self._monotonic_clock = monotonic_clock

    def refresh(self) -> ProtectionState:
        try:
            evidence = self._provider()
        except Exception:
            now = self._wall_clock()
            monotonic_now = self._monotonic_clock()
            self._supervisor.interrupt("EVIDENCE_PROVIDER_FAILURE", now=now, monotonic_now=monotonic_now)
            return self._supervisor.state
        if not isinstance(evidence, ProtectionEvidence):
            now = self._wall_clock()
            monotonic_now = self._monotonic_clock()
            self._supervisor.interrupt("EVIDENCE_PROVIDER_INVALID", now=now, monotonic_now=monotonic_now)
            return self._supervisor.state
        now = self._wall_clock()
        monotonic_now = self._monotonic_clock()
        try:
            if not isinstance(evidence.runtime_mode,ProtectionRuntimeMode):
                raise TypeError("runtime_mode must be ProtectionRuntimeMode")
            if evidence.runtime_mode.protection_eligible is not True:
                self._supervisor.interrupt("RUNTIME_MODE_INELIGIBLE",now=now,monotonic_now=monotonic_now)
                return self._supervisor.state
            return self._supervisor.validate(permission_granted=evidence.permission_granted,runtime_eligible=evidence.runtime_eligible,sensor_available=evidence.sensor_available,connected=evidence.connected,authority_valid=evidence.authority_valid,protection_path_eligible=evidence.protection_path_eligible,observed_at=evidence.observed_at,now=now,observed_monotonic=evidence.observed_monotonic,monotonic_now=monotonic_now,protection_path_reason=evidence.protection_path_reason)
        except (TypeError, ValueError, OverflowError):
            self._supervisor.interrupt("EVIDENCE_VALIDATION_FAILURE", now=now, monotonic_now=monotonic_now)
            return self._supervisor.state
