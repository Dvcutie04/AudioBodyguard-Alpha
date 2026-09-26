"""Bounded, read-only reference samples for a private session timeline.

The Python supervisor reports software eligibility, not qualified native
capture or physical output. Its ACTIVE state is always projected as UNKNOWN.
Capture and publication are separate so delayed or failed publication cannot
quietly refresh a sample. This in-process object does not detect silent OS
suspension, authenticate events, or persist a complete event stream.
"""

import math
from dataclasses import dataclass
from threading import RLock

from .protection_supervisor import ProtectionState, ProtectionStatus, ProtectionSupervisor
from .session_evidence_view import (
    CoverageEvent, ReadOnlySessionJournal, _EXPORT_REASONS, _REASON,
    _identity, _time,
)


@dataclass(frozen=True, slots=True)
class _Capture:
    sequence: int
    observed_monotonic: float
    expires_monotonic: float
    state: ProtectionState
    reason: str
    admission_generation: int


def _project(status: ProtectionStatus) -> tuple[ProtectionState, str]:
    if status.state is ProtectionState.ACTIVE:
        return ProtectionState.UNKNOWN_PHYSICAL_STATE, "REFERENCE_ONLY"
    reason = status.reason
    if type(reason) is not str or _REASON.fullmatch(reason) is None or reason not in _EXPORT_REASONS:
        reason = "OTHER_REASON"
    return status.state, reason


class ReferenceSessionEventProducer:
    """One-slot sample publisher; one producer per in-memory session journal.

    The caller's monotonic times must come from the declared runtime clock.
    No timestamp here proves an OS callback arrived during suspension.
    A dropped/overwritten sample consumes its sequence when captured, so a
    later publication exposes a *known* gap without asserting completeness.
    """

    def __init__(self, supervisor: ProtectionSupervisor,
                 journal: ReadOnlySessionJournal, *, runtime_id: str,
                 clock_domain_id: str) -> None:
        if type(supervisor) is not ProtectionSupervisor or type(journal) is not ReadOnlySessionJournal:
            raise ValueError("reference supervisor and session journal required")
        _identity(runtime_id, "runtime_id")
        _identity(clock_domain_id, "clock_domain_id")
        last = journal.events[-1] if journal.events else None
        if last is not None and last.runtime_id == runtime_id and last.clock_domain_id != clock_domain_id:
            raise ValueError("clock domain changed within runtime")
        self._supervisor = supervisor
        self._journal = journal
        self._runtime_id = runtime_id
        self._clock_domain_id = clock_domain_id
        self._next_sequence = 1 if last is None else last.sequence + 1
        self._last_capture = last.received_monotonic if last is not None and last.runtime_id == runtime_id else None
        self._pending: _Capture | None = None
        self._lock = RLock()

    def capture(self, *, monotonic_now: float) -> int:
        """Sample current supervisor state; replace any unreported sample."""
        _time(monotonic_now, "monotonic_now")
        with self._lock:
            if self._last_capture is not None and monotonic_now < self._last_capture:
                raise ValueError("capture clock rolled back")
            if not math.isfinite(monotonic_now + self._supervisor.max_evidence_age):
                raise ValueError("sample expiry is not finite")
            status = self._supervisor.status(monotonic_now=monotonic_now)
            state, reason = _project(status)
            sequence = self._next_sequence
            self._pending = _Capture(sequence, monotonic_now,
                                     monotonic_now + self._supervisor.max_evidence_age,
                                     state, reason,
                                     status.admission_generation)
            self._next_sequence += 1
            self._last_capture = monotonic_now
            return sequence

    def publish(self, sequence: int, *, received_monotonic: float) -> CoverageEvent:
        """Append a captured sample; failed writes retain the pending sample."""
        _time(received_monotonic, "received_monotonic")
        with self._lock:
            pending = self._pending
            if type(sequence) is not int or pending is None or sequence != pending.sequence:
                raise ValueError("capture superseded or already published")
            if received_monotonic < pending.observed_monotonic:
                raise ValueError("receipt precedes capture")
            status = self._supervisor.status(monotonic_now=received_monotonic)
            current_state, current_reason = _project(status)
            unchanged = ((current_state, current_reason, status.admission_generation)
                         == (pending.state, pending.reason, pending.admission_generation))
            event = CoverageEvent(
                session_id=self._journal.session_id, runtime_id=self._runtime_id,
                clock_domain_id=self._clock_domain_id, sequence=sequence,
                observed_monotonic=pending.observed_monotonic,
                received_monotonic=received_monotonic,
                expires_monotonic=pending.expires_monotonic,
                state=pending.state if unchanged else ProtectionState.UNKNOWN_PHYSICAL_STATE,
                reason=pending.reason if unchanged else "REFERENCE_ONLY",
            )
            self._journal.append(event)
            self._pending = None
            self._last_capture = received_monotonic
            return event
