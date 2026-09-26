"""Read-only product views must never manufacture continuous physical coverage."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from src.control.device_fabric_bridge import BridgeResult
from src.control.session_evidence_view import (
    CapabilityFacts,
    CoverageEvent,
    ReadOnlySessionJournal,
    change_view,
    capability_view,
)
from src.control.protection_supervisor import ProtectionState
from src.control.media_control_verified_state import VerifiedMediaControlState
from src.device_fabric.contracts import (
    ActuationReceipt,
    ActuationStatus,
    DeviceState,
    PhysicalSnapshot,
    PhysicalVerificationRecord,
    VerificationStatus,
)


def sample(sequence=1, *, runtime_id="run-a", state=ProtectionState.ACTIVE,
           reason="PATH_ELIGIBLE", received=100.0, expires=103.0,
           user_paused=False, user_resumed=False):
    return CoverageEvent(
        session_id="sensitive-session-id", runtime_id=runtime_id,
        clock_domain_id="clock-a" if runtime_id == "run-a" else "clock-b",
        sequence=sequence, observed_monotonic=received,
        received_monotonic=received, expires_monotonic=expires,
        state=state, reason=reason, user_paused=user_paused,
        user_resumed=user_resumed,
    )


def test_missing_samples_and_suspension_never_extend_active_coverage():
    journal = ReadOnlySessionJournal("sensitive-session-id", max_events=4)
    assert journal.current(runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=100).state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    journal.append(sample())
    assert journal.current(runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=102).state is ProtectionState.ACTIVE
    stale = journal.current(runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=103.01)
    assert stale.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert stale.reason == "EVIDENCE_EXPIRED"
    assert journal.current(runtime_id="run-b", clock_domain_id="clock-b", now_monotonic=1).state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert journal.recap().active_duration_seconds is None
    assert journal.recap().coverage_percent is None


def test_new_runtime_restores_only_a_new_snapshot_and_preserves_history_gap():
    journal = ReadOnlySessionJournal("sensitive-session-id")
    journal.append(sample())
    journal.append(sample(3, runtime_id="run-b", received=1, expires=2))
    assert journal.recap().missing_sequences == 1
    assert journal.recap().runtime_discontinuities == 1
    assert journal.current(runtime_id="run-b", clock_domain_id="clock-b", now_monotonic=1.5).state is ProtectionState.ACTIVE
    assert journal.recap().coverage_percent is None
    assert journal.current(runtime_id="run-b", clock_domain_id="clock-b", now_monotonic=3).state is ProtectionState.UNKNOWN_PHYSICAL_STATE


def test_first_sample_with_a_skipped_sequence_reports_missing_history():
    journal = ReadOnlySessionJournal("sensitive-session-id")
    journal.append(sample(3))
    assert journal.recap().missing_sequences == 2
    assert journal.recap().coverage_percent is None


def test_user_pause_remains_visible_after_evidence_expires():
    journal = ReadOnlySessionJournal("sensitive-session-id")
    journal.append(sample(state=ProtectionState.PAUSED, reason="USER_PAUSED", user_paused=True))
    view = journal.current(runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=110)
    assert view.state is ProtectionState.PAUSED
    assert view.reason == "USER_PAUSED"
    assert "EVIDENCE_EXPIRED" in view.secondary_reasons


def test_new_callback_does_not_erase_user_pause_without_explicit_resume():
    journal = ReadOnlySessionJournal("sensitive-session-id")
    journal.append(sample(state=ProtectionState.PAUSED, reason="USER_PAUSED", user_paused=True))
    journal.append(sample(2, received=101, expires=104))
    view = journal.current(runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=102)
    assert view.state is ProtectionState.PAUSED
    assert view.reason == "USER_PAUSED"
    journal.append(sample(3, received=102, expires=105,
                          state=ProtectionState.UNKNOWN_PHYSICAL_STATE,
                          reason="POST_CONDITION_UNOBSERVED"))
    view = journal.current(runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=103)
    assert view.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert "USER_PAUSED" in view.secondary_reasons
    journal.append(sample(4, received=104, expires=106, user_resumed=True))
    assert journal.current(runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=104).state is ProtectionState.ACTIVE


@pytest.mark.parametrize("mutation", [
    {"sequence": True}, {"received_monotonic": float("nan")},
    {"observed_monotonic": 101.0}, {"expires_monotonic": 99.0},
    {"state": "ACTIVE"}, {"reason": "a media title / secret"},
    {"user_paused": True},
])
def test_malformed_or_conflicting_event_cannot_enter_timeline(mutation):
    with pytest.raises(ValueError):
        sample(**mutation) if "sequence" in mutation else replace(sample(), **mutation)


def test_replay_clock_switch_and_sequence_rollback_reject_without_mutating():
    journal = ReadOnlySessionJournal("sensitive-session-id")
    journal.append(sample())
    for bad in (sample(), sample(1, received=101),
                replace(sample(2), clock_domain_id="other-clock"),
                sample(2, received=99)):
        with pytest.raises(ValueError):
            journal.append(bad)
    assert len(journal.events) == 1
    assert journal.current(runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=101).state is ProtectionState.ACTIVE


def test_bounded_history_and_export_redaction_cannot_change_authority():
    journal = ReadOnlySessionJournal("sensitive-session-id", max_events=2)
    journal.append(sample())
    journal.append(sample(2, received=101, expires=104, reason="PERMISSION_DENIED", state=ProtectionState.PAUSED))
    journal.append(sample(3, received=102, expires=105, state=ProtectionState.UNKNOWN_PHYSICAL_STATE))
    assert len(journal.events) == 2
    assert journal.recap().evicted_events == 1
    bundle = journal.preview_redacted_export()
    assert "sensitive-session-id" not in bundle
    assert "run-a" not in bundle
    assert "clock-a" not in bundle
    assert "coverage_percent" not in bundle
    assert "authority" not in bundle.lower()
    assert "derived, unverified" in bundle
    assert journal.events[0].reason == "PERMISSION_DENIED"


def test_export_redacts_unrecognized_reason_even_if_it_looks_like_a_code():
    journal = ReadOnlySessionJournal("sensitive-session-id")
    journal.append(sample(reason="PRIVATE_MOVIE_TITLE"))
    assert journal.events[0].reason == "OTHER_REASON"
    assert "PRIVATE_MOVIE_TITLE" not in journal.preview_redacted_export()
    assert '"reason":"OTHER_REASON"' in journal.preview_redacted_export()


def test_read_only_capability_keeps_permission_qualification_and_route_distinct():
    base = CapabilityFacts(hardware=True, qualification=True, permission=True,
                           route=True, runtime=True, evidence=True,
                           observed_monotonic=99, expires_monotonic=105, clock_domain_id="clock-a")
    ready = capability_view(base, now_monotonic=100, clock_domain_id="clock-a")
    assert ready.label == "AVAILABLE_FOR_REVIEW"
    assert ready.can_actuate is False
    for name, reason in (("hardware", "UNSUPPORTED"), ("qualification", "NOT_QUALIFIED"),
                         ("permission", "PERMISSION_DENIED"), ("route", "ROUTE_UNAVAILABLE")):
        blocked = capability_view(replace(base, **{name: False}), now_monotonic=100, clock_domain_id="clock-a")
        assert blocked.label == "BLOCKED" and reason in blocked.reasons
    assert capability_view(replace(base, hardware=None), now_monotonic=100, clock_domain_id="clock-a").label == "UNKNOWN"
    assert capability_view(base, now_monotonic=106, clock_domain_id="clock-a").label == "UNKNOWN"
    assert capability_view(base, now_monotonic=98, clock_domain_id="clock-a").label == "UNKNOWN"
    assert capability_view(base, now_monotonic=1, clock_domain_id="new-boot").label == "UNKNOWN"


def test_bridge_receipt_is_not_a_verified_change_and_failed_undo_is_uncertain():
    receipt = ActuationReceipt(receipt_id="r", intent_id="i", device_id="d",
                               transaction_id="t", capability_digest="c", status=ActuationStatus.EXECUTED)
    assert change_view(BridgeResult("EXECUTED", "i", receipt=receipt)).label == "RESULT_UNCERTAIN"
    assert change_view(BridgeResult("FAILED", "i", receipt=receipt)).label == "RESULT_UNCERTAIN"
    assert change_view(BridgeResult("REJECTED", "i", rejection="NOT_SUPPORTED")).label == "REQUEST_REJECTED"
    assert change_view(BridgeResult("REJECTED", "i", receipt=receipt)).label == "RESULT_UNCERTAIN"


def test_only_matching_verified_media_lineage_gets_scoped_change_wording():
    state = DeviceState(volume=42, custom_state={"captions_enabled": True})
    snapshot = PhysicalSnapshot(device_id="d", state=state, epoch=7, observed_at=100.0,
                                evidence_digest="observed")
    verification = PhysicalVerificationRecord(
        intent_id="i", device_id="d", receipt_id="r",
        expected_state_digest=state.state_digest, observed_state_digest=state.state_digest,
        authorization_digest="a", transaction_id="t", capability_digest="c",
        observed_state_evidence_digest="observed", world_state_epoch=6,
        observed_state_epoch=7, verification_status=VerificationStatus.VERIFIED,
    )
    verified = VerifiedMediaControlState.from_physical_verification(snapshot, verification)
    receipt = ActuationReceipt(receipt_id="r", intent_id="i", device_id="d",
                               transaction_id="t", capability_digest="c", status=ActuationStatus.EXECUTED)
    result = BridgeResult("EXECUTED", "i", receipt=receipt, transaction_id="t",
                          authorization_digest="a", capability_digest="c",
                          verification=verification, verified_state=verified)
    assert change_view(result).label == "VERIFIED_ON_DECLARED_PATH"
    assert change_view(replace(result, transaction_id="other")).label == "RESULT_UNCERTAIN"
    assert change_view(replace(result, status="FAILED")).label == "RESULT_UNCERTAIN"
    assert change_view(replace(result, verification=replace(verification, verification_status=VerificationStatus.PENDING))).label == "RESULT_UNCERTAIN"
    assert change_view(replace(result, receipt=replace(receipt, status=ActuationStatus.REJECTED))).label == "RESULT_UNCERTAIN"


def test_shared_read_only_ios_android_vectors_match_python_reference():
    fixtures = json.loads((Path(__file__).resolve().parents[1] / "contracts/session_evidence_view_v1.json").read_text(encoding="utf-8"))
    assert fixtures["platforms"] == ["ios", "android"]
    assert fixtures["purpose"] == "read_only_reference_projection_not_physical_qualification"
    assert len(fixtures["coverage_cases"]) >= 10
    assert len(fixtures["capability_cases"]) >= 9
    for case in fixtures["coverage_cases"]:
        journal = ReadOnlySessionJournal("sensitive-session-id")
        if case["sample"] is not None:
            entry = case["sample"]
            journal.append(CoverageEvent(
                session_id="sensitive-session-id", runtime_id=entry["runtime"],
                clock_domain_id=entry["clock"], sequence=1,
                observed_monotonic=entry["received"], received_monotonic=entry["received"],
                expires_monotonic=entry["expires"], state=ProtectionState(entry["state"]),
                reason=entry["reason"], user_paused=entry["user_paused"],
            ))
        result = journal.current(runtime_id=case["current_runtime"], clock_domain_id=case["current_clock"], now_monotonic=case["now"])
        assert (result.state.value, result.reason) == (case["expected_state"], case["expected_reason"]), case["id"]
    for case in fixtures["capability_cases"]:
        entry = dict(case["facts"])
        facts = CapabilityFacts(
            **{name: entry[name] for name in ("hardware", "qualification", "permission", "route", "runtime", "evidence")},
            observed_monotonic=entry["observed"], expires_monotonic=entry["expires"], clock_domain_id=entry["clock"],
        )
        assert capability_view(facts, now_monotonic=case["now"], clock_domain_id=case["current_clock"]).label == case["expected"], case["id"]
