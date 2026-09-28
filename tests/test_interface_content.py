import copy
import json
from pathlib import Path

import unittest

from tools.generate_interface_content import TARGET_PAGES, sources, validate

ROOT = Path(__file__).resolve().parents[1]


class InterfaceContentTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "contracts/interface_v1.json").read_text())

    def test_example_chart_cannot_lose_its_synthetic_label(self):
        data = self.data
        data["example"]["label"] = "Live audio"
        with self.assertRaisesRegex(ValueError, "synthetic"):
            validate(data)

    def test_example_cannot_claim_acoustic_units(self):
        self.data["example"]["unit"] = "dB SPL"
        with self.assertRaisesRegex(ValueError, "measured units"):
            validate(self.data)

    def test_example_rejects_unbounded_nonfinite_or_non_numeric_values(self):
        for values in ([0], [0] * 33, [0, True], [0, "50"], [0, float("nan")],
                       [0, float("inf")], [0, -1], [0, 101]):
            with self.subTest(values=values):
                data = copy.deepcopy(self.data)
                data["example"]["values"] = values
                with self.assertRaisesRegex(ValueError, "bounded example"):
                    validate(data)

    def test_theme_rejects_unreadable_secondary_text(self):
        for name in ("midnight", "daylight"):
            with self.subTest(name=name):
                data = copy.deepcopy(self.data)
                data["palettes"][name]["muted"] = data["palettes"][name]["surface"]
                with self.assertRaisesRegex(ValueError, "contrast"):
                    validate(data)

    def test_presentation_contract_rejects_actuation_fields(self):
        for change in ("mode", "feature"):
            with self.subTest(change=change):
                data = copy.deepcopy(self.data)
                if change == "mode":
                    data["mode"] = "live_control"
                else:
                    data["future"][0]["action"] = "start_audio"
                with self.assertRaises(ValueError):
                    validate(data)

    def test_every_tutorial_target_has_a_real_page(self):
        tutorials = json.loads((ROOT / "contracts/tutorial_v1.json").read_text())
        targets = {step["target"] for topic in tutorials["topics"] for step in topic["steps"]}
        self.assertTrue(targets.issubset(TARGET_PAGES))
        self.assertTrue(set(TARGET_PAGES.values()).issubset({page["id"] for page in self.data["pages"]}))

    def test_both_native_apps_have_the_validated_content(self):
        for path, expected in sources(validate(self.data)).items():
            with self.subTest(platform=path):
                self.assertEqual(path.read_text(), expected)
