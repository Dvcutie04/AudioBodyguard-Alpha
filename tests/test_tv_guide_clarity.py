"""Device-specific pictures and choices must match the user's next action."""
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    return json.loads((ROOT / "contracts/setup_guides_v1.json").read_text())


def routes():
    return {route["id"]: route for route in catalog()["routes"]}


def test_google_remote_reads_the_code_on_tv_before_typing_on_phone():
    steps = routes()["google_remote"]["steps"]
    code_steps = [step for step in steps
                  if "code" in step["items"][step["focus"]].lower()
                  and step["action"] in {"check", "type"}]
    assert [step["surface"] for step in code_steps] == ["tv", "phone"]
    assert "enter" not in code_steps[0]["instruction"].lower()
    assert code_steps[1]["action"] == "type"


def test_phone_part_checks_the_existing_brand_app_with_separate_wifi_help():
    data = catalog()
    groups = {group["id"]: group for group in data["groups"]}
    all_routes = {route["id"]: route for route in data["routes"]}
    expected = {"lg": "lg_phone", "vizio": "vizio_phone", "sony": "google_phone",
                "tcl_google": "google_phone", "hisense_google": "google_phone",
                "philips_google": "google_phone", "sharp": "roku_phone"}
    for group_id, route_id in expected.items():
        assert groups[group_id].get("phone_route") == route_id
        assert route_id in groups[group_id]["routes"]
        assert all(step["surface"] == "phone" for step in all_routes[route_id]["steps"])
    assert set(groups["phone"]["routes"]) == {"phone_iphone", "phone_pixel", "phone_galaxy"}


def test_optional_lg_link_does_not_highlight_a_default_account_approval():
    from tools.export_picture_guide import svg
    from xml.etree import ElementTree

    route = routes()["lg_pair"]
    number, step = next((n, s) for n, s in enumerate(route["steps"], 1)
                        if s["title"] == "Decide whether to link accounts")
    picture = ElementTree.fromstring(svg(step, number, route))
    labels = [node.text for node in picture.findall(".//text") if node.text]
    assert "Link" in labels and "Skip" in labels
    assert f"{number} → Choose one" in labels
    assert f"{number} → Link" not in labels


def test_vizio_legacy_account_walks_each_menu_then_reads_and_enters_its_own_code():
    steps = routes()["vizio_account"]["steps"]
    actions = [step["items"][step["focus"]] for step in steps]
    assert actions[4:8] == ["Account", "VIZIO Account", "Devices & TVs", "Add TV"]
    code_steps = [step for step in steps if "6-digit" in step["items"][step["focus"]]]
    assert [step["surface"] for step in code_steps] == ["tv", "phone"]


def test_a_tv_code_picture_keeps_its_device_when_an_earlier_step_is_inserted():
    from tools.export_picture_guide import svg
    from xml.etree import ElementTree

    route = routes()["sony_new"]
    step = dict(route["steps"][4], picture_surface="tv")
    picture = ElementTree.fromstring(svg(step, 6, route))
    labels = [node.text for node in picture.findall(".//text") if node.text]
    assert "TV screen" in labels
    assert "Phone camera" in labels


def test_google_tv_has_a_remote_only_fallback_without_a_reset_or_phone_app():
    route = routes()["google_manual"]
    assert all(step["surface"] == "tv" for step in route["steps"])
    actions = [step["items"][step["focus"]] for step in route["steps"]]
    assert "Down button" in actions
    assert "Set up on TV instead" in actions
    assert route["steps"][-1]["action"] == "check"
    assert "Home screen" in route["steps"][-1]["instruction"]
    assert not any("reset" in step["instruction"].lower() for step in route["steps"])


@pytest.mark.parametrize("route_id", ["google_setup", "tcl_models"])
def test_google_qr_setup_opens_the_phone_scanner_before_showing_the_tv_code(route_id):
    steps = routes()[route_id]["steps"]
    scan = next(i for i, step in enumerate(steps) if step["action"] == "scan")
    assert steps[scan]["surface"] == "both"
    assert steps[scan]["screen"] == "TV setup QR code"
    assert steps[scan - 1]["surface"] == "phone"
    assert steps[scan - 1]["action"] == "tap"
    assert steps[scan - 1]["items"] == ["Scan code"]


@pytest.mark.parametrize("field,value", [
    ("picture_surface", []), ("picture_surface", "unknown"),
    ("pairing_route", {}), ("pairing_route", "lg_phone"),
    ("progress_version", True), ("progress_version", 0),
    ("phone_route", []), ("phone_route", "lg_pair"),
])
def test_invalid_picture_and_phone_handoffs_are_rejected(field, value):
    from tools.generate_setup_guides import validate

    data = catalog()
    route = next(r for r in data["routes"] if r["id"] == "lg_phone")
    target = (route["steps"][0] if field == "picture_surface" else
              next(g for g in data["groups"] if g["id"] == "lg") if field == "phone_route" else route)
    target[field] = value
    with pytest.raises(ValueError):
        validate(data)


def test_phone_pairing_help_cannot_jump_into_another_tv_group():
    from tools.generate_setup_guides import validate

    data = catalog()
    next(r for r in data["routes"] if r["id"] == "lg_phone")["pairing_route"] = "samsung_ok"
    with pytest.raises(ValueError, match="its TV group"):
        validate(data)
