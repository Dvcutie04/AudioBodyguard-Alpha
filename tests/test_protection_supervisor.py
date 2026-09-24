from dataclasses import FrozenInstanceError
from threading import Event, Thread

from src.control.protection_supervisor import ProtectionState, ProtectionStatus, ProtectionSupervisor, ProtectionUnavailableError


def test_interruption_pauses_and_requires_fresh_validation_before_reactivation():
    supervisor = ProtectionSupervisor(max_evidence_age=2.0)
    valid = dict(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True, observed_at=100.0)
    assert supervisor.state is ProtectionState.PAUSED
    assert supervisor.automation_allowed is False
    supervisor.validate(**valid, now=100.0)
    assert supervisor.state is ProtectionState.ACTIVE
    assert supervisor.automation_allowed is True
    supervisor.interrupt("AUDIO_SESSION_INTERRUPTED", now=101.0)
    assert supervisor.state is ProtectionState.PAUSED
    assert supervisor.reason == "AUDIO_SESSION_INTERRUPTED"
    assert supervisor.automation_allowed is False
    supervisor.validate(**valid, now=101.5)
    assert supervisor.state is ProtectionState.PAUSED
    assert supervisor.automation_allowed is False
    valid["observed_at"] = 101.5
    supervisor.validate(**valid, now=101.5)
    assert supervisor.state is ProtectionState.ACTIVE
    assert supervisor.automation_allowed is True


def test_each_unavailable_prerequisite_has_truthful_fail_closed_state():
    base = dict(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True, observed_at=100.0)
    cases = (
        ("permission_granted", ProtectionState.PAUSED, "PERMISSION_DENIED"),
        ("runtime_eligible", ProtectionState.PAUSED, "RUNTIME_INELIGIBLE"),
        ("sensor_available", ProtectionState.DEGRADED, "SENSOR_UNAVAILABLE"),
        ("connected", ProtectionState.DEGRADED, "CONNECTIVITY_UNAVAILABLE"),
        ("authority_valid", ProtectionState.RECOVERY_REQUIRED, "AUTHORITY_INVALID"),
    )
    for field, expected_state, expected_reason in cases:
        supervisor = ProtectionSupervisor(max_evidence_age=2.0)
        evidence = dict(base)
        evidence[field] = False
        supervisor.validate(**evidence, now=100.0)
        assert supervisor.state is expected_state
        assert supervisor.reason == expected_reason
        assert supervisor.automation_allowed is False


def test_stale_future_and_exact_boundary_evidence_are_distinguished():
    base = dict(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True)
    future = ProtectionSupervisor(max_evidence_age=2.0)
    future.validate(**base, observed_at=100.001, now=100.0)
    assert future.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert future.reason == "FUTURE_EVIDENCE"
    assert future.automation_allowed is False
    stale = ProtectionSupervisor(max_evidence_age=2.0)
    stale.validate(**base, observed_at=97.999, now=100.0)
    assert stale.state is ProtectionState.DEGRADED
    assert stale.reason == "STALE_EVIDENCE"
    assert stale.automation_allowed is False
    boundary = ProtectionSupervisor(max_evidence_age=2.0)
    boundary.validate(**base, observed_at=98.0, now=100.0)
    assert boundary.state is ProtectionState.ACTIVE
    assert boundary.reason == "VALIDATED"
    assert boundary.automation_allowed is True


def test_malformed_validation_input_never_mutates_active_state():
    base = dict(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True, observed_at=100.0, now=100.0)
    invalid_updates = (
        {"permission_granted": 1},
        {"runtime_eligible": "true"},
        {"sensor_available": None},
        {"connected": 0},
        {"authority_valid": object()},
        {"observed_at": True},
        {"observed_at": float("nan")},
        {"observed_at": float("inf")},
        {"now": float("-inf")},
    )
    for update in invalid_updates:
        supervisor = ProtectionSupervisor(max_evidence_age=2.0)
        supervisor.validate(**base)
        evidence = dict(base)
        evidence.update(update)
        try:
            supervisor.validate(**evidence)
        except ValueError:
            pass
        else:
            raise AssertionError(f"malformed input was accepted: {update}")
        assert supervisor.state is ProtectionState.ACTIVE
        assert supervisor.reason == "VALIDATED"
        assert supervisor.automation_allowed is True


def test_event_time_watermarks_prevent_reordered_evidence_and_interruptions():
    valid = dict(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True)
    evidence = ProtectionSupervisor(max_evidence_age=2.0)
    evidence.validate(**valid, observed_at=100.0, now=100.0)
    evidence.validate(**valid, observed_at=99.9, now=100.5)
    assert evidence.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert evidence.reason == "NON_MONOTONIC_EVIDENCE"
    assert evidence.automation_allowed is False
    interruption = ProtectionSupervisor(max_evidence_age=2.0)
    interruption.validate(**valid, observed_at=100.0, now=100.0)
    interruption.interrupt("AUDIO_SESSION_INTERRUPTED", now=102.0)
    try:
        interruption.interrupt("LATE_CALLBACK", now=101.0)
    except ValueError:
        pass
    else:
        raise AssertionError("backward interruption time was accepted")
    assert interruption.state is ProtectionState.PAUSED
    assert interruption.reason == "AUDIO_SESSION_INTERRUPTED"
    interruption.validate(**valid, observed_at=101.5, now=102.1)
    assert interruption.state is ProtectionState.PAUSED
    assert interruption.reason == "FRESH_VALIDATION_REQUIRED"
    assert interruption.automation_allowed is False


def test_recovery_from_each_nonactive_state_requires_newer_evidence():
    valid = dict(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True)
    cases = (
        ("permission_granted", ProtectionState.PAUSED),
        ("runtime_eligible", ProtectionState.PAUSED),
        ("sensor_available", ProtectionState.DEGRADED),
        ("connected", ProtectionState.DEGRADED),
        ("authority_valid", ProtectionState.RECOVERY_REQUIRED),
    )
    for field, failure_state in cases:
        supervisor = ProtectionSupervisor(max_evidence_age=2.0)
        supervisor.validate(**valid, observed_at=100.0, now=100.0)
        failed = dict(valid)
        failed[field] = False
        supervisor.validate(**failed, observed_at=101.0, now=101.0)
        assert supervisor.state is failure_state
        supervisor.validate(**valid, observed_at=101.0, now=101.1)
        assert supervisor.state is not ProtectionState.ACTIVE
        assert supervisor.reason == "FRESH_VALIDATION_REQUIRED"
        assert supervisor.automation_allowed is False
        supervisor.validate(**valid, observed_at=101.2, now=101.2)
        assert supervisor.state is ProtectionState.ACTIVE
        assert supervisor.reason == "VALIDATED"
        assert supervisor.automation_allowed is True


def test_status_snapshot_is_immutable_and_internally_consistent():
    supervisor = ProtectionSupervisor(max_evidence_age=2.0)
    supervisor.validate(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True, observed_at=100.0, now=100.0)
    status = supervisor.status()
    assert isinstance(status, ProtectionStatus)
    assert status.state is ProtectionState.ACTIVE
    assert status.reason == "VALIDATED"
    assert status.automation_allowed is True
    assert status.observed_at == 100.0
    try:
        status.reason = "FORGED"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("status snapshot was mutable")


def test_automation_gate_fails_closed_and_returns_active_status():
    supervisor = ProtectionSupervisor(max_evidence_age=2.0)
    try:
        supervisor.require_automation()
    except ProtectionUnavailableError as error:
        assert error.status.state is ProtectionState.PAUSED
        assert error.status.reason == "NOT_VALIDATED"
        assert error.status.automation_allowed is False
    else:
        raise AssertionError("unvalidated automation was allowed")
    supervisor.validate(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True, observed_at=100.0, now=100.0)
    status = supervisor.require_automation()
    assert status.state is ProtectionState.ACTIVE
    assert status.reason == "VALIDATED"
    assert status.automation_allowed is True
    supervisor.interrupt("AUDIO_SESSION_INTERRUPTED", now=101.0)
    try:
        supervisor.require_automation()
    except ProtectionUnavailableError as error:
        assert error.status.state is ProtectionState.PAUSED
        assert error.status.reason == "AUDIO_SESSION_INTERRUPTED"
        assert error.status.automation_allowed is False
    else:
        raise AssertionError("interrupted automation was allowed")


def test_supervisor_serializes_status_and_state_transitions():
    supervisor = ProtectionSupervisor(max_evidence_age=2.0)
    supervisor.validate(permission_granted=True, runtime_eligible=True, sensor_available=True, connected=True, authority_valid=True, protection_path_eligible=True, observed_at=100.0, now=100.0)
    entered = Event()
    finished = Event()
    supervisor._lock.acquire()
    try:
        def interrupt_worker():
            entered.set()
            supervisor.interrupt("AUDIO_SESSION_INTERRUPTED", now=101.0)
            finished.set()
        worker = Thread(target=interrupt_worker)
        worker.start()
        assert entered.wait(1.0)
        assert finished.wait(0.02) is False
        assert supervisor.state is ProtectionState.ACTIVE
        assert supervisor.reason == "VALIDATED"
    finally:
        supervisor._lock.release()
    assert finished.wait(1.0)
    worker.join(1.0)
    assert worker.is_alive() is False
    status = supervisor.status()
    assert status.state is ProtectionState.PAUSED
    assert status.reason == "AUDIO_SESSION_INTERRUPTED"
    assert status.automation_allowed is False


def test_automation_gate_rechecks_evidence_age_at_commit_time():
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=100.0,now=100.0)
    assert supervisor.require_automation(now=102.0).state is ProtectionState.ACTIVE
    try:
        supervisor.require_automation(now=102.001)
    except ProtectionUnavailableError as error:
        assert error.status.state is ProtectionState.DEGRADED
        assert error.status.reason=="STALE_EVIDENCE"
        assert error.status.automation_allowed is False
        assert error.status.observed_at==100.0
    else:
        raise AssertionError("stale evidence remained authorized at commit time")
    assert supervisor.state is ProtectionState.DEGRADED
    assert supervisor.reason=="STALE_EVIDENCE"
    assert supervisor.automation_allowed is False


def test_automation_gate_rejects_clock_rollback_as_future_evidence():
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=100.0,now=100.0)
    try:
        supervisor.require_automation(now=99.999)
    except ProtectionUnavailableError as error:
        assert error.status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
        assert error.status.reason=="FUTURE_EVIDENCE"
        assert error.status.automation_allowed is False
        assert error.status.observed_at==100.0
    else:
        raise AssertionError("backward commit clock authorized future-dated evidence")
    assert supervisor.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.reason=="FUTURE_EVIDENCE"
    assert supervisor.automation_allowed is False


def test_user_visible_status_rechecks_evidence_age():
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=100.0,now=100.0)
    boundary=supervisor.status(now=102.0)
    assert boundary.state is ProtectionState.ACTIVE
    assert boundary.reason=="VALIDATED"
    stale=supervisor.status(now=102.001)
    assert stale.state is ProtectionState.DEGRADED
    assert stale.reason=="STALE_EVIDENCE"
    assert stale.automation_allowed is False
    assert stale.observed_at==100.0
    assert supervisor.state is ProtectionState.DEGRADED


def test_monotonic_freshness_ignores_wall_clock_adjustments():
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,monotonic_now=50.0)
    after_wall_rollback=supervisor.status(now=900.0,monotonic_now=51.0)
    assert after_wall_rollback.state is ProtectionState.ACTIVE
    assert after_wall_rollback.reason=="VALIDATED"
    assert after_wall_rollback.observed_at==1000.0
    stale=supervisor.status(now=1000.0,monotonic_now=52.001)
    assert stale.state is ProtectionState.DEGRADED
    assert stale.reason=="STALE_EVIDENCE"
    assert stale.automation_allowed is False
    assert stale.observed_at==1000.0


def test_commit_clock_requires_matching_monotonic_baseline():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=100.0,now=100.0)
    try:
        supervisor.require_automation(now=101.0,monotonic_now=51.0)
    except ProtectionUnavailableError as exc:
        assert exc.status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
        assert exc.status.reason=="MONOTONIC_BASELINE_REQUIRED"
        assert exc.status.automation_allowed is False
        assert supervisor.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    else:
        raise AssertionError("automation must fail closed without a matching monotonic baseline")


def test_monotonic_clock_rollback_fails_closed():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,monotonic_now=50.0)
    try:
        supervisor.require_automation(now=1001.0,monotonic_now=49.999)
    except ProtectionUnavailableError as exc:
        assert exc.status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
        assert exc.status.reason=="NON_MONOTONIC_CLOCK"
        assert exc.status.automation_allowed is False
        assert exc.status.observed_at==1000.0
        assert supervisor.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    else:
        raise AssertionError("backward monotonic time must fail closed")


def test_validation_uses_evidence_capture_monotonic_time():
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    state=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=47.0,monotonic_now=50.0)
    assert state is ProtectionState.DEGRADED
    assert supervisor.reason=="STALE_EVIDENCE"
    status=supervisor.status(now=1000.0,monotonic_now=50.0)
    assert status.state is ProtectionState.DEGRADED
    assert status.automation_allowed is False
    assert status.observed_at==1000.0


def test_future_evidence_capture_monotonic_time_fails_closed():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    state=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.001,monotonic_now=50.0)
    assert state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.reason=="FUTURE_MONOTONIC_EVIDENCE"
    status=supervisor.status(now=1000.0,monotonic_now=50.0)
    assert status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert status.reason=="FUTURE_MONOTONIC_EVIDENCE"
    assert status.automation_allowed is False
    assert status.observed_at==1000.0


def test_interrupt_uses_monotonic_time_when_wall_clock_moves_backward():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.interrupt("FIRST_INTERRUPTION",now=1000.0,monotonic_now=50.0)
    supervisor.interrupt("SECOND_INTERRUPTION",now=900.0,monotonic_now=51.0)
    status=supervisor.status(now=900.0,monotonic_now=51.0)
    assert status.state is ProtectionState.PAUSED
    assert status.reason=="SECOND_INTERRUPTION"
    assert status.automation_allowed is False


def test_reactivation_uses_monotonic_interruption_boundary():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.interrupt("PLATFORM_INTERRUPTION",now=1000.0,monotonic_now=50.0)
    state=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=900.0,now=900.0,observed_monotonic=51.0,monotonic_now=51.0)
    assert state is ProtectionState.ACTIVE
    status=supervisor.status(now=900.0,monotonic_now=51.0)
    assert status.reason=="VALIDATED"
    assert status.automation_allowed is True


def test_evidence_order_uses_monotonic_time_when_wall_clock_moves_backward():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    first=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    second=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=900.0,now=900.0,observed_monotonic=51.0,monotonic_now=51.0)
    assert first is ProtectionState.ACTIVE
    assert second is ProtectionState.ACTIVE
    status=supervisor.status(now=900.0,monotonic_now=51.0)
    assert status.reason=="VALIDATED"
    assert status.automation_allowed is True
    assert status.observed_at==900.0


def test_evidence_order_rejects_monotonic_rollback_when_wall_clock_advances():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    first=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    second=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1001.0,now=1001.0,observed_monotonic=49.0,monotonic_now=51.0)
    assert first is ProtectionState.ACTIVE
    assert second is ProtectionState.UNKNOWN_PHYSICAL_STATE
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="NON_MONOTONIC_EVIDENCE"
    assert status.automation_allowed is False
    assert status.observed_at==1000.0


def test_reactivation_after_permission_denial_uses_monotonic_boundary():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    denied=supervisor.validate(permission_granted=False,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    restored=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=900.0,now=900.0,observed_monotonic=51.0,monotonic_now=51.0)
    assert denied is ProtectionState.PAUSED
    assert restored is ProtectionState.ACTIVE
    status=supervisor.status(now=900.0,monotonic_now=51.0)
    assert status.reason=="VALIDATED"
    assert status.automation_allowed is True
    assert status.observed_at==900.0


def test_reactivation_requires_evidence_strictly_after_monotonic_boundary():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    denied=supervisor.validate(permission_granted=False,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    replayed=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1001.0,now=1001.0,observed_monotonic=50.0,monotonic_now=51.0)
    assert denied is ProtectionState.PAUSED
    assert replayed is ProtectionState.PAUSED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="FRESH_VALIDATION_REQUIRED"
    assert status.automation_allowed is False


def test_future_monotonic_evidence_does_not_poison_ordering_baseline():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    future=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=60.0,monotonic_now=50.0)
    assert future is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.status(now=1000.0,monotonic_now=50.0).reason=="FUTURE_MONOTONIC_EVIDENCE"
    recovered=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1001.0,now=1001.0,observed_monotonic=51.0,monotonic_now=51.0)
    assert recovered is ProtectionState.ACTIVE
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="VALIDATED"
    assert status.automation_allowed is True
    assert status.observed_at==1001.0


def test_future_monotonic_evidence_does_not_poison_reactivation_boundary():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    denied=supervisor.validate(permission_granted=False,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=60.0,monotonic_now=50.0)
    recovered=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1001.0,now=1001.0,observed_monotonic=51.0,monotonic_now=51.0)
    assert denied is ProtectionState.PAUSED
    assert recovered is ProtectionState.ACTIVE
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="VALIDATED"
    assert status.automation_allowed is True


def test_future_wall_evidence_does_not_poison_reactivation_boundary():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    denied=supervisor.validate(permission_granted=False,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=2000.0,now=1000.0)
    recovered=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1001.0,now=1001.0)
    assert denied is ProtectionState.PAUSED
    assert recovered is ProtectionState.ACTIVE
    status=supervisor.status(now=1001.0)
    assert status.reason=="VALIDATED"
    assert status.automation_allowed is True


def test_resource_ineligible_protection_path_cannot_remain_active():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    active=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    assert active is ProtectionState.ACTIVE
    degraded=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=False,observed_at=1001.0,now=1001.0,observed_monotonic=51.0,monotonic_now=51.0)
    assert degraded is ProtectionState.DEGRADED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="PROTECTION_PATH_INELIGIBLE"
    assert status.automation_allowed is False


def test_unobserved_physical_interruption_enters_unknown_state():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    assert supervisor.state is ProtectionState.ACTIVE
    supervisor.interrupt("POST_CONDITION_UNOBSERVED",now=1001.0,monotonic_now=51.0,physical_state_known=False)
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert status.reason=="POST_CONDITION_UNOBSERVED"
    assert status.automation_allowed is False


def test_protection_validation_cannot_erase_unknown_physical_state():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    supervisor.interrupt("POST_CONDITION_UNOBSERVED",now=1001.0,monotonic_now=51.0,physical_state_known=False)
    state=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1002.0,now=1002.0,observed_monotonic=52.0,monotonic_now=52.0)
    assert state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    status=supervisor.status(now=1002.0,monotonic_now=52.0)
    assert status.reason=="POST_CONDITION_UNOBSERVED"
    assert status.automation_allowed is False
