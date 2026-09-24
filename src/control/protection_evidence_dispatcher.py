import math
import time

from .protection_evidence import ProtectionEvidence,ProtectionEvidenceCoordinator,ProtectionRuntimeMode
from .protection_evidence_source import ProtectionEvidenceSource
from .protection_supervisor import ProtectionState,ProtectionSupervisor


class ProtectionEvidenceEventDispatcher:
    def __init__(self, supervisor: ProtectionSupervisor, source: ProtectionEvidenceSource, coordinator: ProtectionEvidenceCoordinator, *, wall_clock=time.time, monotonic_clock=time.monotonic) -> None:
        if not isinstance(supervisor,ProtectionSupervisor):
            raise TypeError("supervisor must be ProtectionSupervisor")
        if not isinstance(source,ProtectionEvidenceSource):
            raise TypeError("source must be ProtectionEvidenceSource")
        if not isinstance(coordinator,ProtectionEvidenceCoordinator):
            raise TypeError("coordinator must be ProtectionEvidenceCoordinator")
        if not callable(wall_clock) or not callable(monotonic_clock):
            raise TypeError("dispatcher clocks must be callable")
        self._supervisor=supervisor
        self._source=source
        self._coordinator=coordinator
        self._wall_clock=wall_clock
        self._monotonic_clock=monotonic_clock

    @staticmethod
    def _finite(value,name: str) -> float:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        return float(value)

    @staticmethod
    def _is_negative(evidence: ProtectionEvidence) -> bool:
        booleans=(evidence.permission_granted,evidence.runtime_eligible,evidence.sensor_available,evidence.connected,evidence.authority_valid)
        if any(type(value) is not bool for value in booleans):
            raise TypeError("evidence booleans must be boolean")
        if not isinstance(evidence.runtime_mode,ProtectionRuntimeMode):
            raise TypeError("runtime_mode must be ProtectionRuntimeMode")
        return any(value is not True for value in booleans) or evidence.runtime_mode.protection_eligible is not True or evidence.protection_path_eligible is not True

    def apply(self, evidence: ProtectionEvidence) -> ProtectionState:
        if not isinstance(evidence,ProtectionEvidence):
            event_now=self._finite(self._wall_clock(),"wall_clock")
            event_monotonic=self._finite(self._monotonic_clock(),"monotonic_clock")
            self._supervisor.interrupt("EVIDENCE_EVENT_INVALID",now=event_now,monotonic_now=event_monotonic)
            return self._supervisor.state
        try:
            event_now=self._finite(evidence.observed_at,"observed_at")
            event_monotonic=self._finite(evidence.observed_monotonic,"observed_monotonic")
        except (TypeError,ValueError,OverflowError):
            event_now=self._finite(self._wall_clock(),"wall_clock")
            event_monotonic=self._finite(self._monotonic_clock(),"monotonic_clock")
            self._supervisor.interrupt("EVIDENCE_EVENT_INVALID",now=event_now,monotonic_now=event_monotonic)
            return self._supervisor.state
        try:
            negative=self._is_negative(evidence)
        except (TypeError,ValueError,OverflowError):
            self._supervisor.interrupt("EVIDENCE_EVENT_INVALID",now=event_now,monotonic_now=event_monotonic)
            return self._supervisor.state
        try:
            if negative:
                self._supervisor.interrupt("EVIDENCE_UPDATE_PENDING",now=event_now,monotonic_now=event_monotonic)
            self._source.publish(evidence)
        except Exception:
            failure_now=self._finite(self._wall_clock(),"wall_clock")
            failure_monotonic=self._finite(self._monotonic_clock(),"monotonic_clock")
            self._supervisor.interrupt("EVIDENCE_PUBLICATION_FAILURE",now=failure_now,monotonic_now=failure_monotonic)
            return self._supervisor.state
        return self._coordinator.refresh()
