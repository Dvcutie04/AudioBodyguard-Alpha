"""Prepare a private, unverified N2b draft from shared mobile setup text.

Only the worksheet and attachment envelopes are interpreted. Attachment payloads
remain opaque, unauthenticated text. No device, native audio or network API is
called; matching an expected build does not authenticate the sender or software.
Use ordinary files in stable private directories while reading and writing.
"""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import stat
import unicodedata

if __package__:
    from .n2b_inventory_record import REQUIRED_SECTIONS
else:
    from n2b_inventory_record import REQUIRED_SECTIONS


MAX_SOURCE_BYTES = 64 * 1024 + 1  # Largest native report plus one optional final LF.
_FIELDS = (
    ("playback_phone", "Playback phone"), ("intended_output", "Intended output"),
    ("observer_phone", "Second phone"), ("recording_app", "Recording app and mode"),
    ("placement", "Phone placement"), ("constraints", "Setup constraints"),
)
_UNKNOWN_LINES = (
    "Actual playback route: Unknown", "Negotiated format: Unknown",
    "Backend and ownership review: Pending", "Independent capture: Not recorded",
    "Calibration and clock mapping: Unknown", "Playback/capture consent: Not collected",
    "Physical output and protection: Not verified",
)
_ATTACHMENTS = {
    "android_inventory": {
        "platform": "Android", "worksheet": 1,
        "separator": "\n\nAttached output snapshot\nSnapshot only. Outputs may have changed.\n\n",
        "header": "Audio Bodyguard output inventory (v1)",
        "clock": "Read finished at (phone clock, UTC): ", "optional_milliseconds": True,
        "tail": "\n\nSelected playback route: Unknown\nNegotiated format: Unknown\n"
                "Independent output capture: Not recorded\nCalibration: Not recorded\n"
                "Physical output and protection: Not verified\n\nSnapshot only. Outputs may have changed.\n"
                "Advertised metadata only; not physical output evidence.",
        "units": 24 * 1024, "bytes": 48 * 1024,
    },
    "android_quiet_check": {
        "platform": "Android", "worksheet": 2,
        "separator": "\n\nAttached quiet check report\nFramework check only. Sound and protection are not verified.\n\n",
        "header": "Audio Bodyguard quiet output check (v1)",
        "clock": "Reviewed at (phone clock, UTC): ", "optional_milliseconds": False,
        "tail": "\n\nPhysical output and protection: Not verified\nHardware format and acoustic route: Not verified\n"
                "Calibration and independent capture: Not recorded\nNo acoustic latency, silence or retirement is established.\n\n"
                "Framework check only. Sound and protection are not verified.",
        "units": 32 * 1024, "bytes": 32 * 1024,
    },
    "ios_session_details": {
        "platform": "iPhone/iPad", "worksheet": 2,
        "separator": "\n\nIncluded output details (historical snapshot)\n"
                     "The original capture time belongs to the session snapshot. Notes were reviewed separately.\n\n",
        "header": "Audio Bodyguard iPhone output details (v1)",
        "clock": "Captured at (phone clock, UTC): ", "optional_milliseconds": False,
        "tail": "\nActual playback route: Unknown\nNegotiated format: Unknown\nBackend and ownership review: Pending\n"
                "Independent capture: Not recorded\nCalibration and clock mapping: Unknown\n"
                "Physical output and protection: Not verified\nOutputs may have changed since this snapshot.\n\n"
                "Session details only. Playback and protection are not verified.",
        "units": 8 * 1024, "bytes": 16 * 1024,
    },
}


def _require(condition, code):
    if not condition:
        # Codes are fixed strings, never excerpts of untrusted text or local paths.
        raise ValueError(code)


def _units(text):
    return len(text.encode("utf-16-le")) // 2


def _unsafe(char):
    return unicodedata.category(char) in ("Cc", "Cf", "Cs", "Zl", "Zp")


def _identity(platform, version, build):
    _require(platform in ("Android", "iPhone/iPad"), "invalid_platform")
    _require(isinstance(version, str) and 1 <= _units(version) <= 96 and
             version.strip() == version and not any(_unsafe(c) for c in version), "invalid_version")
    _require(isinstance(build, str) and re.fullmatch(r"[0-9]{1,19}|Unavailable", build) is not None, "invalid_build")
    return f"Audio Bodyguard\nPlatform: {platform}\nVersion: {version}\nBuild: {build}"


def _clock(line, prefix, *, optional_milliseconds=False):
    _require(line.startswith(prefix), "missing_phone_clock")
    value = line[len(prefix):]
    fraction = r"(?:\.[0-9]{3})?" if optional_milliseconds else r"\.[0-9]{3}"
    _require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}" + fraction + "Z", value) is not None,
             "invalid_phone_clock")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid_phone_clock") from None
    _require(parsed.year >= 1970, "invalid_phone_clock")
    return value  # No clock conversion, ordering assumption or latency calculation.


def _note(line, title):
    prefix = title + ": "
    _require(line.startswith(prefix), "missing_or_reordered_note")
    value = line[len(prefix):]
    if value == "Unknown":
        return None
    _require(re.fullmatch(r'"(?:[^"\\]|\\["\\])*"', value) is not None, "invalid_note_quoting")
    decoded = json.loads(value)
    _require(1 <= _units(decoded) <= 160 and decoded.strip() == decoded and
             not any(_unsafe(c) for c in decoded), "invalid_note_value")
    return decoded


def _attachment(text, platform, worksheet, envelope):
    if not text:
        _require(worksheet == 1, "missing_attachment")
        return None
    for kind, spec in _ATTACHMENTS.items():
        if spec["platform"] != platform or spec["worksheet"] != worksheet or not text.startswith(spec["separator"]):
            continue
        source = text[len(spec["separator"]):]
        _require(_units(source) <= spec["units"] and len(source.encode("utf-8")) <= spec["bytes"], "attachment_too_large")
        lines = source.split("\n")
        _require(len(lines) >= 8 and lines[0] == spec["header"] and lines[2] == "", "invalid_attachment_envelope")
        headers = {value["header"] for value in _ATTACHMENTS.values()}
        headers.update(("Audio Bodyguard test setup (v1)", "Audio Bodyguard test setup (v2)"))
        _require(sum(line in headers for line in lines) == 1, "multiple_report_envelopes")
        captured = _clock(lines[1], spec["clock"], optional_milliseconds=spec["optional_milliseconds"])
        _require("\n".join(lines[3:7]) == envelope, "attachment_build_mismatch")
        _require(source.endswith(spec["tail"]), "invalid_attachment_uncertainty")
        return {"kind": kind, "captured_at_phone_clock": captured,
                "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "size_bytes": len(source.encode("utf-8")),
                "interpretation": "Envelope only; metadata and trace payload remain opaque and unverified"}
    raise ValueError("unsupported_attachment")


def prepare_intake(raw, *, expected_platform, expected_version, expected_build, source_revision):
    """Return (intake summary, incomplete inventory); neither grants authority."""
    _require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_SOURCE_BYTES, "invalid_source_size")
    _require(isinstance(source_revision, str) and re.fullmatch(r"[0-9a-f]{40}", source_revision) is not None,
             "invalid_declared_source_revision")
    expected = _identity(expected_platform, expected_version, expected_build)
    try:
        original = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("invalid_utf8") from None
    _require(not any(_unsafe(c) for c in original if c != "\n"), "unsafe_source_text")
    trailing = original.endswith("\n")
    text = original[:-1] if trailing else original
    lines = text.split("\n")
    _require(len(lines) >= 26 and lines[0] in (
        "Audio Bodyguard test setup (v1)", "Audio Bodyguard test setup (v2)"), "unsupported_worksheet")
    worksheet = int(lines[0][-2])
    reviewed = _clock(lines[1], "Notes reviewed at (phone clock, UTC): ")
    _require(lines[2] == lines[7] == "" and "\n".join(lines[3:7]) == expected, "worksheet_build_mismatch")
    _require(lines[8] == "Your notes (not verified)", "invalid_notes_heading")
    notes = {key: _note(lines[9 + index], title) for index, (key, title) in enumerate(_FIELDS)}
    _require(lines[15] == lines[23] == "" and tuple(lines[16:23]) == _UNKNOWN_LINES, "invalid_worksheet_uncertainty")
    notice = ("Setup notes and session details. Nothing is verified."
              if expected_platform == "iPhone/iPad" and worksheet == 2 else "Setup notes only. Nothing is verified.")
    _require(lines[24] == notice and lines[25] == "This worksheet does not authorize playback or recording.",
             "invalid_worksheet_notice")
    prefix = "\n".join(lines[:26])
    attachment = _attachment(text[len(prefix):], expected_platform, worksheet, expected)
    if attachment is None:
        unit_limit, byte_limit = 4096, 8192
    elif expected_platform == "iPhone/iPad":
        unit_limit, byte_limit = 16384, 32768
    elif attachment["kind"] == "android_quiet_check":
        unit_limit = byte_limit = 49152
    else:
        unit_limit, byte_limit = 32768, 65536
    _require(_units(text) <= unit_limit and len(text.encode("utf-8")) <= byte_limit, "worksheet_too_large")
    digest = hashlib.sha256(raw).hexdigest()
    summary = {
        "schema_version": 1, "status": "PHONE_REPORT_RECORDED_UNVERIFIED",
        "qualified": False, "production_ready": False,
        "source_revision": source_revision,
        "source_revision_basis": "Operator supplied; matching report labels do not prove this source ran",
        "source_sha256": digest, "source_size_bytes": len(raw),
        "source_authentication": "Not established", "transport_trailing_newline": trailing,
        "report": {"worksheet_version": worksheet, "platform": expected_platform,
                   "version": expected_version, "build": expected_build,
                   "notes_reviewed_at_phone_clock": reviewed, "notes": notes, "attachment": attachment},
    }
    # No free-text answer or framework observation completes an eight-row record.
    quoted = lambda *keys: json.dumps({key: notes[key] for key in keys}, ensure_ascii=False)
    details = {
        "host": "App labels matched the operator's expectation. Host, OS, compiler and driver observations remain incomplete. Unverified notes: " + quoted("playback_phone"),
        "output_route": "Intended output is a proposal, not an observed physical route. Unverified notes: " + quoted("intended_output"),
        "format": "Negotiated format, conversion path, buffers and native resource remain unknown. Attachment payload was not interpreted.",
        "capture": "Independent acquisition and calibration remain unrecorded. Unverified proposed arrangement: " + quoted("observer_phone", "recording_app", "placement"),
        "ownership": "Backend/ownership review, process identity and authoritative admission/hold cut remain pending.",
        "work": "A report and framework call returns do not establish outstanding native work, last use or physical retirement.",
        "continuity": "Phone-clock dates are untrusted labels, not clock mapping, native timing, continuity, crash history or latency evidence.",
        "consent": "Playback/capture consent and the safe trial plan remain uncollected. Unverified constraints: " + quoted("constraints"),
    }
    inventory = {
        "schema_version": 1, "revision": source_revision, "observed_on": None,
        "qualified": False, "production_ready": False,
        "sections": {name: {"status": "unknown", "details": details[name], "evidence_refs": ["phone-report"]}
                     for name in REQUIRED_SECTIONS},
        "evidence": [{"id": "phone-report", "path": "phone-report.txt", "sha256": digest}],
    }
    return summary, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Private UTF-8 shared setup report")
    parser.add_argument("--output-dir", required=True, type=Path, help="New private directory; existing paths are never replaced")
    parser.add_argument("--expected-platform", required=True, help="Android or iPhone/iPad")
    parser.add_argument("--expected-version", required=True, help="Exact expected installed version label")
    parser.add_argument("--expected-build", required=True, help="Exact expected installed build label")
    parser.add_argument("--source-revision", required=True, help="Operator-supplied 40-character lowercase source SHA")
    args = parser.parse_args()
    try:
        _require(stat.S_ISREG(args.report.lstat().st_mode), "source_not_regular")
        with args.report.open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
        summary, inventory = prepare_intake(raw, expected_platform=args.expected_platform,
            expected_version=args.expected_version, expected_build=args.expected_build, source_revision=args.source_revision)
        # Finish validation and serialization before creating any output.
        contents = {"phone-report.txt": raw,
                    "intake.json": (json.dumps(summary, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
                    "inventory.json": (json.dumps(inventory, indent=2, ensure_ascii=False) + "\n").encode("utf-8")}
    except (OSError, ValueError):
        print("INVALID_PHONE_REPORT\nCheck the private file, expected build, declared revision and supported worksheet envelope.")
        return 2
    created = False
    written = []
    try:
        args.output_dir.mkdir(mode=0o700)
        created = True
        for name, data in contents.items():
            path = args.output_dir / name
            with path.open("xb") as stream:
                written.append(path)
                path.chmod(0o600)
                stream.write(data)
    except OSError:
        # Remove only our new fixed-name files; never recurse into existing work.
        if created:
            for path in written:
                try:
                    path.unlink()
                except OSError:
                    pass
            try:
                args.output_dir.rmdir()
            except OSError:
                pass
        print("PHONE_INTAKE_NOT_SAVED\nChoose a new directory beneath a stable private parent; existing paths are not replaced.")
        return 3
    print("PHONE_REPORT_RECORDED_UNVERIFIED\nPrivate draft saved; all eight inventory sections remain unknown.\n"
          "N2b–N5 remain pending. Report labels and hashes do not authenticate hardware observations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
