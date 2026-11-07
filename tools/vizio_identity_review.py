"""Compare private VIZIO identity-review evidence using only local files."""

import argparse
import hashlib
from hmac import compare_digest
import json
from pathlib import Path
import re
import sys

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding

if __package__:
    from .vizio_trial_intake import MAX_REPORT_BYTES, inspect_report, read_private_file
else:
    from vizio_trial_intake import MAX_REPORT_BYTES, inspect_report, read_private_file


MAX_CERTIFICATE_BYTES = 16 * 1024
_DIGEST = re.compile(r"[0-9a-f]{64}")
_MATCH = "CERTIFICATE_BYTES_MATCH_UNVERIFIED"
_FINGERPRINT_MATCH = "CERTIFICATE_FINGERPRINTS_MATCH_UNVERIFIED"


def _require_digest(value, error):
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(error)


def _certificate_status(outcome, reference_sha256, observed_der, observed_sha256):
    if outcome != "SERVICE_ANSWERED_UNVERIFIED":
        return "NO_REPORTED_SERVICE_REPLY"
    if reference_sha256 is None:
        return "INDEPENDENT_REFERENCE_REQUIRED"
    if observed_sha256 is not None:
        if compare_digest(reference_sha256, observed_sha256):
            return _FINGERPRINT_MATCH
        return "CERTIFICATE_REFERENCE_MISMATCH"
    if observed_der is None:
        return "CERTIFICATE_OBSERVATION_REQUIRED"
    if not isinstance(observed_der, bytes) or not 0 < len(observed_der) <= MAX_CERTIFICATE_BYTES:
        raise ValueError("invalid_certificate")
    try:
        certificate = x509.load_der_x509_certificate(observed_der)
        encoded = certificate.public_bytes(Encoding.DER)
    except ValueError:
        raise ValueError("invalid_certificate") from None
    if encoded != observed_der:
        raise ValueError("invalid_certificate")
    if not compare_digest(reference_sha256, hashlib.sha256(observed_der).hexdigest()):
        return "CERTIFICATE_REFERENCE_MISMATCH"
    return _MATCH


def review_identity(report, *, expected_platform, expected_version, expected_build, expected_report_sha256,
                    reference_certificate_sha256=None, observed_certificate_der=None,
                    observed_certificate_sha256=None):
    """Check evidence consistency without enrolling or authenticating a device."""
    _require_digest(expected_report_sha256, "invalid_expected_report_sha256")
    if reference_certificate_sha256 is not None:
        _require_digest(reference_certificate_sha256, "invalid_reference_certificate_sha256")
    if observed_certificate_sha256 is not None:
        _require_digest(observed_certificate_sha256, "invalid_observed_certificate_sha256")
        if observed_certificate_der is not None:
            raise ValueError("ambiguous_certificate_observation")
    intake = inspect_report(report, expected_platform=expected_platform, expected_version=expected_version,
                            expected_build=expected_build)
    digest = intake["source_sha256"]
    if not compare_digest(expected_report_sha256, digest):
        raise ValueError("reviewed_report_mismatch")
    outcome = intake["report"]["outcome"]
    return {
        "schema_version": 1,
        "status": _certificate_status(outcome, reference_certificate_sha256, observed_certificate_der,
                                      observed_certificate_sha256),
        "report_sha256": digest,
        "reported_outcome": outcome,
        "tv_identity_verified": False,
        "pairing_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Private reviewed connection-trial text")
    parser.add_argument("--expected-platform", required=True, help="Android or iPhone/iPad")
    parser.add_argument("--expected-version", required=True, help="Exact expected installed version label")
    parser.add_argument("--expected-build", required=True, help="Exact expected installed build label")
    parser.add_argument("--report-sha256", required=True, help="SHA-256 retained from the reviewed report intake")
    parser.add_argument("--reference-certificate-sha256", help="Independently obtained DER certificate SHA-256")
    observation = parser.add_mutually_exclusive_group()
    observation.add_argument("--observed-certificate", type=Path, help="Private single DER X.509 certificate")
    observation.add_argument("--observed-certificate-sha256", help="Fingerprint displayed by the app’s certificate check")
    args = parser.parse_args()

    try:
        raw = read_private_file(args.report, MAX_REPORT_BYTES)
        observed = (read_private_file(args.observed_certificate, MAX_CERTIFICATE_BYTES)
                    if args.observed_certificate is not None else None)
        summary = review_identity(raw, expected_platform=args.expected_platform, expected_version=args.expected_version,
                                  expected_build=args.expected_build, expected_report_sha256=args.report_sha256,
                                  reference_certificate_sha256=args.reference_certificate_sha256,
                                  observed_certificate_der=observed,
                                  observed_certificate_sha256=args.observed_certificate_sha256)
    except (OSError, ValueError):
        print("INVALID_VIZIO_IDENTITY_REVIEW\nCheck the private files and expected labels and digests.", file=sys.stderr)
        return 2

    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] in (_MATCH, _FINGERPRINT_MATCH) else 1


if __name__ == "__main__":
    raise SystemExit(main())
