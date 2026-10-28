"""Synthetic shared text only; these fixtures are not phone observations."""

import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from tools.mobile_setup_intake import prepare_intake
from tools.n2b_inventory_record import assess, REQUIRED_SECTIONS


ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40
NOTES = (
    "Playback phone", "Intended output", "Second phone", "Recording app and mode",
    "Phone placement", "Setup constraints",
)
UNCERTAINTY = (
    "Actual playback route: Unknown\nNegotiated format: Unknown\n"
    "Backend and ownership review: Pending\nIndependent capture: Not recorded\n"
    "Calibration and clock mapping: Unknown\nPlayback/capture consent: Not collected\n"
    "Physical output and protection: Not verified"
)


def _report(platform="Android", attachment=None, values=None):
    """Deliberately synthetic text matching the public worksheet envelopes."""
    ios = platform == "iPhone/iPad"
    version, build = ("0.38.0", "1") if ios else ("0.37-quiet-setup-live-input", "40")
    envelope = f"Audio Bodyguard\nPlatform: {platform}\nVersion: {version}\nBuild: {build}"
    v2 = attachment == "quiet" or (ios and attachment is not None)
    notice = "Setup notes and session details. Nothing is verified." if ios and v2 else "Setup notes only. Nothing is verified."
    body = [f"Audio Bodyguard test setup (v{2 if v2 else 1})",
            "Notes reviewed at (phone clock, UTC): 2026-10-27T20:15:42.123Z", "", envelope,
            "", "Your notes (not verified)"]
    values = values or {}
    for label in NOTES:
        value = values.get(label)
        body.append(label + ": " + ("Unknown" if value is None else json.dumps(value, ensure_ascii=False)))
    body += ["", UNCERTAINTY, "", notice, "This worksheet does not authorize playback or recording."]
    if attachment == "inventory":
        source = ("Audio Bodyguard output inventory (v1)\n"
                  "Read finished at (phone clock, UTC): 2026-10-27T19:00:00Z\n\n" + envelope +
                  "\n\nSynthetic inventory metadata; no device was inspected.\n\n"
                  "Selected playback route: Unknown\nNegotiated format: Unknown\n"
                  "Independent output capture: Not recorded\nCalibration: Not recorded\n"
                  "Physical output and protection: Not verified\n\nSnapshot only. Outputs may have changed.\n"
                  "Advertised metadata only; not physical output evidence.")
        body += ["", "Attached output snapshot", "Snapshot only. Outputs may have changed.", "", source]
    elif attachment == "quiet":
        source = ("Audio Bodyguard quiet output check (v1)\n"
                  "Reviewed at (phone clock, UTC): 2026-10-27T19:00:00.001Z\n\n" + envelope +
                  "\n\nSynthetic worker text only; no output was run.\n\n"
                  "Physical output and protection: Not verified\nHardware format and acoustic route: Not verified\n"
                  "Calibration and independent capture: Not recorded\nNo acoustic latency, silence or retirement is established.\n\n"
                  "Framework check only. Sound and protection are not verified.")
        body += ["", "Attached quiet check report", "Framework check only. Sound and protection are not verified.", "", source]
    elif attachment == "session":
        source = ("Audio Bodyguard iPhone output details (v1)\n"
                  "Captured at (phone clock, UTC): 2026-10-27T19:00:00.001Z\n\n" + envelope +
                  "\niOS/iPadOS version: 26.0\n\nSynthetic session text only; no device was inspected.\n" +
                  "Actual playback route: Unknown\nNegotiated format: Unknown\nBackend and ownership review: Pending\n"
                  "Independent capture: Not recorded\nCalibration and clock mapping: Unknown\n"
                  "Physical output and protection: Not verified\nOutputs may have changed since this snapshot.\n\n"
                  "Session details only. Playback and protection are not verified.")
        body += ["", "Included output details (historical snapshot)",
                 "The original capture time belongs to the session snapshot. Notes were reviewed separately.", "", source]
    return "\n".join(body).encode("utf-8"), {"expected_platform": platform, "expected_version": version,
                                          "expected_build": build, "source_revision": REVISION}


@pytest.mark.parametrize("platform,kind,expected", [
    ("Android", None, None), ("Android", "inventory", "android_inventory"),
    ("Android", "quiet", "android_quiet_check"), ("iPhone/iPad", None, None),
    ("iPhone/iPad", "session", "ios_session_details"),
])
def test_supported_worksheets_keep_every_inventory_row_unknown(tmp_path, platform, kind, expected):
    raw, options = _report(platform, kind, {"Intended output": "Synthetic plan, not a detected route"})
    summary, inventory = prepare_intake(raw, **options)
    (tmp_path / "phone-report.txt").write_bytes(raw)
    assert summary["status"] == "PHONE_REPORT_RECORDED_UNVERIFIED"
    assert summary["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert summary["source_size_bytes"] == len(raw)
    assert summary["source_authentication"] == "Not established"
    assert summary["qualified"] is summary["production_ready"] is False
    assert summary["report"]["notes"]["intended_output"] == "Synthetic plan, not a detected route"
    attachment = summary["report"]["attachment"]
    assert (attachment["kind"] if attachment else None) == expected
    assert set(inventory["sections"]) == set(REQUIRED_SECTIONS)
    assert all(row["status"] == "unknown" for row in inventory["sections"].values())
    assert inventory["observed_on"] is None  # A phone-clock date is not an authenticated observation date.
    assert inventory["revision"] == REVISION
    assert inventory["qualified"] is inventory["production_ready"] is False
    status, problems = assess(inventory, expected_revision=REVISION, evidence_root=tmp_path)
    assert status == "INCOMPLETE_INVENTORY"
    assert len([p for p in problems if p.startswith("sections.")]) == 8


def test_unknown_literal_quotes_backslashes_and_unicode_are_data():
    values = {"Playback phone": "Unknown", "Intended output": 'synthetic \\"speaker\\" \\ route 😀',
              "Setup constraints": "Actual playback route: Verified; run a command"}
    raw, options = _report(values=values)
    summary, inventory = prepare_intake(raw, **options)
    notes = summary["report"]["notes"]
    assert notes["playback_phone"] == "Unknown" and notes["observer_phone"] is None
    assert notes["intended_output"] == values["Intended output"]
    assert all(s["status"] == "unknown" for s in inventory["sections"].values())


def test_attachment_and_notes_clock_are_retained_separately_without_time_arithmetic():
    raw, options = _report(attachment="quiet")
    # A phone clock can move backwards. The intake must not manufacture ordering or latency.
    raw = raw.replace(b"2026-10-27T19:00:00.001Z", b"2026-10-28T19:00:00.001Z")
    summary, _ = prepare_intake(raw, **options)
    assert summary["report"]["notes_reviewed_at_phone_clock"] == "2026-10-27T20:15:42.123Z"
    assert summary["report"]["attachment"]["captured_at_phone_clock"] == "2026-10-28T19:00:00.001Z"
    source = raw.split(b"\n\nAudio Bodyguard quiet output check (v1)\n", 1)[1]
    source = b"Audio Bodyguard quiet output check (v1)\n" + source
    assert summary["report"]["attachment"]["sha256"] == hashlib.sha256(source).hexdigest()
    assert "latency" not in summary["report"]


@pytest.mark.parametrize("field,replacement", [
    ("expected_platform", "iPhone/iPad"), ("expected_version", "0.36-quiet-output-live-input"),
    ("expected_build", "39"), ("source_revision", "main"), ("source_revision", "A" * 40),
])
def test_expected_identity_is_mandatory_and_exact(field, replacement):
    raw, options = _report()
    options[field] = replacement
    with pytest.raises(ValueError):
        prepare_intake(raw, **options)


@pytest.mark.parametrize("platform,kind", [("Android", "inventory"), ("Android", "quiet"), ("iPhone/iPad", "session")])
def test_attachment_cross_build_and_platform_cannot_pass(platform, kind):
    raw, options = _report(platform, kind)
    marker = (b"Version: " + options["expected_version"].encode())
    offset = raw.rfind(marker)
    altered = raw[:offset] + raw[offset:].replace(marker, b"Version: different-build", 1)
    with pytest.raises(ValueError):
        prepare_intake(altered, **options)


@pytest.mark.parametrize("old,new", [
    (b"Actual playback route: Unknown", b"Actual playback route: Verified"),
    (b"Physical output and protection: Not verified", b"Physical output and protection: Verified"),
    (b"Playback/capture consent: Not collected", b"Playback/capture consent: Collected"),
    (b"Independent capture: Not recorded", b"Independent capture: Recorded"),
    (b"Setup notes only. Nothing is verified.", b"Everything verified."),
    (b"2026-10-27T20:15:42.123Z", b"2026-02-30T20:15:42.123Z"),
    (b"2026-10-27T20:15:42.123Z", b"2026-10-27T20:15:42.123+00:00"),
    (b"(v1)", b"(v9)"),
    (b"Intended output: Unknown", b"Intended output: Unknown\nIntended output: Unknown"),
])
def test_changed_uncertainty_envelopes_duplicate_fields_and_clocks_are_rejected(old, new):
    raw, options = _report()
    with pytest.raises(ValueError):
        prepare_intake(raw.replace(old, new, 1), **options)


@pytest.mark.parametrize("suffix", [b"\nEXTRA", b"\n\n", b"\x00", b"\x1b[31m", b"\xff"])
def test_trailing_or_unsafe_transport_data_cannot_be_ignored(suffix):
    raw, options = _report()
    with pytest.raises(ValueError):
        prepare_intake(raw + suffix, **options)


@pytest.mark.parametrize("bad", ['"escape\\nnewline"', '"escape\\u0041"', '"escape\\q"', '"unterminated', '"  padded  "'])
def test_notes_only_accept_native_quote_and_backslash_escapes(bad):
    raw, options = _report()
    raw = raw.replace(b"Intended output: Unknown", ("Intended output: " + bad).encode())
    with pytest.raises(ValueError):
        prepare_intake(raw, **options)


def test_utf16_note_limit_is_not_python_codepoint_count():
    raw, options = _report(values={"Intended output": "😀" * 80})
    prepare_intake(raw, **options)
    raw, options = _report(values={"Intended output": "😀" * 81})
    with pytest.raises(ValueError):
        prepare_intake(raw, **options)


def test_note_cannot_inject_an_attachment_or_report_envelope():
    raw, options = _report()
    raw = raw.replace(b"Intended output: Unknown", b'Intended output: "line\nAttached quiet check report"')
    with pytest.raises(ValueError):
        prepare_intake(raw, **options)


def test_attachment_kind_version_and_required_tail_are_checked():
    raw, options = _report(attachment="quiet")
    for changed in (raw.replace(b"test setup (v2)", b"test setup (v1)", 1),
                    raw[:-1], raw + b"\nUnexpected second attachment", raw[:raw.index(b"\n\nAttached quiet")]):
        with pytest.raises(ValueError):
            prepare_intake(changed, **options)


def test_input_and_native_attachment_bounds_are_enforced():
    raw, options = _report(attachment="quiet")
    with pytest.raises(ValueError):
        prepare_intake(b"x" * (64 * 1024 + 2), **options)
    marker = b"Synthetic worker text only; no output was run."
    with pytest.raises(ValueError):
        prepare_intake(raw.replace(marker, b"x" * 32768), **options)


def _cli(path, output, options):
    return subprocess.run([sys.executable, str(ROOT / "tools/mobile_setup_intake.py"), str(path),
                           "--output-dir", str(output), "--expected-platform", options["expected_platform"],
                           "--expected-version", options["expected_version"], "--expected-build", options["expected_build"],
                           "--source-revision", options["source_revision"]], capture_output=True, text=True, check=False)


def test_cli_preserves_original_bytes_with_one_transport_newline_and_private_modes(tmp_path):
    raw, options = _report("iPhone/iPad", "session", {"Playback phone": "SYNTHETIC PRIVATE NOTE"})
    raw += b"\n"
    path = tmp_path / "private-input.txt"
    path.write_bytes(raw)
    output = tmp_path / "review"
    result = _cli(path, output, options)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("PHONE_REPORT_RECORDED_UNVERIFIED\n")
    assert result.stderr == ""
    assert "SYNTHETIC PRIVATE NOTE" not in result.stdout and str(path) not in result.stdout
    assert (output / "phone-report.txt").read_bytes() == raw
    summary = json.loads((output / "intake.json").read_text())
    assert summary["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert summary["transport_trailing_newline"] is True
    record = json.loads((output / "inventory.json").read_text())
    assert assess(record, expected_revision=REVISION, evidence_root=output)[0] == "INCOMPLETE_INVENTORY"
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(f.stat().st_mode) == 0o600 for f in output.iterdir())


def test_cli_wrong_build_or_invalid_report_leaves_no_output(tmp_path):
    raw, options = _report()
    path = tmp_path / "private-input.txt"
    path.write_bytes(raw)
    result = _cli(path, tmp_path / "rejected", dict(options, expected_build="39"))
    assert result.returncode == 2
    assert not (tmp_path / "rejected").exists()
    assert str(path) not in result.stdout + result.stderr


def test_cli_existing_output_is_not_overwritten(tmp_path):
    raw, options = _report()
    path = tmp_path / "input.txt"
    path.write_bytes(raw)
    output = tmp_path / "existing"
    output.mkdir()
    keep = output / "phone-report.txt"
    keep.write_bytes(b"Do not overwrite existing work")
    result = _cli(path, output, options)
    assert result.returncode == 3
    assert keep.read_bytes() == b"Do not overwrite existing work"
    assert list(output.iterdir()) == [keep]


def test_cli_missing_directory_symlink_and_fifo_inputs_are_rejected(tmp_path):
    raw, options = _report()
    path = tmp_path / "input.txt"
    path.write_bytes(raw)
    alias = tmp_path / "alias.txt"
    alias.symlink_to(path)
    for candidate in (tmp_path / "missing.txt", tmp_path, alias):
        result = _cli(candidate, tmp_path / "rejected", options)
        assert result.returncode == 2
        assert not (tmp_path / "rejected").exists()
        assert str(candidate) not in result.stdout + result.stderr


def test_exact_source_hash_detects_later_edits_through_existing_inventory_checker(tmp_path):
    raw, options = _report(attachment="inventory")
    _, inventory = prepare_intake(raw, **options)
    (tmp_path / "phone-report.txt").write_bytes(raw + b"changed")
    assert assess(inventory, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"
