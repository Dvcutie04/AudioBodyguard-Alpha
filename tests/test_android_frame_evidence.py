from tools.android_frame_evidence import compare_frames
import pytest


PROCESS = "** Graphics info for pid 1234 [com.aqss.bodyguard.prototype.liveinput] **\n"


@pytest.mark.parametrize("baseline_completion", [0, 1010000000])
@pytest.mark.parametrize("before_process,after_process,available", [
    (PROCESS, PROCESS.replace("1234", "5678"), True),
    (PROCESS, PROCESS.replace(".liveinput", ".other"), True),
    ("", PROCESS, False),
    (PROCESS, "", False),
    ("", "", False),
    (PROCESS + PROCESS.replace("1234", "5678"), PROCESS, False),
    (PROCESS, PROCESS + PROCESS.replace("1234", "5678"), False),
    (PROCESS.replace("1234", "0"), PROCESS, False),
    (PROCESS, PROCESS + PROCESS.replace("1234", "unreadable"), False),
], ids=["pid-change", "name-change", "missing-before", "missing-after", "missing-both",
        "ambiguous-before", "ambiguous-after", "invalid-pid", "malformed-added-header"])
def test_unmatched_or_unavailable_process_identity_cannot_attribute_frames(
        before_process, after_process, available, baseline_completion):
    columns = "Flags,IntendedVsync,FrameCompleted,\n"
    before = "Uptime: 2000 Realtime: 2000\n" + before_process + columns + f"0,1000000000,{baseline_completion},\n"
    after = "Uptime: 2100 Realtime: 2100\n" + after_process + columns + "0,1500000000,1510000000,\n"
    result = compare_frames(before, after)
    assert result["baseline_available"] is True
    assert result["clock_bound_available"] is True
    assert result["uptime_order_valid"] is True
    assert result["invalid_timing_count"] == 0
    assert result["timing_qualified"] is False
    assert result["process_identity_available"] is available
    assert result["process_identity_matches"] is False
    assert result["frame_count"] == 0
    assert result["durations_ms"] == []
    assert result["median_ms"] is None
    assert result["maximum_ms"] is None


@pytest.mark.parametrize("baseline_completion", [0, 1010000000])
def test_regressed_uptime_cannot_attribute_frames_to_the_same_transition(baseline_completion):
    columns = "Flags,IntendedVsync,FrameCompleted,\n"
    before = "Uptime: 2000 Realtime: 2000\n" + PROCESS + columns + f"0,1000000000,{baseline_completion},\n"
    # Both rows are locally plausible within the collector's diagnostic horizon,
    # but a smaller dump uptime makes their cross-snapshot ordering untrustworthy.
    after = "Uptime: 1000 Realtime: 1000\n" + PROCESS + columns + "0,1500000000,1510000000,\n"
    result = compare_frames(before, after)
    assert result["baseline_available"] is True
    assert result["clock_bound_available"] is True
    assert result["timing_qualified"] is False
    assert result["uptime_order_valid"] is False
    assert result["frame_count"] == 0
    assert result["durations_ms"] == []
    assert result["median_ms"] is None
    assert result["maximum_ms"] is None

def test_only_new_completed_frames_contribute_to_picture_transition():
    header = "Uptime: 1000 Realtime: 1000\n" + PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    before = header + "0,100000000,110000000,\n"
    after = header + "0,100000000,110000000,\n0,200000000,225000000,\n1,300000000,900000000,\n0,400000000,0,\n"
    result = compare_frames(before, after)
    assert result["frame_count"] == 1
    assert result["durations_ms"] == [25.0]
    assert result["median_ms"] == 25.0
    assert result["scope"] == "rendered frames; not touch-to-response or physical latency"


def test_inflight_baseline_frame_is_not_counted_as_new():
    header = "Uptime: 1000 Realtime: 1000\n" + PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    result = compare_frames(header + "0,100000000,0,\n", header + "0,100000000,160000000,\n0,200000000,210000000,\n")
    assert result["durations_ms"] == [10.0]


def test_duplicate_snapshots_and_unavailable_evidence_do_not_invent_samples():
    header = "Uptime: 1000 Realtime: 1000\n" + PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    before = header + "0,100000000,110000000,\n"
    after = header + "0,200000000,210000000,\n" + header + "0,200000000,210000000,\n"
    assert compare_frames(before, after)["frame_count"] == 1
    unavailable = compare_frames("no frame baseline", after)
    assert unavailable["baseline_available"] is False
    assert unavailable["frame_count"] == 0
    assert unavailable["median_ms"] is None


def test_implausible_completion_timestamp_makes_transition_unqualified():
    header = PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    before = "Uptime: 450000 Realtime: 450000\n" + header + "0,449000000000,449010000000,\n"
    after = "Uptime: 459141 Realtime: 459141\n" + header + "0,456634339846,7305508662576702820,\n"
    result = compare_frames(before, after)
    assert result["frame_count"] == 0
    assert result["invalid_timing_count"] == 1
    assert result["timing_qualified"] is False
    assert result["median_ms"] is None


def test_missing_clock_or_mixed_invalid_evidence_cannot_claim_a_latency_summary():
    header = PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    before = header + "0,100000000,110000000,\n"
    after = header + "0,200000000,225000000,\n"
    result = compare_frames(before, after)
    assert result["clock_bound_available"] is False
    assert result["median_ms"] is None
    assert result["timing_qualified"] is False
    before = "Uptime: 1000 Realtime: 1000\n" + before
    after = "Uptime: 1000 Realtime: 1000\n" + after + "0,300000000,7305508662576702820,\n"
    result = compare_frames(before, after)
    assert result["frame_count"] == 1
    assert result["invalid_timing_count"] == 1
    assert result["median_ms"] is None
    assert result["maximum_ms"] is None
