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

    def test_controls_use_the_same_cyan_and_reject_low_contrast(self):
        self.assertEqual(self.data["palettes"]["midnight"]["control"], "64DAE8")
        self.assertEqual(self.data["palettes"]["daylight"]["control"], "64DAE8")
        for key in ("controlText", "controlBorder"):
            data = copy.deepcopy(self.data)
            if key == "controlText":
                data["palettes"]["daylight"][key] = "64DAE8"
            else:
                data["palettes"]["daylight"][key] = "FFFFFF"
            with self.assertRaisesRegex(ValueError, "contrast"):
                validate(data)

    def test_native_secondary_buttons_have_cyan_focus_and_neutral_disabled_states(self):
        # A source-level regression guard. Native builds/screenshots remain required.
        ios = (ROOT / "native/ios-app/Sources/AQSSReadOnlyApp.swift").read_text()
        android = (ROOT / "native/android/app/src/main/kotlin/com/aqss/bodyguard/prototype/InterfaceTheme.kt").read_text()
        self.assertIn("!isEnabled ? theme.outline : primary ? theme.controlBorder : theme.accent", ios)
        self.assertIn("lineWidth: isEnabled && !primary ? 2 : 1", ios)
        self.assertIn("!isEnabled ? theme.muted : primary ? theme.controlText : theme.text", ios)
        self.assertIn("StateListDrawable().apply", android)
        self.assertIn("addState(intArrayOf(-android.R.attr.state_enabled), shape(raised, 14)", android)
        self.assertIn("if (primary) controlBorder else accent", android)
        self.assertIn("RippleDrawable(ColorStateList.valueOf(accent), shapeStates, null)", android)

    def test_tv_system_choice_illustrations_use_cyan_instead_of_blue_or_purple(self):
        """All enabled app-owned choices share cyan; labels remain readable."""
        path = ROOT / "native/ios-app/Sources/SetupGuides.swift"
        source = path.read_text()
        self.assertIn("foregroundColor(theme.controlText).padding(10).background(theme.control)", source)
        self.assertNotIn("background(blue ? Color.blue : theme.violet)", source)
        self.assertIn("buttonStyle(AppButtonStyle(theme: theme))", source)
        self.assertIn("!isEnabled ? theme.outline", (ROOT / "native/ios-app/Sources/AQSSReadOnlyApp.swift").read_text())
        android = (ROOT / "native/android/app/src/main/kotlin/com/aqss/bodyguard/prototype/SetupGuideActivity.kt").read_text()
        self.assertIn("skin.style(this, primary)", android)

    def test_fresh_install_defaults_to_daylight_without_overriding_saved_preferences(self):
        # Static guard for first-launch presentation; native light-appearance screenshots
        # remain a separate verification gate. Existing saved choices are untouched.
        ios = (ROOT / "native/ios-app/Sources/AQSSReadOnlyApp.swift").read_text()
        android = (ROOT / "native/android/app/src/main/kotlin/com/aqss/bodyguard/prototype/ReadOnlyHomeActivity.kt").read_text()
        self.assertIn('@AppStorage("aqssAppearance") private var appearance = "daylight"', ios)
        self.assertIn('appearance == "daylight" ? .light : .dark', ios)
        self.assertIn('getString("appearance", "daylight") ?: "daylight"', android)
        self.assertIn('putString("appearance", value).apply()', android)
        self.assertIn('"daylight" -> false', android)

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

    def test_settings_describe_the_verified_gate_and_preview_without_dispatch_fields(self):
        for item in self.data["settings"]:
            self.assertIn("verified connection", item["explanation"])
            self.assertIn("two seconds", item["explanation"])
            self.assertIn("This preview", item["explanation"])
            self.assertIn("[?]", next(t for t in json.loads((ROOT / "contracts/tutorial_v1.json").read_text())["topics"] if t["id"] == "advanced")["steps"][0]["explanation"])
        data = copy.deepcopy(self.data)
        data["settings"][0]["action"] = "select_captions"
        with self.assertRaisesRegex(ValueError, "descriptions only"):
            validate(data)

    def test_every_tutorial_target_has_a_real_page(self):
        tutorials = json.loads((ROOT / "contracts/tutorial_v1.json").read_text())
        targets = {step["target"] for topic in tutorials["topics"] for step in topic["steps"]}
        self.assertTrue(targets.issubset(TARGET_PAGES))
        self.assertTrue(set(TARGET_PAGES.values()).issubset({page["id"] for page in self.data["pages"]}))

    def test_picture_guide_pages_use_concise_action_copy(self):
        home = self.data["pages"][0]["subtitle"]
        self.assertIn("TV and phone picture guide", home)
        for page in self.data["pages"]:
            with self.subTest(page=page["id"]):
                self.assertNotIn("this preview", page["subtitle"].lower())
                self.assertNotIn("does not", page["subtitle"].lower())
                self.assertNotIn("five-step", page["subtitle"].lower())

    def test_both_native_apps_have_the_validated_content(self):
        for path, expected in sources(validate(self.data)).items():
            with self.subTest(platform=path):
                self.assertEqual(path.read_text(), expected)
