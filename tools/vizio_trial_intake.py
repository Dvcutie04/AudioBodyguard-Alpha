"""Check a reviewed Audio Bodyguard connection-trial report offline."""

import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys

if __package__:
    from .mobile_setup_intake import format_build_details, parse_phone_clock
else:
    from mobile_setup_intake import format_build_details, parse_phone_clock


MAX_REPORT_BYTES = 4096
_HEADER = "Audio Bodyguard connection trial (v1)"
_CLOCK_PREFIX = "Reviewed at (phone clock, UTC): "
_SELECTED_TEST = "Selected test: VIZIO candidate TCP services (not a verified TV model)"
_TRAILER = (
    "",
    "No TV command or audio was sent by this check.",
    "TV identity: Not verified",
    "TV pairing: Not verified",
    "Audio protection: Not verified",
    "",
    "Historical check only. TV identity, pairing and protection are not verified.",
    "No TV address, Wi-Fi name, password, audio or photo is included.",
    "Reviewing or sharing this text does not authorize a device action.",
)
_OUTCOMES = {
    "ADDRESS_REJECTED": (
        "No native check started: the entered address was rejected.",
        "Check the address shown in the TV's network settings against the app's private IPv4 requirement.",
    ),
    "WIFI_REQUIRED": (
        "No native check started: a suitable Wi-Fi path was unavailable.",
        "Check whether the phone and TV can use the same home Wi-Fi.",
    ),
    "CHECK_UNAVAILABLE": (
        "No new native check started: previous work was closing or unavailable.",
        "Check the app's current availability and let any previous check finish closing.",
    ),
    "SERVICE_ANSWERED_UNVERIFIED": (
        "A TCP service answered at that moment. Its identity is not authenticated.",
        "Confirm the result against the intended physical setup before reviewing TV identity and authentication.",
    ),
    "NO_SERVICE_RESPONSE": (
        "The check ended without establishing a service response. The cause is unknown.",
        "Check the TV's current address, the Wi-Fi setup and the phone's local-network access separately.",
    ),
    "CHECK_STOPPED": (
        "The check stopped. This is not a successful connection result.",
        "Keep this attempt as stopped. Any later test needs a new explicit start on the phone.",
    ),
    "CLEANUP_UNRESOLVED": (
        "Cleanup was not confirmed. Another check must remain blocked.",
        "Keep new checks blocked while the app reports unresolved cleanup.",
    ),
}


def inspect_report(raw, *, expected_platform, expected_version, expected_build):
    """Validate the v1 text against independently supplied app labels."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_REPORT_BYTES:
        raise ValueError("invalid_report_size")
    build_details = format_build_details(expected_platform, expected_version, expected_build)
    try:
        report = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("invalid_utf8") from None

    # Allow a consistent line ending and a single final terminator from text transport.
    newline = "\r\n" if "\r\n" in report else "\n"
    lines = report.removesuffix(newline).split(newline)
    if len(lines) != 20 or lines[0] != _HEADER:
        raise ValueError("invalid_connection_trial_envelope")
    reviewed_at = parse_phone_clock(lines[1], _CLOCK_PREFIX)
    if lines[3:7] != build_details.split("\n"):
        raise ValueError("trial_build_mismatch")
    if lines[2] != "" or lines[7:9] != ["", _SELECTED_TEST] or tuple(lines[11:]) != _TRAILER:
        raise ValueError("invalid_connection_trial_envelope")

    outcome_prefix = "Outcome: "
    if not lines[9].startswith(outcome_prefix):
        raise ValueError("invalid_trial_outcome")
    outcome = lines[9][len(outcome_prefix):]
    outcome_details = _OUTCOMES.get(outcome)
    if outcome_details is None or lines[10] != outcome_details[0]:
        raise ValueError("invalid_trial_outcome")
    reported_result, next_observation = outcome_details

    return {
        "schema_version": 1,
        "status": "PHONE_TRIAL_RECORDED_UNVERIFIED",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_size_bytes": len(raw),
        "source_authentication": "Not established",
        "report": {
            "platform": expected_platform,
            "version": expected_version,
            "build": expected_build,
            "reviewed_at_phone_clock": reviewed_at,
            "outcome": outcome,
            "reported_result": reported_result,
        },
        "tv_identity_verified": False,
        "tv_pairing_verified": False,
        "audio_protection_verified": False,
        "next_observation": next_observation,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Private UTF-8 connection-trial report file")
    parser.add_argument("--expected-platform", required=True, help="Android or iPhone/iPad")
    parser.add_argument("--expected-version", required=True, help="Exact expected installed version label")
    parser.add_argument("--expected-build", required=True, help="Exact expected installed build label")
    args = parser.parse_args()

    try:
        if not stat.S_ISREG(args.report.lstat().st_mode):
            raise ValueError("report_not_regular")
        with args.report.open("rb") as stream:
            raw = stream.read(MAX_REPORT_BYTES + 1)
        summary = inspect_report(raw, expected_platform=args.expected_platform,
                                 expected_version=args.expected_version, expected_build=args.expected_build)
    except (OSError, ValueError):
        print("INVALID_VIZIO_TRIAL_REPORT\nCheck the private file, app labels and connection trial v1 format.",
              file=sys.stderr)
        return 2

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
