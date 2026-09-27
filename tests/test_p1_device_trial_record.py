from copy import deepcopy

from tools.p1_device_trial_record import assess, REQUIRED_CASES


def _reported_trial():
    return {
        "schema_version": 1,
        "revision": "a" * 40,
        "platform": "ios",
        "device_model": "Test iPhone",
        "os_build": "Test build",
        "installation": "xcode_signed_device",
        "cases": [
            {
                "id": case,
                "performed": True,
                "coverage": "UNKNOWN_PHYSICAL_STATE",
                "simulation_label_visible": True,
                "no_output_observation_visible": True,
                "hint_source": "app_session",
                "callback_observed": False if case in ("foreground_attach", "foreground_detach") else None,
                "screen_reader_checked": True if case == "accessible_large_text" else None,
                "large_text_checked": True if case == "accessible_large_text" else None,
                "independent_trace_ref": f"redacted/{case}.txt",
                "prior_visit_hint_reused": False if case == "background_resume" else None,
            }
            for case in REQUIRED_CASES
        ],
    }


def test_structurally_complete_manual_record_does_not_certify_device():
    status, problems = assess(_reported_trial())
    assert status == "STRUCTURE_COMPLETE_PHYSICAL_UNVERIFIED"
    assert problems == []


def test_active_claim_fails_even_if_other_cases_are_missing():
    record = _reported_trial()
    record["cases"] = record["cases"][:1]
    record["cases"][0]["coverage"] = "ACTIVE"
    status, problems = assess(record)
    assert status == "UNSAFE_REPORTED_UI"
    assert any("ACTIVE" in problem for problem in problems)


def test_missing_case_and_missing_independent_trace_are_incomplete():
    record = _reported_trial()
    record["cases"].pop()
    record["cases"][0]["independent_trace_ref"] = None
    status, problems = assess(record)
    assert status == "INCOMPLETE_RECORD"
    assert any("missing" in problem for problem in problems)


def test_stale_hint_or_cross_platform_source_is_unsafe():
    record = _reported_trial()
    case = next(row for row in record["cases"] if row["id"] == "background_resume")
    case["prior_visit_hint_reused"] = True
    record["cases"][0]["hint_source"] = "connected_device_inventory"
    status, problems = assess(record)
    assert status == "UNSAFE_REPORTED_UI"
    assert any("previous visit" in problem for problem in problems)
    assert any("source" in problem for problem in problems)


def test_template_and_mismatched_revision_cannot_pass():
    record = _reported_trial()
    record["revision"] = None
    record["cases"][0]["performed"] = False
    assert assess(record)[0] == "INCOMPLETE_RECORD"
    record = _reported_trial()
    assert assess(record, expected_revision="b" * 40)[0] == "INCOMPLETE_RECORD"


def test_repeat_case_and_fabricated_no_observation_are_rejected():
    record = deepcopy(_reported_trial())
    record["cases"].append(deepcopy(record["cases"][0]))
    record["cases"][0]["no_output_observation_visible"] = False
    status, problems = assess(record)
    assert status == "UNSAFE_REPORTED_UI"
    assert any("No output observation" in problem for problem in problems)
    assert any("duplicate" in problem for problem in problems)


def test_malformed_platform_does_not_crash_or_pass():
    record = _reported_trial()
    record["platform"] = ["ios"]
    assert assess(record)[0] == "INCOMPLETE_RECORD"
    record["qualified"] = "true"
    assert assess(record)[0] == "UNSAFE_REPORTED_UI"
