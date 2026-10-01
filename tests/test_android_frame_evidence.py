from tools.android_frame_evidence import compare_frames

def test_only_new_completed_frames_contribute_to_picture_transition():
    header = "Flags,IntendedVsync,FrameCompleted,\n"
    before = header + "0,100000000,110000000,\n"
    after = header + "0,100000000,110000000,\n0,200000000,225000000,\n1,300000000,900000000,\n0,400000000,0,\n"
    result = compare_frames(before, after)
    assert result["frame_count"] == 1
    assert result["durations_ms"] == [25.0]
    assert result["median_ms"] == 25.0
    assert result["scope"] == "rendered frames; not touch-to-response or physical latency"


def test_inflight_baseline_frame_is_not_counted_as_new():
    header = "Flags,IntendedVsync,FrameCompleted,\n"
    result = compare_frames(header + "0,100000000,0,\n", header + "0,100000000,160000000,\n0,200000000,210000000,\n")
    assert result["durations_ms"] == [10.0]


def test_duplicate_snapshots_and_unavailable_evidence_do_not_invent_samples():
    header = "Flags,IntendedVsync,FrameCompleted,\n"
    before = header + "0,100000000,110000000,\n"
    after = header + "0,200000000,210000000,\n" + header + "0,200000000,210000000,\n"
    assert compare_frames(before, after)["frame_count"] == 1
    unavailable = compare_frames("no frame baseline", after)
    assert unavailable["baseline_available"] is False
    assert unavailable["frame_count"] == 0
    assert unavailable["median_ms"] is None
