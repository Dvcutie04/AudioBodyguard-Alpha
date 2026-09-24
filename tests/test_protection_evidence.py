from dataclasses import FrozenInstanceError

import pytest

from src.control.protection_evidence import ProtectionEvidence, ProtectionEvidenceCoordinator, ProtectionRuntimeMode
from src.control.protection_path_assessment import ProtectionPathAssessment,ProtectionPathReason
from src.control.protection_supervisor import ProtectionState, ProtectionSupervisor


def test_coordinator_preserves_immutable_capture_timestamps_and_rejects_delayed_evidence():
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=47.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)
    calls=[]
    def provider():
        calls.append(True)
        return evidence
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    coordinator=ProtectionEvidenceCoordinator(supervisor,provider,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    state=coordinator.refresh()
    assert calls==[True]
    assert state is ProtectionState.DEGRADED
    assert supervisor.reason=="STALE_EVIDENCE"
    assert supervisor.status(now=1000.0,monotonic_now=50.0).automation_allowed is False
    with pytest.raises(FrozenInstanceError):
        evidence.observed_monotonic=50.0


def test_malformed_provider_output_fails_closed():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    assert supervisor.state is ProtectionState.ACTIVE
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:object(),wall_clock=lambda:1001.0,monotonic_clock=lambda:51.0)
    state=coordinator.refresh()
    assert state is ProtectionState.PAUSED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="EVIDENCE_PROVIDER_INVALID"
    assert status.automation_allowed is False


def test_provider_exception_fails_closed():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    def failing_provider():
        raise RuntimeError("platform evidence unavailable")
    coordinator=ProtectionEvidenceCoordinator(supervisor,failing_provider,wall_clock=lambda:1001.0,monotonic_clock=lambda:51.0)
    state=coordinator.refresh()
    assert state is ProtectionState.PAUSED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="EVIDENCE_PROVIDER_FAILURE"
    assert status.automation_allowed is False


def test_invalid_evidence_fields_fail_closed():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    evidence=ProtectionEvidence(permission_granted=1,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1001.0,observed_monotonic=51.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:1001.0,monotonic_clock=lambda:51.0)
    state=coordinator.refresh()
    assert state is ProtectionState.PAUSED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="EVIDENCE_VALIDATION_FAILURE"
    assert status.automation_allowed is False


def test_fresh_evidence_reactivates_after_provider_failure():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    attempts=[]
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1002.0,observed_monotonic=52.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)
    def provider():
        attempts.append(True)
        if len(attempts)==1:
            raise RuntimeError("temporary platform interruption")
        return evidence
    wall_times=iter((1001.0,1002.0))
    monotonic_times=iter((51.0,52.0))
    coordinator=ProtectionEvidenceCoordinator(supervisor,provider,wall_clock=lambda:next(wall_times),monotonic_clock=lambda:next(monotonic_times))
    assert coordinator.refresh() is ProtectionState.PAUSED
    assert supervisor.reason=="EVIDENCE_PROVIDER_FAILURE"
    assert coordinator.refresh() is ProtectionState.ACTIVE
    status=supervisor.status(now=1002.0,monotonic_now=52.0)
    assert status.automation_allowed is True
    assert attempts==[True,True]


def test_provider_failure_recovery_survives_wall_clock_rollback():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    attempts=[]
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=900.0,observed_monotonic=51.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)
    def provider():
        attempts.append(True)
        if len(attempts)==1:
            raise RuntimeError("temporary provider failure")
        return evidence
    wall_times=iter((1000.0,900.0))
    monotonic_times=iter((50.0,51.0))
    coordinator=ProtectionEvidenceCoordinator(supervisor,provider,wall_clock=lambda:next(wall_times),monotonic_clock=lambda:next(monotonic_times))
    assert coordinator.refresh() is ProtectionState.PAUSED
    assert coordinator.refresh() is ProtectionState.ACTIVE
    assert supervisor.status(now=900.0,monotonic_now=51.0).automation_allowed is True


def test_resource_ineligible_evidence_degrades_supervisor():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=False,reason=ProtectionPathReason.RESOURCE_INELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.DEGRADED
    status=supervisor.status(now=1000.0,monotonic_now=50.0)
    assert status.reason=="PROTECTION_PATH_INELIGIBLE"
    assert status.automation_allowed is False


def test_evidence_derives_path_eligibility_from_typed_assessment():
    path=ProtectionPathAssessment(eligible=False,reason=ProtectionPathReason.STORAGE_INELIGIBLE)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)
    assert evidence.protection_path is path
    assert evidence.protection_path_eligible is False
    assert evidence.protection_path_reason is ProtectionPathReason.STORAGE_INELIGIBLE


def test_storage_ineligible_evidence_requires_recovery_without_false_resource_label():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    path=ProtectionPathAssessment(eligible=False,reason=ProtectionPathReason.STORAGE_INELIGIBLE)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.RECOVERY_REQUIRED
    assert evidence.protection_path_reason is ProtectionPathReason.STORAGE_INELIGIBLE
    status=supervisor.status(now=1000.0,monotonic_now=50.0)
    assert status.reason=="PROTECTION_PATH_INELIGIBLE"
    assert status.automation_allowed is False


def test_contradictory_typed_path_evidence_fails_closed():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    assert supervisor.state is ProtectionState.ACTIVE
    forged=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.STORAGE_INELIGIBLE)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=forged,observed_at=1001.0,observed_monotonic=51.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:1001.0,monotonic_clock=lambda:51.0)
    assert coordinator.refresh() is ProtectionState.PAUSED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="EVIDENCE_VALIDATION_FAILURE"
    assert status.automation_allowed is False


def test_deferred_maintenance_cannot_claim_active_protection():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.DEFERRED_MAINTENANCE)
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.PAUSED
    status=supervisor.status(now=1000.0,monotonic_now=50.0)
    assert status.reason=="RUNTIME_MODE_INELIGIBLE"
    assert status.automation_allowed is False


@pytest.mark.parametrize("mode",(ProtectionRuntimeMode.FOREGROUND_INTERACTIVE,ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS))
def test_eligible_runtime_modes_can_activate_with_valid_evidence(mode):
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=mode)
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    assert supervisor.automation_allowed is True


def test_suspended_runtime_cannot_claim_active_protection():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.SUSPENDED)
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.PAUSED
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


def test_malformed_runtime_mode_fails_closed():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode="FOREGROUND_INTERACTIVE")
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.PAUSED
    assert supervisor.reason=="EVIDENCE_VALIDATION_FAILURE"
    assert supervisor.automation_allowed is False


def test_runtime_mode_contract_and_fresh_reactivation():
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    evidence=[ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.DEFERRED_MAINTENANCE),ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE),ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1001.0,observed_monotonic=51.0,runtime_mode=ProtectionRuntimeMode.FOREGROUND_INTERACTIVE)]
    times=iter(((1000.0,50.0),(1000.0,50.0),(1001.0,51.0)))
    current=[None]
    def wall_clock():
        current[0]=next(times)
        return current[0][0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence.pop(0),wall_clock=wall_clock,monotonic_clock=lambda:current[0][1])
    assert coordinator.refresh() is ProtectionState.PAUSED
    assert coordinator.refresh() is ProtectionState.PAUSED
    assert supervisor.reason=="FRESH_VALIDATION_REQUIRED"
    assert coordinator.refresh() is ProtectionState.ACTIVE
    assert supervisor.reason=="VALIDATED"
    assert supervisor.automation_allowed is True
