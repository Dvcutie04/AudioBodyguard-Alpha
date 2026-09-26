"""Read-only reference projections for AQSS session explanations.

This module cannot issue authority or verify a real output. Producers must
qualify their own sources; a constructed event is only a reported observation.
User-facing history is separate from durable execution/finality journals.
"""

import json
import math
import re
from dataclasses import dataclass

from src.control.device_fabric_bridge import BridgeResult
from src.control.media_control_verified_state import VerifiedMediaControlState
from src.control.protection_supervisor import ProtectionState
from src.device_fabric.contracts import (
    ActuationReceipt,
    ActuationStatus,
    PhysicalVerificationRecord,
    VerificationStatus,
)


_REASON = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
_EXPORT_REASONS = frozenset({
    "AUTHORITY_INVALID", "CONNECTIVITY_UNAVAILABLE", "FRESH_VALIDATION_REQUIRED",
    "FUTURE_EVIDENCE", "FUTURE_MONOTONIC_EVIDENCE", "MONOTONIC_BASELINE_REQUIRED",
    "NON_MONOTONIC_CLOCK", "NON_MONOTONIC_EVIDENCE", "NOT_VALIDATED",
    "PERMISSION_DENIED", "PROTECTION_PATH_INELIGIBLE", "RUNTIME_INELIGIBLE",
    "SENSOR_UNAVAILABLE", "STALE_EVIDENCE", "VALIDATED", "USER_PAUSED",
    "PATH_ELIGIBLE", "POST_CONDITION_UNOBSERVED", "REFERENCE_ONLY",
})


def _identity(value: object, name: str) -> None:
    if type(value) is not str or not value.strip() or value != value.strip() or len(value) > 256:
        raise ValueError(f"invalid {name}")


def _time(value: object, name: str) -> None:
    if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
        raise ValueError(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class CoverageEvent:
    session_id: str
    runtime_id: str
    clock_domain_id: str
    sequence: int
    observed_monotonic: float
    received_monotonic: float
    expires_monotonic: float
    state: ProtectionState
    reason: str
    user_paused: bool = False
    user_resumed: bool = False

    def __post_init__(self) -> None:
        for name in ("session_id", "runtime_id", "clock_domain_id"):
            _identity(getattr(self, name), name)
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("invalid sequence")
        for name in ("observed_monotonic", "received_monotonic", "expires_monotonic"):
            _time(getattr(self, name), name)
        if self.received_monotonic < self.observed_monotonic:
            raise ValueError("observation is after receipt")
        if self.expires_monotonic < self.observed_monotonic:
            raise ValueError("evidence expires before observation")
        if type(self.state) is not ProtectionState:
            raise ValueError("invalid protection state")
        if type(self.reason) is not str or _REASON.fullmatch(self.reason) is None:
            raise ValueError("invalid reason code")
        if type(self.user_paused) is not bool or (self.user_paused and self.state is not ProtectionState.PAUSED):
            raise ValueError("invalid user pause")
        if type(self.user_resumed) is not bool or (self.user_paused and self.user_resumed):
            raise ValueError("invalid user resume")
        # Even a code-shaped value can be a private title/identifier. Keep
        # unsupported reasons out of the privacy-side journal altogether.
        if self.reason not in _EXPORT_REASONS:
            object.__setattr__(self, "reason", "OTHER_REASON")


@dataclass(frozen=True, slots=True)
class CurrentCoverage:
    state: ProtectionState
    reason: str
    last_checked_monotonic: float | None
    secondary_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SessionRecap:
    observations: int
    missing_sequences: int
    runtime_discontinuities: int
    evicted_events: int
    active_duration_seconds: None = None
    coverage_percent: None = None


class ReadOnlySessionJournal:
    """Bounded privacy-side snapshots; never a completeness or safety journal.

    A fresh observation may describe *now*; nothing here proves the time
    between samples was covered, especially after suspension or a reboot.
    """

    def __init__(self, session_id: str, *, max_events: int = 256) -> None:
        _identity(session_id, "session_id")
        if type(max_events) is not int or not 1 <= max_events <= 4096:
            raise ValueError("invalid max_events")
        self._session_id = session_id
        self._max_events = max_events
        self._events: list[CoverageEvent] = []
        self._observations = 0
        self._missing_sequences = 0
        self._runtime_discontinuities = 0
        self._evicted_events = 0
        self._user_pause_latched = False

    @property
    def events(self) -> tuple[CoverageEvent, ...]:
        return tuple(self._events)

    @property
    def session_id(self) -> str:
        return self._session_id

    def append(self, event: CoverageEvent) -> None:
        if type(event) is not CoverageEvent or event.session_id != self._session_id:
            raise ValueError("session event mismatch")
        if self._events:
            prior = self._events[-1]
            if event.sequence <= prior.sequence:
                raise ValueError("replayed or out-of-order event")
            if event.runtime_id == prior.runtime_id:
                if event.clock_domain_id != prior.clock_domain_id:
                    raise ValueError("clock domain changed within runtime")
                if (event.received_monotonic < prior.received_monotonic
                        or event.observed_monotonic < prior.observed_monotonic):
                    raise ValueError("monotonic time rolled back within runtime")
            else:
                self._runtime_discontinuities += 1
            self._missing_sequences += event.sequence - prior.sequence - 1
        else:
            self._missing_sequences += event.sequence - 1
        if event.user_paused:
            self._user_pause_latched = True
        elif event.user_resumed:
            self._user_pause_latched = False
        self._events.append(event)
        self._observations += 1
        if len(self._events) > self._max_events:
            self._events.pop(0)
            self._evicted_events += 1

    def current(self, *, runtime_id: str, clock_domain_id: str,
                now_monotonic: float) -> CurrentCoverage:
        _identity(runtime_id, "runtime_id")
        _identity(clock_domain_id, "clock_domain_id")
        _time(now_monotonic, "now_monotonic")
        if not self._events:
            return CurrentCoverage(ProtectionState.UNKNOWN_PHYSICAL_STATE, "NO_OBSERVATION", None)
        last = self._events[-1]
        if (last.runtime_id != runtime_id or last.clock_domain_id != clock_domain_id
                or now_monotonic < last.received_monotonic):
            return CurrentCoverage(ProtectionState.UNKNOWN_PHYSICAL_STATE, "RUNTIME_OR_CLOCK_CHANGED", None,
                                   (last.reason, "USER_PAUSED") if self._user_pause_latched else (last.reason,))
        if now_monotonic > last.expires_monotonic:
            if self._user_pause_latched and last.state is ProtectionState.PAUSED:
                return CurrentCoverage(ProtectionState.PAUSED, last.reason,
                                       last.received_monotonic, ("EVIDENCE_EXPIRED",))
            return CurrentCoverage(ProtectionState.UNKNOWN_PHYSICAL_STATE, "EVIDENCE_EXPIRED",
                                   last.received_monotonic,
                                   (last.reason, "USER_PAUSED") if self._user_pause_latched else (last.reason,))
        if self._user_pause_latched and last.state is ProtectionState.ACTIVE:
            return CurrentCoverage(ProtectionState.PAUSED, "USER_PAUSED", last.received_monotonic,
                                   (last.reason,))
        if self._user_pause_latched and last.reason != "USER_PAUSED":
            return CurrentCoverage(last.state, last.reason, last.received_monotonic,
                                   ("USER_PAUSED",))
        return CurrentCoverage(last.state, last.reason, last.received_monotonic)

    def recap(self) -> SessionRecap:
        return SessionRecap(self._observations, self._missing_sequences,
                            self._runtime_discontinuities, self._evicted_events)

    def preview_redacted_export(self) -> str:
        """Derived, consent-previewable data; omits identity, absolute times and audio.

        Caller chooses if/where to export. This is not an original signed log.
        """
        return json.dumps({
            "schema_version": 1,
            "provenance": "derived, unverified read-only session samples",
            "observations": [
                {"state": event.state.value,
                 "reason": event.reason,
                 "sequence_gap_before": index > 0 and event.sequence != self._events[index - 1].sequence + 1,
                 "runtime_changed_before": index > 0 and event.runtime_id != self._events[index - 1].runtime_id}
                for index, event in enumerate(self._events)
            ],
            "recap": {
                "observations": self._observations,
                "missing_sequences": self._missing_sequences,
                "runtime_discontinuities": self._runtime_discontinuities,
                "evicted_events": self._evicted_events,
                "continuous_coverage_measured": False,
            },
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


@dataclass(frozen=True, slots=True)
class CapabilityFacts:
    """Reported prerequisites for a read-only card, not executable permission."""

    hardware: bool | None
    qualification: bool | None
    permission: bool | None
    route: bool | None
    runtime: bool | None
    evidence: bool | None
    observed_monotonic: float
    expires_monotonic: float
    clock_domain_id: str

    def __post_init__(self) -> None:
        for name in ("hardware", "qualification", "permission", "route", "runtime", "evidence"):
            if getattr(self, name) is not None and type(getattr(self, name)) is not bool:
                raise ValueError(f"invalid {name}")
        _time(self.observed_monotonic, "observed_monotonic")
        _time(self.expires_monotonic, "expires_monotonic")
        if self.expires_monotonic < self.observed_monotonic:
            raise ValueError("capability evidence expires before observation")
        _identity(self.clock_domain_id, "clock_domain_id")


@dataclass(frozen=True, slots=True)
class CapabilityView:
    label: str
    reasons: tuple[str, ...]
    can_actuate: bool = False


_FACT_REASONS = {
    "hardware": "UNSUPPORTED",
    "qualification": "NOT_QUALIFIED",
    "permission": "PERMISSION_DENIED",
    "route": "ROUTE_UNAVAILABLE",
    "runtime": "RUNTIME_INELIGIBLE",
    "evidence": "OBSERVATION_UNAVAILABLE",
}


def capability_view(facts: CapabilityFacts, *, now_monotonic: float,
                    clock_domain_id: str) -> CapabilityView:
    if type(facts) is not CapabilityFacts:
        raise ValueError("capability facts required")
    _time(now_monotonic, "now_monotonic")
    _identity(clock_domain_id, "clock_domain_id")
    if (clock_domain_id != facts.clock_domain_id
            or now_monotonic < facts.observed_monotonic
            or now_monotonic > facts.expires_monotonic):
        return CapabilityView("UNKNOWN", ("EVIDENCE_EXPIRED_OR_RUNTIME_CHANGED",))
    blocked = tuple(reason for name, reason in _FACT_REASONS.items()
                    if getattr(facts, name) is False)
    if blocked:
        return CapabilityView("BLOCKED", blocked)
    missing = tuple(name.upper() + "_UNKNOWN" for name in _FACT_REASONS
                    if getattr(facts, name) is None)
    return CapabilityView("UNKNOWN", missing) if missing else CapabilityView("AVAILABLE_FOR_REVIEW", ())


@dataclass(frozen=True, slots=True)
class ChangeView:
    label: str
    description: str


def change_view(result: BridgeResult) -> ChangeView:
    """Present a bridge result without promoting a receipt into physical proof."""
    if type(result) is not BridgeResult:
        raise ValueError("bridge result required")
    receipt = result.receipt
    verification = result.verification
    state = result.verified_state
    if (result.status == "EXECUTED"
            and type(receipt) is ActuationReceipt
            and receipt.status in (ActuationStatus.EXECUTED, ActuationStatus.COMMITTED)
            and type(verification) is PhysicalVerificationRecord
            and type(state) is VerifiedMediaControlState
            and verification.verification_status is VerificationStatus.VERIFIED
            and (receipt.intent_id, verification.intent_id, state.intent_id) == (result.intent_id,) * 3
            and (receipt.receipt_id, state.receipt_id) == (verification.receipt_id,) * 2
            and (receipt.device_id, state.device_id) == (verification.device_id,) * 2
            and (receipt.transaction_id, verification.transaction_id, state.transaction_id) == (result.transaction_id,) * 3
            and (receipt.capability_digest, verification.capability_digest, state.capability_digest) == (result.capability_digest,) * 3
            and (verification.authorization_digest, state.authorization_digest) == (result.authorization_digest,) * 2
            and state.observed_state_digest == verification.observed_state_digest
            and state.observed_state_evidence_digest == verification.observed_state_evidence_digest):
        return ChangeView("VERIFIED_ON_DECLARED_PATH", "The recorded media setting passed its scoped reference verification.")
    if result.status == "REJECTED" and receipt is None and verification is None and state is None:
        return ChangeView("REQUEST_REJECTED", "The request was rejected; no physical result is claimed.")
    return ChangeView("RESULT_UNCERTAIN", "The physical result is not established by this record.")
