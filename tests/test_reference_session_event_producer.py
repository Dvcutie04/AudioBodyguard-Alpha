"""A reference supervisor can report losses, but cannot certify physical coverage."""

import pytest

from src.control.protection_supervisor import ProtectionState, ProtectionSupervisor
from src.control.session_evidence_view import ReadOnlySessionJournal
from src.control.session_event_producer import ReferenceSessionEventProducer


def _active_supervisor():
    supervisor = ProtectionSupervisor(max_evidence_age=2.0)
    supervisor.validate(permission_granted=True, runtime_eligible=True,
                        sensor_available=True, connected=True, authority_valid=True,
                        protection_path_eligible=True, observed_at=100.0, now=100.0,
                        observed_monotonic=100.0, monotonic_now=100.0)
    assert supervisor.state is ProtectionState.ACTIVE
    return supervisor


def _producer(supervisor, journal, *, runtime="runtime-a", clock="clock-a"):
    return ReferenceSessionEventProducer(supervisor, journal, runtime_id=runtime,
                                         clock_domain_id=clock)


def test_software_active_never_becomes_a_positive_physical_coverage_event():
    supervisor = _active_supervisor()
    journal = ReadOnlySessionJournal("private-session")
    producer = _producer(supervisor, journal)
    ticket = producer.capture(monotonic_now=100.0)
    supervisor.max_evidence_age = 20.0
    event = producer.publish(ticket, received_monotonic=100.5)
    assert (event.sequence, event.observed_monotonic, event.received_monotonic,
            event.expires_monotonic) == (1, 100.0, 100.5, 102.0)
    assert (event.state, event.reason) == (ProtectionState.UNKNOWN_PHYSICAL_STATE,
                                           "REFERENCE_ONLY")
    assert journal.current(runtime_id="runtime-a", clock_domain_id="clock-a",
                           now_monotonic=100.5).state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert journal.recap().coverage_percent is None
    assert journal.recap().active_duration_seconds is None


def test_negative_snapshot_is_reported_but_later_software_recovery_is_not_verified():
    supervisor = _active_supervisor()
    journal = ReadOnlySessionJournal("private-session")
    producer = _producer(supervisor, journal)
    supervisor.interrupt("PERMISSION_DENIED", now=101.0, monotonic_now=101.0)
    producer.publish(producer.capture(monotonic_now=101.0), received_monotonic=101.1)
    assert journal.current(runtime_id="runtime-a", clock_domain_id="clock-a",
                           now_monotonic=101.1).state is ProtectionState.PAUSED
    supervisor.validate(permission_granted=True, runtime_eligible=True,
                        sensor_available=True, connected=True, authority_valid=True,
                        protection_path_eligible=True, observed_at=102.0, now=102.0,
                        observed_monotonic=102.0, monotonic_now=102.0)
    assert supervisor.state is ProtectionState.ACTIVE
    resumed = producer.publish(producer.capture(monotonic_now=102.0),
                               received_monotonic=102.1)
    assert (resumed.state, resumed.reason) == (ProtectionState.UNKNOWN_PHYSICAL_STATE,
                                               "REFERENCE_ONLY")
    assert resumed.user_resumed is False


def test_failed_publication_and_overwritten_capture_leave_visible_sequence_gap():
    supervisor = _active_supervisor()
    journal = ReadOnlySessionJournal("private-session")
    producer = _producer(supervisor, journal)
    first = producer.capture(monotonic_now=100.0)
    second = producer.capture(monotonic_now=100.1)
    with pytest.raises(ValueError, match="superseded"):
        producer.publish(first, received_monotonic=100.2)
    original_append = journal.append
    def fail_once(event):
        journal.append = original_append
        raise OSError("storage unavailable")
    journal.append = fail_once
    with pytest.raises(OSError, match="storage unavailable"):
        producer.publish(second, received_monotonic=100.2)
    third = producer.capture(monotonic_now=100.3)
    event = producer.publish(third, received_monotonic=100.4)
    assert event.sequence == 3
    assert journal.recap().missing_sequences == 2
    with pytest.raises(ValueError, match="superseded"):
        producer.publish(third, received_monotonic=100.4)


def test_delayed_status_change_clock_rollback_and_runtime_switch_fail_closed():
    supervisor = _active_supervisor()
    journal = ReadOnlySessionJournal("private-session")
    producer = _producer(supervisor, journal)
    captured = producer.capture(monotonic_now=100.0)
    supervisor.interrupt("PERMISSION_DENIED", now=100.1, monotonic_now=100.1)
    stale = producer.publish(captured, received_monotonic=100.2)
    assert (stale.state, stale.reason) == (ProtectionState.UNKNOWN_PHYSICAL_STATE,
                                           "REFERENCE_ONLY")
    with pytest.raises(ValueError, match="rolled back"):
        producer.capture(monotonic_now=99.0)
    newer = _producer(ProtectionSupervisor(max_evidence_age=2.0), journal,
                      runtime="runtime-b", clock="clock-b")
    event = newer.publish(newer.capture(monotonic_now=1.0),
                          received_monotonic=1.1)
    assert event.sequence == 2
    assert journal.recap().runtime_discontinuities == 1
    assert journal.current(runtime_id="runtime-a", clock_domain_id="clock-a",
                           now_monotonic=100.3).state is ProtectionState.UNKNOWN_PHYSICAL_STATE


def test_unrecognized_reason_is_removed_before_retention_and_old_sample_expires():
    supervisor = _active_supervisor()
    journal = ReadOnlySessionJournal("private-session")
    producer = _producer(supervisor, journal)
    supervisor.interrupt("PRIVATE_MOVIE_TITLE", now=101.0, monotonic_now=101.0)
    event = producer.publish(producer.capture(monotonic_now=101.0),
                             received_monotonic=101.1)
    assert (event.state, event.reason) == (ProtectionState.PAUSED, "OTHER_REASON")
    assert "PRIVATE_MOVIE_TITLE" not in journal.preview_redacted_export()
    with pytest.raises(ValueError, match="rolled back"):
        producer.capture(monotonic_now=101.05)
    late = producer.publish(producer.capture(monotonic_now=102.0),
                            received_monotonic=104.01)
    assert late.expires_monotonic == 104.0
    assert journal.current(runtime_id="runtime-a", clock_domain_id="clock-a",
                           now_monotonic=104.01).state is ProtectionState.UNKNOWN_PHYSICAL_STATE


def test_append_then_raise_does_not_replay_an_already_recorded_sample():
    supervisor = _active_supervisor()
    journal = ReadOnlySessionJournal("private-session")
    producer = _producer(supervisor, journal)
    first = producer.capture(monotonic_now=100.0)
    original_append = journal.append
    def fail_after_append(event):
        original_append(event)
        journal.append = original_append
        raise OSError("uncertain write result")
    journal.append = fail_after_append
    with pytest.raises(OSError, match="uncertain write result"):
        producer.publish(first, received_monotonic=100.1)
    with pytest.raises(ValueError, match="replayed"):
        producer.publish(first, received_monotonic=100.1)
    producer.publish(producer.capture(monotonic_now=100.2),
                     received_monotonic=100.3)
    assert [item.sequence for item in journal.events] == [1, 2]
    assert journal.recap().missing_sequences == 0
