"""Behavioral N1 simulation; no native or physical qualification."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from tests.native_endpoint_fake import UnqualifiedNativeEndpointFake
from tests.test_endpoint_native_boundary_contract import CONTRACT, _synthetic_conformance_eligible


def test_empty_application_queue_keeps_submitted_native_frame_unsettled():
    endpoint = UnqualifiedNativeEndpointFake()
    assert endpoint.accept("frame-8", generation=8)
    assert endpoint.publish("frame-8")
    assert endpoint.submit("frame-8")
    assert endpoint.app_queue_empty
    assert endpoint.close_generation(8)
    assert not endpoint.old_work_settled
    assert endpoint.apply("frame-8")
    assert not endpoint.old_work_settled
    assert endpoint.observe("frame-8")
    assert not endpoint.old_work_settled  # Observation cannot retire buffered work.
    assert endpoint.settle("frame-8", disposition="completed")
    assert endpoint.old_work_settled
    assert endpoint.applied_work == ("frame-8",)
    assert [event.kind for event in endpoint.trace] == [
        "accepted", "published", "submitted", "generation_closed",
        "simulated_applied", "simulated_observed", "native_settled",
    ]
    trace = deepcopy(json.loads(CONTRACT.read_text(encoding="utf-8"))["baseline"])
    trace["native"].update(endpoint.native_snapshot())
    assert trace["native"]["backend_qualified"] is False
    assert _synthetic_conformance_eligible(trace) is False
    assert endpoint.production_ready is False


def test_older_descendant_remains_registered_after_parent_settles():
    endpoint = UnqualifiedNativeEndpointFake()
    assert endpoint.accept("timer-7", generation=7)
    assert endpoint.register_descendant("child-7", parent_id="timer-7")
    assert endpoint.settle("timer-7", disposition="discarded")
    assert endpoint.accept("frame-8", generation=8)
    assert endpoint.settle("frame-8", disposition="discarded")
    assert endpoint.close_generation(8)
    assert endpoint.app_queue_empty
    assert not endpoint.old_work_settled
    snapshot = endpoint.native_snapshot()
    assert snapshot["closed_generations"] == [7, 8]
    assert snapshot["work"] == [
        {"id": "timer-7", "generation": 7, "settled": True},
        {"id": "child-7", "generation": 7, "settled": False},
        {"id": "frame-8", "generation": 8, "settled": True},
    ]
    assert endpoint.publish("child-7") is False
    assert endpoint.settle("child-7", disposition="discarded")
    assert endpoint.old_work_settled
    assert endpoint.applied_work == ()


def test_hold_blocks_late_publication_descendants_and_successor_admission():
    endpoint = UnqualifiedNativeEndpointFake()
    assert endpoint.accept("unpublished-8", generation=8)
    assert endpoint.accept("published-8", generation=8)
    assert endpoint.publish("published-8")
    assert endpoint.close_generation(8)
    before = endpoint.trace
    assert endpoint.publish("unpublished-8") is False
    assert endpoint.submit("published-8") is False
    assert endpoint.register_descendant("late-child", parent_id="unpublished-8") is False
    assert endpoint.accept("successor-9", generation=9) is False
    assert endpoint.close_generation(8) is False
    assert endpoint.trace == before
    assert endpoint.applied_work == ()
    assert not endpoint.old_work_settled


@pytest.mark.parametrize("disposition", ["unknown", "partial"])
def test_incomplete_settlement_keeps_native_work_pending(disposition):
    endpoint = UnqualifiedNativeEndpointFake()
    endpoint.accept("frame", generation=8)
    endpoint.publish("frame")
    endpoint.submit("frame")
    endpoint.close_generation(8)
    before = endpoint.trace
    assert endpoint.settle("frame", disposition=disposition) is False
    assert endpoint.trace == before
    assert not endpoint.old_work_settled
    assert endpoint.settle("frame", disposition="discarded")
    assert endpoint.old_work_settled
    assert endpoint.apply("frame") is False
    assert endpoint.observe("frame") is False
    assert endpoint.applied_work == ()


def test_distinct_effect_and_observation_events_reject_replay_and_false_discard():
    endpoint = UnqualifiedNativeEndpointFake()
    endpoint.accept("frame", generation=8)
    assert endpoint.apply("frame") is False
    assert endpoint.observe("frame") is False
    assert endpoint.settle("frame", disposition="completed") is False
    endpoint.publish("frame")
    endpoint.submit("frame")
    assert endpoint.apply("frame")
    assert endpoint.apply("frame") is False
    assert endpoint.observe("frame")
    assert endpoint.observe("frame") is False
    assert endpoint.settle("frame", disposition="discarded") is False
    assert endpoint.settle("frame", disposition="completed")
    assert endpoint.settle("frame", disposition="completed") is False
    with pytest.raises(ValueError, match="settlement conflict"):
        endpoint.settle("frame", disposition="discarded")
    assert endpoint.applied_work == ("frame",)
    assert endpoint.observed_work == ("frame",)
    assert [event.sequence for event in endpoint.trace] == list(range(1, 7))


def test_bounded_registry_preserves_work_and_accepts_inhibition_when_full():
    endpoint = UnqualifiedNativeEndpointFake(max_work_items=2)
    endpoint.accept("parent", generation=7)
    endpoint.register_descendant("child", parent_id="parent")
    before = endpoint.native_snapshot()
    with pytest.raises(BufferError, match="registry full"):
        endpoint.accept("overflow", generation=8)
    assert endpoint.native_snapshot() == before
    assert endpoint.close_generation(8)
    assert not endpoint.old_work_settled
    endpoint.settle("parent", disposition="discarded")
    assert not endpoint.old_work_settled
    endpoint.settle("child", disposition="discarded")
    assert endpoint.old_work_settled
    assert endpoint.production_ready is False


def test_conflicting_identity_and_invalid_generation_cannot_replace_work():
    endpoint = UnqualifiedNativeEndpointFake()
    endpoint.accept("work", generation=8)
    assert endpoint.accept("work", generation=8) is False
    before = endpoint.native_snapshot()
    with pytest.raises(ValueError, match="binding mismatch"):
        endpoint.accept("work", generation=7)
    with pytest.raises(ValueError, match="positive integer"):
        endpoint.accept("invalid", generation=True)
    assert endpoint.native_snapshot() == before
    endpoint.settle("work", disposition="discarded")
    assert endpoint.register_descendant("too-late", parent_id="work") is False


def _activated_frame(endpoint, work_id="pending"):
    assert endpoint.accept(work_id, generation=8)
    assert endpoint.publish(work_id)
    return endpoint.activate_candidate(
        work_id, request_id="handoff-a-to-b", controller_id="phone-b",
        fencing_token=9, activated_at=101, expires_at=130,
    )


def test_runtime_change_does_not_erase_submitted_native_work():
    endpoint = UnqualifiedNativeEndpointFake()
    submitted = _activated_frame(endpoint, "old-frame")
    assert endpoint.submit("old-frame", candidate=submitted, at=102)
    pending = _activated_frame(endpoint, "pending-frame")
    assert endpoint.restart_runtime("runtime-two")
    assert endpoint.app_queue_empty  # The app lost its queue, not the native work.
    before = endpoint.trace
    assert endpoint.submit("pending-frame", candidate=pending, at=103) is False
    assert endpoint.submit("pending-frame", at=103) is False
    assert endpoint.trace == before
    assert endpoint.close_generation(8)
    assert not endpoint.old_work_settled
    assert endpoint.apply("old-frame")  # Already submitted work can still take effect.
    assert not endpoint.old_work_settled
    assert endpoint.production_ready is False


def test_actual_route_switch_invalidates_activation_before_cached_notification():
    endpoint = UnqualifiedNativeEndpointFake()
    pending = _activated_frame(endpoint)
    assert endpoint.switch_actual_route("wireless", route_epoch=2)
    scope = endpoint.context_snapshot()
    assert (scope["cached_route_id"], scope["cached_route_epoch"]) == ("built-in", 1)
    assert (scope["actual_route_id"], scope["actual_route_epoch"]) == ("wireless", 2)
    before = endpoint.trace
    assert endpoint.submit("pending", candidate=pending, at=102) is False
    assert endpoint.trace == before
    assert endpoint.notify_route()
    assert endpoint.submit("pending", candidate=pending, at=103) is False
    assert endpoint.applied_work == ()
    assert endpoint.production_ready is False


def test_successor_change_invalidates_activation_at_final_submission():
    endpoint = UnqualifiedNativeEndpointFake()
    pending = _activated_frame(endpoint)
    assert endpoint.replace_successor(
        request_id="handoff-b-to-c", controller_id="phone-c", fencing_token=10,
    )
    before = endpoint.trace
    assert endpoint.submit("pending", candidate=pending, at=102) is False
    assert endpoint.trace == before
    assert endpoint.production_ready is False


def test_protection_revocation_cannot_revalidate_old_activation_on_restoration():
    endpoint = UnqualifiedNativeEndpointFake()
    pending = _activated_frame(endpoint)
    assert endpoint.set_protection_active(False)
    assert endpoint.submit("pending", candidate=pending, at=102) is False
    assert endpoint.set_protection_active(True)
    assert endpoint.submit("pending", candidate=pending, at=103) is False
    assert endpoint.production_ready is False


def test_submission_rechecks_expiry_and_accepts_only_the_current_synthetic_context():
    endpoint = UnqualifiedNativeEndpointFake()
    pending = _activated_frame(endpoint)
    assert endpoint.submit("pending", candidate=pending, at=130) is False
    assert endpoint.submit("pending", candidate=pending, at=100) is False
    assert endpoint.submit("pending", at=102) is False
    assert endpoint.submit("pending", candidate=replace(pending), at=102) is False
    assert endpoint.submit("pending", candidate=pending, at=102)
    assert endpoint.submit("pending", candidate=pending, at=102) is False
    assert endpoint.applied_work == ()  # Synthetic submission is not a physical effect.
    assert endpoint.production_ready is False


@pytest.mark.parametrize("change", ["route", "protection"])
def test_unbound_submission_cannot_bypass_changed_context(change):
    endpoint = UnqualifiedNativeEndpointFake()
    endpoint.accept("unbound", generation=8)
    endpoint.publish("unbound")
    if change == "route":
        endpoint.switch_actual_route("wireless", route_epoch=2)
    else:
        endpoint.set_protection_active(False)
    before = endpoint.trace
    assert endpoint.submit("unbound") is False
    assert endpoint.trace == before
    assert endpoint.production_ready is False


def test_new_candidate_after_route_notification_is_still_unqualified():
    endpoint = UnqualifiedNativeEndpointFake()
    endpoint.switch_actual_route("wireless", route_epoch=2)
    endpoint.notify_route()
    candidate = _activated_frame(endpoint)
    assert endpoint.submit("pending", candidate=candidate, at=102)
    assert endpoint.production_ready is False
    assert endpoint.native_snapshot()["route_enforced"] is False
