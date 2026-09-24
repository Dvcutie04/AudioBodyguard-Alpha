import pytest

from src.control.protection_evidence import ProtectionEvidence,ProtectionEvidenceCoordinator,ProtectionRuntimeMode
from src.control.protection_evidence_dispatcher import ProtectionEvidenceEventDispatcher
from src.control.protection_evidence_source import ProtectionEvidenceSource
from src.control.protection_path_assessment import ProtectionPathAssessment,ProtectionPathReason
from src.control.protection_platform_events import ProtectionPlatformEvent,ProtectionPlatformEventAdapter
from src.control.protection_supervisor import ProtectionState,ProtectionSupervisor


def test_apple_audio_interruption_began_atomically_suspends_protection():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1001.0,51.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_BEGAN,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    snapshot=source.snapshot()
    assert snapshot.runtime_mode is ProtectionRuntimeMode.SUSPENDED
    assert snapshot.observed_at==1001.0
    assert snapshot.observed_monotonic==51.0
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


@pytest.mark.parametrize("event_name",("ANDROID_AUDIO_FOCUS_LOSS","ANDROID_AUDIO_FOCUS_LOSS_TRANSIENT"))
def test_android_audio_focus_loss_atomically_suspends_protection(event_name):
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1001.0,51.0]
    event=getattr(ProtectionPlatformEvent,event_name)
    assert adapter.apply(event,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    snapshot=source.snapshot()
    assert snapshot.runtime_mode is ProtectionRuntimeMode.SUSPENDED
    assert snapshot.observed_monotonic==51.0
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


def test_apple_audio_route_change_requires_path_revalidation():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1001.0,51.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_ROUTE_CHANGED,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    snapshot=source.snapshot()
    assert snapshot.runtime_mode is ProtectionRuntimeMode.SUSPENDED
    assert snapshot.observed_at==1001.0
    assert snapshot.observed_monotonic==51.0
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


def test_apple_audio_interruption_ended_does_not_reactivate_protection():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1001.0,51.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_BEGAN,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    clock[:]=[1002.0,52.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_ENDED,observed_at=1002.0,observed_monotonic=52.0) is ProtectionState.PAUSED
    snapshot=source.snapshot()
    assert snapshot.runtime_mode is ProtectionRuntimeMode.SUSPENDED
    assert snapshot.observed_at==1002.0
    assert snapshot.observed_monotonic==52.0
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


def test_android_audio_focus_gain_does_not_reactivate_protection():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1001.0,51.0]
    assert adapter.apply(ProtectionPlatformEvent.ANDROID_AUDIO_FOCUS_LOSS_TRANSIENT,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    clock[:]=[1002.0,52.0]
    assert adapter.apply(ProtectionPlatformEvent.ANDROID_AUDIO_FOCUS_GAIN,observed_at=1002.0,observed_monotonic=52.0) is ProtectionState.PAUSED
    snapshot=source.snapshot()
    assert snapshot.runtime_mode is ProtectionRuntimeMode.SUSPENDED
    assert snapshot.observed_at==1002.0
    assert snapshot.observed_monotonic==52.0
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


def test_string_platform_event_fails_closed_without_publication():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    before=source.snapshot()
    clock[:]=[1001.0,51.0]
    assert adapter.apply("APPLE_AUDIO_INTERRUPTION_BEGAN",observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    assert source.snapshot() is before
    assert supervisor.reason=="EVIDENCE_EVENT_INVALID"
    assert supervisor.automation_allowed is False


@pytest.mark.parametrize(("observed_at","observed_monotonic"),((True,51.0),(float("nan"),51.0),(1001.0,float("inf"))))
def test_invalid_platform_event_timestamps_fail_closed_without_publication(observed_at,observed_monotonic):
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    before=source.snapshot()
    clock[:]=[1001.0,51.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_BEGAN,observed_at=observed_at,observed_monotonic=observed_monotonic) is ProtectionState.PAUSED
    assert source.snapshot() is before
    assert supervisor.reason=="EVIDENCE_EVENT_INVALID"
    assert supervisor.automation_allowed is False


@pytest.mark.parametrize("bad_event",(None,object(),7))
def test_arbitrary_platform_event_objects_fail_closed_without_publication(bad_event):
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    before=source.snapshot()
    clock[:]=[1001.0,51.0]
    assert adapter.apply(bad_event,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    assert source.snapshot() is before
    assert supervisor.reason=="EVIDENCE_EVENT_INVALID"
    assert supervisor.automation_allowed is False


def test_older_platform_event_cannot_overwrite_newer_evidence():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1002.0,52.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_BEGAN,observed_at=1002.0,observed_monotonic=52.0) is ProtectionState.PAUSED
    newer=source.snapshot()
    clock[:]=[1003.0,53.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_ROUTE_CHANGED,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    assert source.snapshot() is newer
    assert supervisor.reason=="EVIDENCE_PUBLICATION_FAILURE"
    assert supervisor.automation_allowed is False


def test_conflicting_same_boundary_platform_event_cannot_overwrite_evidence():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1002.0,52.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_BEGAN,observed_at=1002.0,observed_monotonic=52.0) is ProtectionState.PAUSED
    established=source.snapshot()
    clock[:]=[1003.0,53.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_ROUTE_CHANGED,observed_at=1003.0,observed_monotonic=52.0) is ProtectionState.PAUSED
    assert source.snapshot() is established
    assert supervisor.reason=="EVIDENCE_PUBLICATION_FAILURE"
    assert supervisor.automation_allowed is False


def test_identical_platform_event_replay_is_idempotent():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1001.0,51.0]
    assert adapter.apply(ProtectionPlatformEvent.ANDROID_AUDIO_FOCUS_LOSS,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    established=source.snapshot()
    assert adapter.apply(ProtectionPlatformEvent.ANDROID_AUDIO_FOCUS_LOSS,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    assert source.snapshot() is established
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


def test_fresh_revalidated_evidence_is_required_to_restore_active():
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1000.0,observed_monotonic=50.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    clock=[1000.0,50.0]
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    adapter=ProtectionPlatformEventAdapter(source,dispatcher)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[1001.0,51.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_BEGAN,observed_at=1001.0,observed_monotonic=51.0) is ProtectionState.PAUSED
    clock[:]=[1002.0,52.0]
    assert adapter.apply(ProtectionPlatformEvent.APPLE_AUDIO_INTERRUPTION_ENDED,observed_at=1002.0,observed_monotonic=52.0) is ProtectionState.PAUSED
    assert supervisor.automation_allowed is False
    fresh=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=1003.0,observed_monotonic=53.0,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    clock[:]=[1003.0,53.0]
    assert source.publish(fresh) is fresh
    assert coordinator.refresh() is ProtectionState.ACTIVE
    assert source.snapshot() is fresh
    assert supervisor.automation_allowed is True
