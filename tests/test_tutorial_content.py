import copy
import json

import pytest

from tools.generate_tutorial_content import ROOT, sources, validate


def contract():
    return json.loads((ROOT / "contracts/tutorial_v1.json").read_text())


def test_native_tutorials_use_the_same_bounded_presentation_contract():
    data = validate(contract())
    for path, content in sources(data).items():
        assert path.read_text() == content


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
        "connectionCheck", "featureExample", "guideFinish",
    ]
    assert "does not monitor or change TV audio" in topic["steps"][0]["explanation"]
    assert "not connected" in topic["steps"][4]["explanation"]
    assert "Help" in topic["steps"][-1]["explanation"]
    assert {c["id"] for c in data["choices"]["chooseHome"]} == {"alexa", "google", "both", "neither"}
    assert {"samsung", "lg", "sony", "other", "unsure"} <= {c["id"] for c in data["choices"]["chooseTV"]}


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
