"""Check the structure and safety wording of a manually observed P1 device trial.

This tool cannot inspect a device, trace, callback, sound path, or actual install.
Its successful status explicitly does not close an AQSS qualification gate.
"""

import argparse
import json
import re
from pathlib import Path


REQUIRED_CASES = (
    "fresh_launch",
    "foreground_attach",
    "foreground_detach",
    "background_resume",
    "process_restart",
    "accessible_large_text",
)
_SCOPES = {"ios": "app_session", "android": "connected_device_inventory"}
_INSTALLS = {"ios": "xcode_signed_device", "android": "android_debug_apk"}
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_VERSION = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+){1,2}\Z")
_BUNDLE_ID = re.compile(r"[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z][A-Za-z0-9-]*)+\Z")
_POSITIVE_DECIMAL = re.compile(r"[1-9][0-9]*\Z")
_PLACEHOLDERS = {"", "unknown", "not run", "pending", "todo", "tbd", "example"}


def _filled(value):
    return isinstance(value, str) and value.strip().lower() not in _PLACEHOLDERS


def _testflight_provenance_problems(value):
    if not isinstance(value, dict):
        return ["build_provenance must be an object for TestFlight"]
    problems = []
    for key in ("workflow_run_id", "workflow_attempt"):
        if type(value.get(key)) is not int or value[key] <= 0:
            problems.append(f"build_provenance.{key} must be a positive integer")
    for key in ("xcode_version", "iphoneos_sdk_version"):
        version = value.get(key)
        if not isinstance(version, str) or not _VERSION.fullmatch(version) or int(version.split(".")[0]) < 26:
            problems.append(f"build_provenance.{key} must name a version 26 or later")
    bundle_id = value.get("bundle_id")
    if not isinstance(bundle_id, str) or not _BUNDLE_ID.fullmatch(bundle_id):
        problems.append("build_provenance.bundle_id must be a nonempty bundle identifier")
    version = value.get("app_version")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        problems.append("build_provenance.app_version must be a dotted version")
    for key in ("build_number", "testflight_build_id"):
        number = value.get(key)
        if not isinstance(number, str) or not _POSITIVE_DECIMAL.fullmatch(number):
            problems.append(f"build_provenance.{key} must be a positive decimal string")
    digest = value.get("submitted_ipa_sha256")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        problems.append("build_provenance.submitted_ipa_sha256 must be a lowercase SHA-256 digest")
    return problems


def assess(record, *, expected_revision=None):
    """Return (record status, reasons), with unsafe display outranking missing data."""
    incomplete = []
    unsafe = []
    if not isinstance(record, dict):
        return "INCOMPLETE_RECORD", ["record must be an object"]
    schema_version = record.get("schema_version")
    if type(schema_version) is not int or schema_version not in (1, 2):
        incomplete.append("schema_version must be 1 or 2")
    revision = record.get("revision")
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        incomplete.append("revision must be an exact lowercase 40-character commit SHA")
    if expected_revision is not None and revision != expected_revision:
        incomplete.append("revision does not match expected build revision")
    platform = record.get("platform")
    if not isinstance(platform, str) or platform not in _SCOPES:
        incomplete.append("platform must be ios or android")
    if schema_version == 2:
        if platform != "ios" or record.get("installation") != "testflight":
            incomplete.append("schema_version 2 requires an iOS TestFlight installation")
        incomplete.extend(_testflight_provenance_problems(record.get("build_provenance")))
    elif isinstance(platform, str) and platform in _INSTALLS and record.get("installation") != _INSTALLS[platform]:
        incomplete.append("installation must name a physical-device install method")
    for key in ("device_model", "os_build"):
        if not _filled(record.get(key)):
            incomplete.append(f"{key} missing")
    for claim in ("qualified", "production_ready"):
        if claim in record and record[claim] is not False:
            unsafe.append(f"manual P1 record cannot claim {claim}")

    rows = record.get("cases")
    if not isinstance(rows, list):
        return "UNSAFE_REPORTED_UI" if unsafe else "INCOMPLETE_RECORD", unsafe + incomplete + ["cases missing"]
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            incomplete.append("case must be an object")
            continue
        case = row.get("id")
        if case not in REQUIRED_CASES:
            incomplete.append("case id is unknown")
            continue
        if case in seen:
            incomplete.append(f"duplicate case: {case}")
            continue
        seen.add(case)
        if row.get("performed") is not True:
            incomplete.append(f"{case}: not performed")
            continue
        coverage = row.get("coverage")
        if not _filled(coverage):
            incomplete.append(f"{case}: coverage missing")
        elif coverage != "UNKNOWN_PHYSICAL_STATE":
            unsafe.append(f"{case}: {coverage} displayed without an owned output or observer")
        for key, label in (
            ("simulation_label_visible", "SIMULATION"),
            ("no_output_observation_visible", "No output observation"),
        ):
            if row.get(key) is False:
                unsafe.append(f"{case}: {label} was missing")
            elif row.get(key) is not True:
                incomplete.append(f"{case}: {label} visibility not recorded")
        scope = row.get("hint_source")
        if isinstance(platform, str) and platform in _SCOPES and scope != _SCOPES[platform]:
            if scope is None:
                incomplete.append(f"{case}: hint source missing")
            else:
                unsafe.append(f"{case}: hint source misattributes platform callback")
        if not _filled(row.get("independent_trace_ref")):
            incomplete.append(f"{case}: independent trace reference missing")
        if case == "background_resume":
            reused = row.get("prior_visit_hint_reused")
            if reused is True:
                unsafe.append(f"{case}: previous visit hint leaked into new visit")
            elif reused is not False:
                incomplete.append(f"{case}: previous visit hint not checked")
        if case in ("foreground_attach", "foreground_detach") and type(row.get("callback_observed")) is not bool:
            incomplete.append(f"{case}: callback observed or missed not recorded")
        if case == "accessible_large_text":
            for key in ("screen_reader_checked", "large_text_checked"):
                if row.get(key) is not True:
                    incomplete.append(f"{case}: {key} not completed")
    for case in REQUIRED_CASES:
        if case not in seen:
            incomplete.append(f"required case missing: {case}")
    if unsafe:
        return "UNSAFE_REPORTED_UI", unsafe + incomplete
    if incomplete:
        return "INCOMPLETE_RECORD", incomplete
    return "STRUCTURE_COMPLETE_PHYSICAL_UNVERIFIED", []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="JSON report from a manually installed device trial")
    parser.add_argument("--expected-revision", help="Exact git revision used for the device build")
    args = parser.parse_args()
    try:
        report = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"INCOMPLETE_RECORD: cannot read JSON record: {error}")
        return 1
    status, problems = assess(report, expected_revision=args.expected_revision)
    print(status)
    for problem in problems:
        print(f"- {problem}")
    return {"STRUCTURE_COMPLETE_PHYSICAL_UNVERIFIED": 0, "INCOMPLETE_RECORD": 1, "UNSAFE_REPORTED_UI": 2}[status]


if __name__ == "__main__":
    raise SystemExit(main())
