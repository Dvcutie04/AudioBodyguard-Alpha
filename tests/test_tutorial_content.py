import copy
import json

import pytest

from tools.generate_tutorial_content import ROOT, sources, validate


def contract():
    return json.loads((ROOT / "contracts/tutorial_v1.json").read_text())


def test_beginner_default_is_brief_while_the_complete_catalog_stays_available():
    data = contract()
    presentation = data["onboarding"]
    assert presentation["featured_ids"] == ["series_intro", "commercial_volume", "remote"]
    assert len(data["feature_catalog"]["items"]) == 21
    assert "preview" in presentation["notice"].lower()
    assert "no TV control" in presentation["notice"]
    beginner = data["topics"][0]
    assert [step["target"] for step in beginner["steps"]] == [
        "welcome", "chooseTV", "chooseHome", "connectionPlan", "connectionCheck", "guideFinish",
    ]
    assert all(len(step["explanation"].split()) <= 20 for step in beginner["steps"])


def test_connection_guide_requires_both_visible_parts_without_claiming_connection():
    data = contract()
    stages = data["connection_stages"]
    assert [stage["number"] for stage in stages] == [1, 2]
    assert [stage["title"] for stage in stages] == [
        "Connect to your TV or home device", "Connect to your phone",
    ]
    assert "connectionPlan" in stages[0]["targets"]
    assert "connectionCheck" in stages[1]["targets"]
    topic = data["topics"][0]
    assert "both" in topic["steps"][0]["explanation"].lower()
    assert topic["steps"][3]["title"].startswith("1.")
    assert topic["steps"][4]["title"].startswith("2.")
    assert "not connected" in topic["steps"][4]["explanation"]
    assert not any("connected" in stage.get("status", "").lower() for stage in stages)


def test_welcome_feature_list_includes_requested_controls_with_truthful_availability():
    catalog = contract()["feature_catalog"]
    items = catalog["items"]
    assert [item["id"] for item in items[:3]] == ["series_intro", "commercial_volume", "remote"]
    assert {"loud_sounds", "presets", "equalizer", "captions", "languages", "voice", "profiles", "undo", "history", "recovery", "handoff", "background", "privacy", "setup", "input", "suggestions", "accessories", "status"} <= {item["id"] for item in items}
    assert all(item["availability"] == "planned" for item in items[:3])
    assert "preview" in catalog["note"].lower()
    assert "does not control" in catalog["note"].lower()
    assert not any("skip ads" in item["title"].lower() or item["title"].lower() == "etc." for item in items)


def test_native_tutorials_use_the_same_bounded_presentation_contract():
    data = validate(contract())
    for path, content in sources(data).items():
        assert path.read_text() == content


@pytest.mark.parametrize("change", ["duplicate_feature", "active_feature", "feature_command", "stage_status", "invalid_stage_target"])
def test_feature_and_connection_catalogs_reject_commands_or_fabricated_availability(change):
    data = contract()
    if change == "duplicate_feature":
        data["feature_catalog"]["items"].append(data["feature_catalog"]["items"][0])
    elif change == "active_feature":
        data["feature_catalog"]["items"][0]["availability"] = "active"
    elif change == "feature_command":
        data["feature_catalog"]["items"][0]["actuate"] = "skip_intro"
    elif change == "stage_status":
        data["connection_stages"][0]["status"] = "connected"
    else:
        data["connection_stages"][0]["targets"] = [[]]
    with pytest.raises(ValueError):
        validate(data)


def test_readiness_guidance_keeps_all_six_prerequisites_unknown():
    readiness = next(topic for topic in validate(contract())["topics"] if topic["id"] == "readiness")
    assert {step["target"] for step in readiness["steps"]} == {
        "checkHardware", "checkQualification", "checkPermission", "checkRoute",
        "checkRuntime", "checkEvidence",
    }
    for step in readiness["steps"]:
        assert step["area"] == "checklist"
        assert step["explanation"].startswith("Unknown:")


def test_beginner_guide_has_one_ordered_connection_path_and_no_actuation():
    data = validate(contract())
    topic = data["topics"][0]
    assert topic["id"] == "getting_started"
    assert [s["target"] for s in topic["steps"]] == [
        "welcome", "chooseTV", "chooseHome", "connectionPlan",
        "connectionCheck", "guideFinish",
    ]
    assert "does not monitor or change TV audio" in topic["steps"][0]["explanation"]
    assert "not connected" in topic["steps"][4]["explanation"]
    assert "Help" in topic["steps"][-1]["explanation"]
    assert {c["id"] for c in data["choices"]["chooseHome"]} == {"alexa", "google", "both", "neither"}
    assert {"samsung", "lg", "sony", "other", "unsure"} <= {c["id"] for c in data["choices"]["chooseTV"]}


@pytest.mark.parametrize("change", ["unknown_feature", "duplicate_feature", "unknown_route", "helper_route", "duplicate_route", "command"])
def test_simplified_onboarding_rejects_ambiguous_or_unsafe_continuation(change):
    data = contract()
    presentation = data["onboarding"]
    if change == "unknown_feature":
        presentation["featured_ids"][0] = "invented"
    elif change == "duplicate_feature":
        presentation["featured_ids"][0] = presentation["featured_ids"][1]
    elif change == "unknown_route":
        presentation["picture_continue_routes"].append("invented")
    elif change == "helper_route":
        presentation["picture_continue_routes"].append("roku_network")
    elif change == "duplicate_route":
        presentation["picture_continue_routes"].append(presentation["picture_continue_routes"][0])
    else:
        presentation["connect"] = "run_adapter"
    with pytest.raises(ValueError):
        validate(data)


@pytest.mark.parametrize("change", ["duplicate", "command", "icon", "group", "empty"])
def test_connection_choices_reject_unsafe_or_ambiguous_content(change):
    data = copy.deepcopy(contract())
    choices = data["choices"]["chooseTV"]
    if change == "duplicate":
        choices.append(choices[0])
    elif change == "command":
        choices[0]["connect"] = "run_adapter"
    elif change == "icon":
        choices[0]["icon"] = "https://tracker.invalid/image"
    elif change == "group":
        data["choices"]["unknown"] = choices
    else:
        choices.clear()
    with pytest.raises(ValueError):
        validate(data)


@pytest.mark.parametrize("change", ["action", "target", "area", "example", "too_many"])
def test_tutorial_rejects_commands_unknown_targets_and_unlabeled_examples(change):
    data = copy.deepcopy(contract())
    step = data["topics"][0]["steps"][0]
    if change == "action":
        step["actuate"] = "set_volume"
    elif change == "target":
        step["target"] = "production_adapter"
    elif change == "area":
        step["area"] = "options"
    elif change == "example":
        step["example"] = "Your speaker is now protected"
    else:
        data["topics"][0]["steps"] *= 3
    with pytest.raises(ValueError):
        validate(data)
