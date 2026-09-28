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
