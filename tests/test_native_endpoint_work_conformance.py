"""Behavioral N1 simulation; no native or physical qualification."""
from copy import deepcopy
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
