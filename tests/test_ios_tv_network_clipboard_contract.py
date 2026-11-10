"""Reject forged or leaking VIZIO report text before comparing native clipboard."""
import pytest
from tools.check_ios_tv_network_clipboard import validate_reviewed_text

INFO = {"CFBundleShortVersionString": "0.50.0", "CFBundleVersion": "5"}
REPORT = (
    "Audio Bodyguard connection trial (v1)\nReviewed at (phone clock, UTC): 2026-11-08T00:00:00.000Z\n\n"
    "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: 0.50.0\nBuild: 5\n\n"
    "Selected test: VIZIO candidate TCP services (not a verified TV model)\n"
    "Outcome: ADDRESS_REJECTED\nNo native check started: the entered address was rejected.\n\n"
    "No TV command or audio was sent by this check.\n"
    "TV identity: Not verified\nTV pairing: Not verified\nAudio protection: Not verified\n\n"
    "Historical check only. TV identity, pairing and protection are not verified.\n"
    "No TV address, Wi-Fi name, password, audio or photo is included.\n"
    "Reviewing or sharing this text does not authorize a device action."
)

def test_safe_no_contact_report():
    assert validate_reviewed_text(REPORT, INFO)

@pytest.mark.parametrize("altered", [
    REPORT.replace("Outcome: ADDRESS_REJECTED", "Outcome: SERVICE_ANSWERED_UNVERIFIED"),
    REPORT.replace("Version: 0.50.0", "Version: 0.49.0"),
    REPORT.replace("TV pairing: Not verified", "TV pairing: Verified"),
    REPORT + "\nTV IP address: 8.8.8.8",
    REPORT.replace("No native check started: the entered address was rejected.", "A service answered."),
])
def test_rejects_mismatched_and_authority_claims(altered):
    with pytest.raises(AssertionError):
        validate_reviewed_text(altered, INFO)
