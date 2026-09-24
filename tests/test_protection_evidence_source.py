from dataclasses import replace

import pytest

from src.control.protection_evidence import ProtectionEvidence,ProtectionEvidenceCoordinator,ProtectionRuntimeMode
from src.control.protection_evidence_source import ProtectionEvidenceSource
from src.control.protection_evidence_dispatcher import ProtectionEvidenceEventDispatcher
from src.control.protection_path_assessment import ProtectionPathAssessment,ProtectionPathReason
from src.control.protection_supervisor import ProtectionState,ProtectionSupervisor


def test_suspension_event_atomically_pauses_active_protection():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clocks=iter(((1000.0,50.0),(1001.0,51.0)))
    current=[None]
    def wall_clock():
        current[0]=next(clocks)
        return current[0][0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=wall_clock,monotonic_clock=lambda:current[0][1])
    assert coordinator.refresh() is ProtectionState.ACTIVE
    suspended=source.transition_runtime_mode(ProtectionRuntimeMode.SUSPENDED,observed_at=1001.0,observed_monotonic=51.0)
    assert suspended.runtime_mode is ProtectionRuntimeMode.SUSPENDED
    assert suspended.observed_at==1001.0
    assert suspended.observed_monotonic==51.0
    assert coordinator.refresh() is ProtectionState.PAUSED
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


def test_conflicting_runtime_transition_requires_strictly_newer_evidence():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.SUSPENDED)
    source=ProtectionEvidenceSource(initial)
    with pytest.raises(ValueError,match="strictly newer"):
        source.transition_runtime_mode(ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS,observed_at=1001.0,observed_monotonic=50.0)
    snapshot=source.snapshot()
    assert snapshot is initial
    assert snapshot.runtime_mode is ProtectionRuntimeMode.SUSPENDED
    assert snapshot.observed_at==1000.0
    assert snapshot.observed_monotonic==50.0


def test_complete_permission_revocation_snapshot_is_published_atomically():
    path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE)
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    revoked=ProtectionEvidence(permission_granted=False,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1001.0,observed_monotonic=51.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    published=source.publish(revoked)
    assert published is revoked
    assert source.snapshot() is revoked
    assert initial.permission_granted is True
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:1001.0,monotonic_clock=lambda:51.0)
    assert coordinator.refresh() is ProtectionState.PAUSED
    assert supervisor.reason=="PERMISSION_DENIED"
    assert supervisor.automation_allowed is False


@pytest.mark.parametrize("field,value",(("observed_at",float("nan")),("observed_at",float("inf")),("observed_at",True),("observed_monotonic",float("nan")),("observed_monotonic",float("-inf")),("observed_monotonic",False)))
def test_source_rejects_nonfinite_or_boolean_initial_timestamps(field,value):
    valid=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    with pytest.raises(ValueError,match=field):
        ProtectionEvidenceSource(replace(valid,**{field:value}))


def test_negative_event_pauses_before_failed_publication():
    path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE)
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    revoked=replace(initial,permission_granted=False,observed_at=1001.0,observed_monotonic=51.0)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    class FailingSource(ProtectionEvidenceSource):
        def __init__(self,evidence):
            super().__init__(evidence)
            self.calls=0
        def publish(self,evidence):
            self.calls+=1
            assert supervisor.state is ProtectionState.PAUSED
            assert supervisor.automation_allowed is False
            raise OSError("evidence store unavailable")
    source=FailingSource(initial)
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    # Failure handling must use the same synthetic clock domain as the evidence.
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:1001.0,monotonic_clock=lambda:51.0)
    assert dispatcher.apply(revoked) is ProtectionState.PAUSED
    assert source.calls==1
    assert supervisor.reason=="EVIDENCE_PUBLICATION_FAILURE"
    assert supervisor.automation_allowed is False
    assert source.snapshot() is initial


def test_malformed_event_pauses_without_publication():
    path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE)
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    malformed=replace(initial,permission_granted=1,observed_at=1001.0,observed_monotonic=51.0)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    assert dispatcher.apply(malformed) is ProtectionState.PAUSED
    assert supervisor.reason=="EVIDENCE_EVENT_INVALID"
    assert supervisor.automation_allowed is False
    assert source.snapshot() is initial


def test_invalid_event_timestamp_uses_trusted_clock_to_pause():
    path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE)
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    malformed=replace(initial,observed_at=float("nan"),observed_monotonic=float("inf"))
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:1001.0,monotonic_clock=lambda:51.0)
    assert dispatcher.apply(malformed) is ProtectionState.PAUSED
    assert supervisor.reason=="EVIDENCE_EVENT_INVALID"
    assert supervisor.automation_allowed is False
    assert source.snapshot() is initial


def test_wrong_type_event_uses_trusted_clock_to_pause():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:1000.0,monotonic_clock=lambda:50.0)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:1001.0,monotonic_clock=lambda:51.0)
    assert dispatcher.apply(object()) is ProtectionState.PAUSED
    assert supervisor.reason=="EVIDENCE_EVENT_INVALID"
    assert supervisor.automation_allowed is False
    assert source.snapshot() is initial


def test_successful_permission_revocation_is_published_and_remains_paused():
    path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE)
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    revoked=replace(initial,permission_granted=False,observed_at=1001.0,observed_monotonic=51.0)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clocks=iter(((1000.0,50.0),(1001.0,51.0)))
    current=[None]
    def wall_clock():
        current[0]=next(clocks)
        return current[0][0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=wall_clock,monotonic_clock=lambda:current[0][1])
    assert coordinator.refresh() is ProtectionState.ACTIVE
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    assert dispatcher.apply(revoked) is ProtectionState.PAUSED
    assert source.snapshot() is revoked
    assert supervisor.reason=="PERMISSION_DENIED"
    assert supervisor.automation_allowed is False


def test_fresh_permission_restoration_reactivates_after_revocation():
    path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE)
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    revoked=replace(initial,permission_granted=False,observed_at=1001.0,observed_monotonic=51.0)
    restored=replace(initial,observed_at=1002.0,observed_monotonic=52.0)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clocks=iter(((1000.0,50.0),(1001.0,51.0),(1002.0,52.0)))
    current=[None]
    def wall_clock():
        current[0]=next(clocks)
        return current[0][0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=wall_clock,monotonic_clock=lambda:current[0][1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    assert dispatcher.apply(revoked) is ProtectionState.PAUSED
    assert supervisor.reason=="PERMISSION_DENIED"
    assert dispatcher.apply(restored) is ProtectionState.ACTIVE
    assert source.snapshot() is restored
    assert supervisor.reason=="VALIDATED"
    assert supervisor.automation_allowed is True


def test_same_boundary_permission_restoration_cannot_reactivate():
    path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE)
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    revoked=replace(initial,permission_granted=False,observed_at=1001.0,observed_monotonic=51.0)
    replayed_restoration=replace(initial,observed_at=1002.0,observed_monotonic=51.0)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clocks=iter(((1000.0,50.0),(1001.0,51.0)))
    current=[None]
    def wall_clock():
        current[0]=next(clocks)
        return current[0][0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=wall_clock,monotonic_clock=lambda:current[0][1])
    # Failure handling must use the same synthetic clock domain as the evidence.
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:1002.0,monotonic_clock=lambda:52.0)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    assert dispatcher.apply(revoked) is ProtectionState.PAUSED
    assert source.snapshot() is revoked
    assert dispatcher.apply(replayed_restoration) is ProtectionState.PAUSED
    assert source.snapshot() is revoked
    assert supervisor.reason=="EVIDENCE_PUBLICATION_FAILURE"
    assert supervisor.automation_allowed is False
