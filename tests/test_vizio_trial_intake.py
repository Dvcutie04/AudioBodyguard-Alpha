import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.vizio_trial_intake import MAX_REPORT_BYTES, inspect_report


REPORT = """Audio Bodyguard connection trial (v1)
Reviewed at (phone clock, UTC): 2026-11-06T03:12:34.567Z

Audio Bodyguard
Platform: {platform}
Version: {version}
Build: {build}

Selected test: VIZIO candidate TCP services (not a verified TV model)
Outcome: {outcome}
{result}

No TV command or audio was sent by this check.
TV identity: Not verified
TV pairing: Not verified
Audio protection: Not verified

Historical check only. TV identity, pairing and protection are not verified.
No TV address, Wi-Fi name, password, audio or photo is included.
Reviewing or sharing this text does not authorize a device action."""

ANDROID = {"expected_platform": "Android", "expected_version": "0.45-friend-trial-live-input", "expected_build": "48"}
IPHONE = {"expected_platform": "iPhone/iPad", "expected_version": "1.0.0", "expected_build": "14.1"}
NO_REPLY = "The check ended without establishing a service response. The cause is unknown."
REPLY = "A TCP service answered at that moment. Its identity is not authenticated."
SCRIPT = Path(__file__).resolve().parents[1] / "tools/vizio_trial_intake.py"


def report_bytes(labels, outcome="NO_SERVICE_RESPONSE", result=NO_REPLY):
    return REPORT.format(platform=labels["expected_platform"], version=labels["expected_version"],
                         build=labels["expected_build"], outcome=outcome, result=result).encode("utf-8")


@pytest.mark.parametrize("labels", [ANDROID, IPHONE])
@pytest.mark.parametrize("outcome,result", [
    ("ADDRESS_REJECTED", "No native check started: the entered address was rejected."),
    ("WIFI_REQUIRED", "No native check started: a suitable Wi-Fi path was unavailable."),
    ("CHECK_UNAVAILABLE", "No new native check started: previous work was closing or unavailable."),
    ("SERVICE_ANSWERED_UNVERIFIED", REPLY),
    ("NO_SERVICE_RESPONSE", NO_REPLY),
    ("CHECK_STOPPED", "The check stopped. This is not a successful connection result."),
    ("CLEANUP_UNRESOLVED", "Cleanup was not confirmed. Another check must remain blocked."),
])
def test_v1_native_envelopes_preserve_their_separate_outcomes(labels, outcome, result):
    raw = report_bytes(labels, outcome, result)
    summary = inspect_report(raw, **labels)
    assert summary["status"] == "PHONE_TRIAL_RECORDED_UNVERIFIED"
    assert summary["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert summary["source_size_bytes"] == len(raw)
    assert summary["report"] == {
        "platform": labels["expected_platform"], "version": labels["expected_version"], "build": labels["expected_build"],
        "reviewed_at_phone_clock": "2026-11-06T03:12:34.567Z", "outcome": outcome, "reported_result": result,
    }
    assert summary["source_authentication"] == "Not established"
    assert summary["tv_identity_verified"] is summary["tv_pairing_verified"] is summary["audio_protection_verified"] is False
    if outcome == "SERVICE_ANSWERED_UNVERIFIED":
        assert "Confirm the result" in summary["next_observation"]
    if outcome == "CLEANUP_UNRESOLVED":
        assert "blocked" in summary["next_observation"]


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
@pytest.mark.parametrize("trailing", [False, True])
def test_transport_line_endings_keep_the_original_digest(newline, trailing):
    raw = report_bytes(IPHONE).replace(b"\n", newline) + (newline if trailing else b"")
    assert inspect_report(raw, **IPHONE)["source_sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("old,new,error", [
    (b"(v1)", b"(v2)", "invalid_connection_trial_envelope"),
    (b"Platform: Android", b"Platform: iPhone/iPad", "trial_build_mismatch"),
    (b"Build: 48", b"Build: 49", "trial_build_mismatch"),
    (b"0.45-friend-trial-live-input", b"0.46-friend-trial-live-input", "trial_build_mismatch"),
    (b"2026-11-06", b"2026-02-30", "invalid_phone_clock"),
    (b".567Z", b"Z", "invalid_phone_clock"),
    (b"NO_SERVICE_RESPONSE", b"PAIRED", "invalid_trial_outcome"),
    (b"NO_SERVICE_RESPONSE", b"SERVICE_ANSWERED_UNVERIFIED", "invalid_trial_outcome"),
    (b"TV identity: Not verified", b"TV identity: Verified", "invalid_connection_trial_envelope"),
    (b"TV pairing: Not verified", b"TV IP: 192.168.0.2", "invalid_connection_trial_envelope"),
    (b"\nAudio Bodyguard\n", b"\r\nAudio Bodyguard\n", "invalid_connection_trial_envelope"),
    (b"Outcome: ", b"\xff", "invalid_utf8"),
])
def test_rejects_changed_fields_without_echoing_them(old, new, error):
    raw = report_bytes(ANDROID).replace(old, new, 1)
    with pytest.raises(ValueError, match=f"^{error}$"):
        inspect_report(raw, **ANDROID)


def test_rejects_trailing_data_and_oversized_reports():
    raw = report_bytes(ANDROID)
    for suffix in (b"\n\n", b"\nWi-Fi password: synthetic-private-data"):
        with pytest.raises(ValueError, match="invalid_connection_trial_envelope"):
            inspect_report(raw + suffix, **ANDROID)
    with pytest.raises(ValueError, match="invalid_report_size"):
        inspect_report(b"x" * (MAX_REPORT_BYTES + 1), **ANDROID)


def test_build_label_syntax_is_platform_specific():
    labels = {**ANDROID, "expected_build": "14.1"}
    with pytest.raises(ValueError, match="invalid_build"):
        inspect_report(report_bytes(labels), **labels)


def test_cli_reads_a_private_copy_and_rejects_nonregular_files(tmp_path):
    source = tmp_path / "synthetic-private-file.txt"
    raw = report_bytes(IPHONE)
    source.write_bytes(raw)
    command = [sys.executable, str(SCRIPT), "--expected-platform", "iPhone/iPad",
               "--expected-version", "1.0.0", "--expected-build", "14.1"]
    run = subprocess.run([*command, str(source)], cwd=tmp_path, capture_output=True, check=True, text=True)
    assert json.loads(run.stdout)["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert not run.stderr
    assert source.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [source]

    link = tmp_path / "synthetic-private-link.txt"
    link.symlink_to(source)
    for invalid in (link, tmp_path):
        rejected = subprocess.run([*command, str(invalid)], cwd=tmp_path, capture_output=True, text=True)
        assert rejected.returncode == 2
        assert not rejected.stdout
        assert "INVALID_VIZIO_TRIAL_REPORT" in rejected.stderr
        assert "synthetic-private" not in rejected.stderr

    source.write_bytes(raw + b"\nWi-Fi password: synthetic-private-data")
    rejected = subprocess.run([*command, str(source)], cwd=tmp_path, capture_output=True, text=True)
    assert rejected.returncode == 2
    assert not rejected.stdout
    assert "synthetic-private" not in rejected.stderr
