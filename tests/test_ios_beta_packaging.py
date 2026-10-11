"""App Store Connect packaging requirements for the existing local UI APIs."""
import plistlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
