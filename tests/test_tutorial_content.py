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


def test_beginner_tour_is_first_and_visits_each_page_in_learning_order():
    from tools.generate_interface_content import TARGET_PAGES

    topic = validate(contract())["topics"][0]
    assert topic["id"] == "getting_started"
    assert [step["target"] for step in topic["steps"]] == [
        "welcome", "capability", "options", "trends", "appearance",
    ]
    assert [TARGET_PAGES[step["target"]] for step in topic["steps"]] == [
        "home", "devices", "sound", "insights", "settings",
    ]
    assert "does not monitor or change audio" in topic["steps"][0]["explanation"]
    assert "invented" in topic["steps"][3]["explanation"]
    assert "Help" in topic["steps"][-1]["explanation"]


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
