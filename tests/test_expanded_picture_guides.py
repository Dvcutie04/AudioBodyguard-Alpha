import json
from pathlib import Path

def test_new_brands_have_evidenced_picture_routes_and_onboarding_choices():
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "contracts/setup_guides_v1.json").read_text())
    choices = json.loads((root / "contracts/tutorial_v1.json").read_text())["choices"]["chooseTV"]
    groups = {g["id"]: g for g in catalog["groups"]}
    routes = {r["id"]: r for r in catalog["routes"]}
    for brand in ("philips", "sharp", "roku", "insignia"):
        assert brand in {c["id"] for c in choices}
        assert groups[brand]["routes"]
        for route_id in groups[brand]["routes"]:
            route = routes[route_id]
            assert route["sources"] and len(route["steps"]) >= 4
            assert all(s["items"][s["focus"]] for s in route["steps"])
    assert "philips_voice_remote" in groups["philips"]["routes"]
    assert "fire_setup" in groups["insignia"]["routes"]
