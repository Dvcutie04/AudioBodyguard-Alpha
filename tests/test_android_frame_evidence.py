from tools.android_frame_evidence import compare_frames
import pytest


PROCESS = "** Graphics info for pid 1234 [com.aqss.bodyguard.prototype.liveinput] **\n"


def _frame_table(columns, values):
    return ",".join(columns) + ",\n" + ",".join(map(str, values)) + ",\n"


@pytest.mark.parametrize("side", ["before", "after"])
@pytest.mark.parametrize("bad_first", [False, True], ids=["bad-last", "bad-first"])
@pytest.mark.parametrize("kind,column", [
    (kind, column) for kind in ("duplicate", "missing")
    for column in ("Flags", "IntendedVsync", "FrameCompleted")
])
def test_ambiguous_or_incomplete_frame_schema_withholds_attribution(side, bad_first, kind, column):
    columns = ["Flags", "IntendedVsync", "FrameCompleted"]
    start = 1100000000 if side == "before" else 1600000000
    values = [0, start, start + 10000000]
    index = columns.index(column)
    if kind == "duplicate":
        columns.insert(index, column)
        values.insert(index, {"Flags": 1, "IntendedVsync": start - 100000000,
                              "FrameCompleted": start + 100000000}[column])
    else:
        columns.pop(index)
        values.pop(index)
    bad = _frame_table(columns, values)
    native = ["Flags", "IntendedVsync", "FrameCompleted"]
    before = _frame_table(native, [0, 1000000000, 1010000000])
    after = _frame_table(native, [0, 1500000000, 1510000000])
    if side == "before":
        before = bad + before if bad_first else before + bad
    else:
        after = bad + after if bad_first else after + bad
    result = compare_frames("Uptime: 2000 Realtime: 2000\n" + PROCESS + before,
                            "Uptime: 2200 Realtime: 2200\n" + PROCESS + after)
    # Fail first on the old semantic defect, before checking the new evidence field.
    assert result["timing_qualified"] is False
    assert result["frame_schema_available"] is False
    assert result["baseline_available"] is True  # A valid observed start is still known.
    assert result["clock_bound_available"] is True
    assert result["uptime_order_valid"] is True
    assert result["process_identity_matches"] is True
    assert result["frame_count"] == 0
    assert result["durations_ms"] == []
    assert result["median_ms"] is None
    assert result["maximum_ms"] is None


@pytest.mark.parametrize("columns,values,repeat", [
    (["Flags", "IntendedVsync", "FrameCompleted"], [0, 1500000000, 1510000000], False),
    (["FrameCompleted", "Extra", "Flags", "IntendedVsync"], [1510000000, 9, 0, 1500000000], False),
    (["Flags", "Extra", "Extra", "IntendedVsync", "FrameCompleted", ""],
     [0, 8, 9, 1500000000, 1510000000, ""], False),
    (["FrameCompleted", "Flags", "IntendedVsync"], [1510000000, 0, 1500000000], True),
], ids=["native", "reordered", "unrelated-duplicates", "repeated-reordered"])
def test_unique_required_frame_columns_preserve_existing_summary(columns, values, repeat):
    prefix = "Uptime: 2200 Realtime: 2200\n" + PROCESS
    before = prefix + _frame_table(["Flags", "IntendedVsync", "FrameCompleted"],
                                   [0, 1000000000, 1010000000])
    after = prefix + _frame_table(columns, values)
    if repeat:
        after += _frame_table(["Flags", "IntendedVsync", "FrameCompleted"],
                              [0, 1500000000, 1510000000])
    result = compare_frames(before, after)
    assert result["timing_qualified"] is True
    assert result["frame_count"] == 1
    assert result["durations_ms"] == [10.0]
    assert result["median_ms"] == 10.0
    assert result["maximum_ms"] == 10.0


@pytest.mark.parametrize("side", ["before", "after"])
@pytest.mark.parametrize("bad_clock", [
    "Uptime: 2100.5 Realtime: 2100\n",
    "Uptime: 2100ms Realtime: 2100\n",
    "Uptime: 2100e3 Realtime: 2100\n",
    "Uptime:\n2100 Realtime: 2100\n",
    "Uptime: 2100 Realtime: 2100\nUptime: 1900 Realtime: 1900\n",
    "Uptime: 1900 Realtime: 1900\nUptime: 2100 Realtime: 2100\n",
    "Uptime: 2100 Realtime: 2100\nUptime: unreadable Realtime: 2100\n",
    "Uptime: unreadable Realtime: 2100\nUptime: 2100 Realtime: 2100\n",
], ids=["fraction", "unit-suffix", "exponent", "split-line", "conflicting-descending",
        "conflicting-ascending", "malformed-last", "malformed-first"])
def test_malformed_or_ambiguous_uptime_cannot_qualify_timing(side, bad_clock):
    columns = PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    before_clock, after_clock = "Uptime: 2000 Realtime: 2000\n", "Uptime: 2200 Realtime: 2200\n"
    if side == "before":
        before_clock = bad_clock
    else:
        after_clock = bad_clock
    result = compare_frames(before_clock + columns + "0,1000000000,1010000000,\n",
                            after_clock + columns + "0,1500000000,1510000000,\n")
    assert result["baseline_available"] is True
    assert result["process_identity_matches"] is True
    assert result["clock_bound_available"] is False
    assert result["uptime_order_valid"] is False
    assert result["timing_qualified"] is False
    # Unknown clocks retain the existing valid-subset diagnostic treatment.
    assert result["frame_count"] == 1
    assert result["durations_ms"] == [10.0]
    assert result["median_ms"] is None
    assert result["maximum_ms"] is None


@pytest.mark.parametrize("clock", [
    "Uptime: 2100 Realtime: 2100\n",
    "Uptime: 2100\n",
    "Uptime:\t2100\tRealtime: 2100\n",
    "Uptime: 2100 Realtime: 2100\nUptime: 2100 Realtime: 2100\n",
], ids=["native", "uptime-only", "horizontal-whitespace", "identical-duplicate"])
def test_unambiguous_integer_uptime_retains_qualified_summary(clock):
    columns = PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    result = compare_frames(clock + columns + "0,1000000000,1010000000,\n",
                            clock + columns + "0,1500000000,1510000000,\n")
    assert result["clock_bound_available"] is True
    assert result["uptime_order_valid"] is True
    assert result["timing_qualified"] is True
    assert result["durations_ms"] == [10.0]
    assert result["median_ms"] == 10.0
    assert result["maximum_ms"] == 10.0


def _unreadable_completion_row(start, completion, flag=0):
    return f"{flag},{start}" + (f",{completion},\n" if completion is not None else "\n")


@pytest.mark.parametrize("baseline_completion", [0, 1010000000], ids=["inflight", "completed"])
@pytest.mark.parametrize("completion", ["unreadable", "1.5", "", None],
                         ids=["text", "fraction", "empty", "missing"])
def test_unreadable_new_completion_withholds_summary_but_retains_valid_subset(
        baseline_completion, completion):
    columns = PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    before = "Uptime: 2000 Realtime: 2000\n" + columns + f"0,1000000000,{baseline_completion},\n"
    bad = _unreadable_completion_row(1600000000, completion)
    after = "Uptime: 2100 Realtime: 2100\n" + columns + "0,1500000000,1510000000,\n" + bad + bad
    result = compare_frames(before, after)
    assert result["baseline_available"] is True
    assert result["clock_bound_available"] is True
    assert result["uptime_order_valid"] is True
    assert result["process_identity_matches"] is True
    assert result["invalid_timing_count"] == 1
    assert result["timing_qualified"] is False
    assert result["frame_count"] == 1
    assert result["durations_ms"] == [10.0]
    assert result["median_ms"] is None
    assert result["maximum_ms"] is None


@pytest.mark.parametrize("earlier_completed", [False, True], ids=["only-baseline", "later-baseline"])
@pytest.mark.parametrize("completion", ["unreadable", "1.5", "", None],
                         ids=["text", "fraction", "empty", "missing"])
def test_unreadable_baseline_completion_does_not_erase_observed_start(earlier_completed, completion):
    columns = PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    before = "Uptime: 2000 Realtime: 2000\n" + columns
    if earlier_completed:
        before += "0,500000000,510000000,\n"
    before += _unreadable_completion_row(1000000000, completion)
    after = "Uptime: 2100 Realtime: 2100\n" + columns + "0,1000000000,1100000000,\n0,1500000000,1510000000,\n"
    result = compare_frames(before, after)
    assert result["baseline_available"] is True
    assert result["invalid_timing_count"] == 0
    assert result["frame_count"] == 1
    assert result["durations_ms"] == [10.0]
    assert result["timing_qualified"] is True
    assert result["median_ms"] == 10.0
    assert result["maximum_ms"] == 10.0


@pytest.mark.parametrize("flag,start", [(1, 1600000000), (0, 1000000000)], ids=["flagged", "not-new"])
def test_unreadable_completion_outside_new_eligible_frames_does_not_poison_summary(flag, start):
    columns = PROCESS + "Flags,IntendedVsync,FrameCompleted,\n"
    before = "Uptime: 2000 Realtime: 2000\n" + columns + "0,1000000000,1010000000,\n"
    after = "Uptime: 2100 Realtime: 2100\n" + columns + "0,1500000000,1510000000,\n" + _unreadable_completion_row(start, "unreadable", flag)
    result = compare_frames(before, after)
    assert result["invalid_timing_count"] == 0
    assert result["durations_ms"] == [10.0]
    assert result["timing_qualified"] is True
    assert result["median_ms"] == 10.0
    assert result["maximum_ms"] == 10.0


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
