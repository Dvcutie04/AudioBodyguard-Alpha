import math
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from threading import RLock

from .protection_path_assessment import ProtectionPathReason


class ProtectionState(Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    PAUSED = "PAUSED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    UNKNOWN_PHYSICAL_STATE = "UNKNOWN_PHYSICAL_STATE"


@dataclass(frozen=True)
class ProtectionStatus:
    state: ProtectionState
    reason: str
    automation_allowed: bool
    observed_at: float | None
    admission_generation: int = 0


class ProtectionUnavailableError(RuntimeError):
    def __init__(self, status: ProtectionStatus) -> None:
        self.status = status
        super().__init__(f"automation unavailable: {status.reason}")


def _serialized(method):
    @wraps(method)
    def locked(self, *args, **kwargs):
        with self._lock:
            prior_state = self.state
            prior_generation = self._admission_generation
            try:
                return method(self, *args, **kwargs)
            finally:
                if prior_state is ProtectionState.ACTIVE and self.state is not ProtectionState.ACTIVE and self._admission_generation == prior_generation:
                    self._admission_generation += 1
    return locked


class ProtectionSupervisor:
    def __init__(self, *, max_evidence_age: float) -> None:
        self._lock = RLock()
        self.max_evidence_age = self._finite(max_evidence_age, "max_evidence_age")
        if self.max_evidence_age <= 0.0:
            raise ValueError("max_evidence_age must be positive")
        self.state = ProtectionState.PAUSED
        self.reason = "NOT_VALIDATED"
        self._interrupted_at = None
        self._interrupted_monotonic = None
        self._last_observed_at = None
        self._last_observed_monotonic = None
        self._reactivation_after = None
        self._reactivation_after_monotonic = None
        self._physical_state_unresolved = False
        self._unresolved_physical_transactions = set()
        self._admission_generation = 0

    @staticmethod
    def _finite(value, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        return float(value)

    @staticmethod
    def _boolean(value, name: str) -> bool:
        if type(value) is not bool:
            raise ValueError(f"{name} must be boolean")
        return value

    @property
    def automation_allowed(self) -> bool:
        return self.state is ProtectionState.ACTIVE

    @_serialized
    def status(self, *, now: float | None = None, monotonic_now: float | None = None) -> ProtectionStatus:
        current_time = None if now is None else self._finite(now, "now")
        monotonic_time = None if monotonic_now is None else self._finite(monotonic_now, "monotonic_now")
        if self.state is ProtectionState.ACTIVE and self._last_observed_at is not None:
            if monotonic_time is not None:
                if self._last_observed_monotonic is None:
                    self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
                    self.reason = "MONOTONIC_BASELINE_REQUIRED"
                elif monotonic_time < self._last_observed_monotonic:
                    self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
                    self.reason = "NON_MONOTONIC_CLOCK"
                elif monotonic_time - self._last_observed_monotonic > self.max_evidence_age:
                    self.state = ProtectionState.DEGRADED
                    self.reason = "STALE_EVIDENCE"
                    self._reactivation_after = self._last_observed_at
                    self._reactivation_after_monotonic = self._last_observed_monotonic
            elif current_time is not None:
                if self._last_observed_at > current_time:
                    self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
                    self.reason = "FUTURE_EVIDENCE"
                elif current_time - self._last_observed_at > self.max_evidence_age:
                    self.state = ProtectionState.DEGRADED
                    self.reason = "STALE_EVIDENCE"
                    self._reactivation_after = self._last_observed_at
                    self._reactivation_after_monotonic = self._last_observed_monotonic
        return ProtectionStatus(
            state=self.state,
            reason=self.reason,
            automation_allowed=self.automation_allowed,
            observed_at=self._last_observed_at,
            admission_generation=self._admission_generation,
        )

    @_serialized
    def require_automation(self, *, now: float | None = None, monotonic_now: float | None = None) -> ProtectionStatus:
        status = self.status(now=now, monotonic_now=monotonic_now)
        if not status.automation_allowed:
            raise ProtectionUnavailableError(status)
        return status

    @_serialized
    def interrupt(self, reason: str, *, now: float, monotonic_now: float | None = None, physical_state_known: bool = True, physical_transaction_id: str | None = None) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be nonempty")
        physical_state_known = self._boolean(physical_state_known, "physical_state_known")
        if physical_transaction_id is not None and (type(physical_transaction_id) is not str or not physical_transaction_id.strip() or physical_transaction_id != physical_transaction_id.strip()):
            raise ValueError("physical_transaction_id must be a nonempty identifier")
        if physical_state_known and physical_transaction_id is not None:
            raise ValueError("known physical state cannot declare an unresolved transaction")
        now = self._finite(now, "now")
        monotonic_now = None if monotonic_now is None else self._finite(monotonic_now, "monotonic_now")
        if monotonic_now is not None:
            if self._interrupted_monotonic is not None and monotonic_now < self._interrupted_monotonic:
                raise ValueError("interruption monotonic time must be monotonic")
            self._interrupted_monotonic = monotonic_now
        elif self._interrupted_at is not None and now < self._interrupted_at:
            raise ValueError("interruption time must be monotonic")
        self._interrupted_at = now
        if physical_state_known is not True:
            if physical_transaction_id is None:
                self._physical_state_unresolved = True
            else:
                self._unresolved_physical_transactions.add(physical_transaction_id)
        self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE if self._physical_state_unresolved or self._unresolved_physical_transactions else ProtectionState.PAUSED
        self.reason = reason

    @_serialized
    def require_revalidation(self, reason: str, *, observed_at: float | None, now: float, monotonic_now: float | None = None, physical_state_known: bool = True) -> ProtectionState:
        if not isinstance(reason,str) or not reason.strip() or reason!=reason.strip():
            raise ValueError("reason must be a nonempty identifier")
        observed_at=None if observed_at is None else self._finite(observed_at,"observed_at")
        now=self._finite(now,"now")
        monotonic_now=None if monotonic_now is None else self._finite(monotonic_now,"monotonic_now")
        physical_state_known=self._boolean(physical_state_known,"physical_state_known")
        self._last_observed_at=observed_at
        self._last_observed_monotonic=None
        self._reactivation_after=now
        self._reactivation_after_monotonic=monotonic_now
        if physical_state_known is not True:
            self._physical_state_unresolved=True
        self.reason=reason
        if self._physical_state_unresolved or self._unresolved_physical_transactions:
            self.state=ProtectionState.UNKNOWN_PHYSICAL_STATE
            return self.state
        self.state=ProtectionState.RECOVERY_REQUIRED
        return self.state

    @_serialized
    def resolve_physical_transaction(self, transaction_id: str, *, now: float, monotonic_now: float | None = None) -> ProtectionState:
        if type(transaction_id) is not str or not transaction_id.strip() or transaction_id != transaction_id.strip():
            raise ValueError("transaction_id must be a nonempty identifier")
        now = self._finite(now, "now")
        monotonic_now = None if monotonic_now is None else self._finite(monotonic_now, "monotonic_now")
        if transaction_id not in self._unresolved_physical_transactions:
            self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
            return self.state
        self._unresolved_physical_transactions.remove(transaction_id)
        if self._physical_state_unresolved or self._unresolved_physical_transactions:
            self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
            return self.state
        self.state = ProtectionState.PAUSED
        self.reason = "FRESH_VALIDATION_REQUIRED"
        self._reactivation_after = now
        self._reactivation_after_monotonic = monotonic_now
        return self.state

    @_serialized
    def validate(self, *, permission_granted: bool, runtime_eligible: bool, sensor_available: bool, connected: bool, authority_valid: bool, protection_path_eligible: bool, observed_at: float, now: float, observed_monotonic: float | None = None, monotonic_now: float | None = None, protection_path_reason: ProtectionPathReason | None = None) -> ProtectionState:
        permission_granted = self._boolean(permission_granted, "permission_granted")
        runtime_eligible = self._boolean(runtime_eligible, "runtime_eligible")
        sensor_available = self._boolean(sensor_available, "sensor_available")
        connected = self._boolean(connected, "connected")
        authority_valid = self._boolean(authority_valid, "authority_valid")
        protection_path_eligible = self._boolean(protection_path_eligible, "protection_path_eligible")
        if protection_path_reason is not None:
            if not isinstance(protection_path_reason,ProtectionPathReason):
                raise ValueError("protection_path_reason must be ProtectionPathReason")
            if protection_path_eligible is not (protection_path_reason is ProtectionPathReason.ELIGIBLE):
                raise ValueError("protection path eligibility and reason are inconsistent")
        observed_at = self._finite(observed_at, "observed_at")
        now = self._finite(now, "now")
        monotonic_now = None if monotonic_now is None else self._finite(monotonic_now, "monotonic_now")
        observed_monotonic = monotonic_now if observed_monotonic is None else self._finite(observed_monotonic, "observed_monotonic")
        if self._physical_state_unresolved or self._unresolved_physical_transactions:
            self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
            return self.state
        if self._interrupted_monotonic is not None:
            evidence_not_after_interruption = observed_monotonic is None or observed_monotonic <= self._interrupted_monotonic
        else:
            evidence_not_after_interruption = self._interrupted_at is not None and observed_at <= self._interrupted_at
        if self._reactivation_after_monotonic is not None:
            evidence_not_after_reactivation = observed_monotonic is None or observed_monotonic <= self._reactivation_after_monotonic
        else:
            evidence_not_after_reactivation = self._reactivation_after is not None and observed_at <= self._reactivation_after
        if self._last_observed_monotonic is not None and observed_monotonic is not None:
            evidence_regressed = observed_monotonic < self._last_observed_monotonic
        else:
            evidence_regressed = self._last_observed_at is not None and observed_at < self._last_observed_at
        if evidence_regressed:
            self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
            self.reason = "NON_MONOTONIC_EVIDENCE"
            return self.state
        if observed_at <= now:
            self._last_observed_at = observed_at
            if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now:
                self._last_observed_monotonic = observed_monotonic
        if permission_granted is not True:
            self.state = ProtectionState.PAUSED
            self.reason = "PERMISSION_DENIED"
            self._reactivation_after = observed_at if observed_at <= now else now
            self._reactivation_after_monotonic = observed_monotonic if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now else None
        elif runtime_eligible is not True:
            self.state = ProtectionState.PAUSED
            self.reason = "RUNTIME_INELIGIBLE"
            self._reactivation_after = observed_at if observed_at <= now else now
            self._reactivation_after_monotonic = observed_monotonic if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now else None
        elif sensor_available is not True:
            self.state = ProtectionState.DEGRADED
            self.reason = "SENSOR_UNAVAILABLE"
            self._reactivation_after = observed_at if observed_at <= now else now
            self._reactivation_after_monotonic = observed_monotonic if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now else None
        elif connected is not True:
            self.state = ProtectionState.DEGRADED
            self.reason = "CONNECTIVITY_UNAVAILABLE"
            self._reactivation_after = observed_at if observed_at <= now else now
            self._reactivation_after_monotonic = observed_monotonic if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now else None
        elif authority_valid is not True:
            self.state = ProtectionState.RECOVERY_REQUIRED
            self.reason = "AUTHORITY_INVALID"
            self._reactivation_after = observed_at if observed_at <= now else now
            self._reactivation_after_monotonic = observed_monotonic if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now else None
        elif protection_path_eligible is not True:
            self.state = ProtectionState.RECOVERY_REQUIRED if protection_path_reason is ProtectionPathReason.STORAGE_INELIGIBLE else ProtectionState.DEGRADED
            self.reason = "PROTECTION_PATH_INELIGIBLE"
            self._reactivation_after = observed_at if observed_at <= now else now
            self._reactivation_after_monotonic = observed_monotonic if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now else None
        elif observed_at > now:
            self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
            self.reason = "FUTURE_EVIDENCE"
        elif observed_monotonic is not None and monotonic_now is not None and observed_monotonic > monotonic_now:
            self.state = ProtectionState.UNKNOWN_PHYSICAL_STATE
            self.reason = "FUTURE_MONOTONIC_EVIDENCE"
        elif observed_monotonic is not None and monotonic_now is not None and monotonic_now - observed_monotonic > self.max_evidence_age:
            self.state = ProtectionState.DEGRADED
            self.reason = "STALE_EVIDENCE"
            self._reactivation_after = observed_at if observed_at <= now else now
            self._reactivation_after_monotonic = observed_monotonic if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now else None
        elif now - observed_at > self.max_evidence_age:
            self.state = ProtectionState.DEGRADED
            self.reason = "STALE_EVIDENCE"
            self._reactivation_after = observed_at if observed_at <= now else now
            self._reactivation_after_monotonic = observed_monotonic if observed_monotonic is None or monotonic_now is None or observed_monotonic <= monotonic_now else None
        elif evidence_not_after_interruption or evidence_not_after_reactivation:
            self.state = ProtectionState.PAUSED
            self.reason = "FRESH_VALIDATION_REQUIRED"
        else:
            self.state = ProtectionState.ACTIVE
            self.reason = "VALIDATED"
            self._reactivation_after = None
            self._reactivation_after_monotonic = None
        return self.state
