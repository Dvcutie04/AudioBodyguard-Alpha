"""Catch missing instructional pictures before native packaging."""
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "native/feature-pictures"


def test_native_instructions_reference_valid_bundled_pictures():
    catalog = json.loads((ASSETS / "guides.json").read_text())
    required = {step["picture"] for guide in catalog.values() for step in guide["steps"]}
    for directory in (ROOT / "native/ios-app/Sources",
                      ROOT / "native/android/app/src/main/kotlin/com/aqss/bodyguard/prototype"):
        for source in directory.glob("*"):
            if source.suffix not in {".swift", ".kt"}:
                continue
            required.update(re.findall(r'picture: "([\w-]+)"', source.read_text()))
            required.update(re.findall(r'FeaturePictureGuide.step\(skin, "([\w-]+)"', source.read_text()))
    for name in required:
        data = (ASSETS / (name + ".png")).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", name
        assert struct.unpack(">II", data[16:24]) == (660, 246), name
    android = (ROOT / "native/android/app/build.gradle.kts").read_text()
    apple = (ROOT / "native/ios-app/AQSSReadOnly.xcodeproj/project.pbxproj").read_text()
    assert 'assets.srcDir("../../feature-pictures")' in android
    assert 'path = "../feature-pictures"' in apple
