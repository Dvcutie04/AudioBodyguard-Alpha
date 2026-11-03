"""App Store Connect packaging requirements for the existing local UI APIs."""
import plistlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_unsigned_archive_checks_the_current_source_build_label():
    project = (ROOT / "native/ios-app/AQSSReadOnly.xcodeproj/project.pbxproj").read_text()
    source_builds = re.findall(r"CURRENT_PROJECT_VERSION = ([0-9.]+);", project)
    assert len(source_builds) == 2 and len(set(source_builds)) == 1
    workflow = (ROOT / ".github/workflows/iphoneos-device-preflight.yml").read_text()
    expected = re.search(r"Print :CFBundleVersion'[^\n]+ = '([^']+)'", workflow)
    assert expected is not None, "The archive's installed build must be checked"
    assert expected.group(1) == source_builds[0]


def test_ios_declares_its_local_preferences_and_elapsed_time_api_reasons():
    manifest = ROOT / "native/ios-app/PrivacyInfo.xcprivacy"
    assert manifest.is_file(), "Required-reason API privacy manifest is missing"
    info = plistlib.loads(manifest.read_bytes())
    reasons = {
        item["NSPrivacyAccessedAPIType"]: set(item["NSPrivacyAccessedAPITypeReasons"])
        for item in info["NSPrivacyAccessedAPITypes"]
    }
    assert "CA92.1" in reasons["NSPrivacyAccessedAPICategoryUserDefaults"]
    assert "35F9.1" in reasons["NSPrivacyAccessedAPICategorySystemBootTime"]
    assert info["NSPrivacyTracking"] is False
    assert info["NSPrivacyTrackingDomains"] == []
    assert info["NSPrivacyCollectedDataTypes"] == []
