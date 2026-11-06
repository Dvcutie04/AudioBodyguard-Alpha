from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
import pytest

from tests.test_vizio_trial_intake import ANDROID, IPHONE, REPLY, report_bytes
from tools.vizio_identity_review import MAX_CERTIFICATE_BYTES, review_identity


SCRIPT = Path(__file__).resolve().parents[1] / "tools/vizio_identity_review.py"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def certificates():
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "synthetic lab peer")])
    key = ec.generate_private_key(ec.SECP256R1())
    builder = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
               .public_key(key.public_key())
               .not_valid_before(datetime(2025, 1, 1, tzinfo=timezone.utc))
               .not_valid_after(datetime(2027, 1, 1, tzinfo=timezone.utc)))
    return tuple(builder.serial_number(serial).sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.DER)
                 for serial in (1, 2))


def reached(labels=IPHONE):
    return report_bytes(labels, "SERVICE_ANSWERED_UNVERIFIED", REPLY)


def review(report, labels=IPHONE, **evidence):
    options = {"expected_report_sha256": sha256(report), **labels, **evidence}
    summary = review_identity(report, **options)
    assert summary["report_sha256"] == sha256(report)
    assert summary["tv_identity_verified"] is summary["pairing_authorized"] is False
    return summary


@pytest.mark.parametrize("labels", [ANDROID, IPHONE])
def test_equal_certificate_bytes_remain_unverified_on_both_platforms(labels, certificates):
    original, _ = certificates
    summary = review(reached(labels), labels, reference_certificate_sha256=sha256(original),
                     observed_certificate_der=original)
    assert summary["status"] == "CERTIFICATE_BYTES_MATCH_UNVERIFIED"
    assert summary["reported_outcome"] == "SERVICE_ANSWERED_UNVERIFIED"
    assert sha256(original) not in json.dumps(summary)


def test_a_tcp_reply_and_observed_certificate_cannot_create_a_reference(certificates):
    original, _ = certificates
    assert review(reached(), observed_certificate_der=original)["status"] == "INDEPENDENT_REFERENCE_REQUIRED"
    assert review(reached(), reference_certificate_sha256=sha256(original))["status"] == "CERTIFICATE_OBSERVATION_REQUIRED"


def test_nonresponse_blocks_even_with_a_matching_certificate(certificates):
    original, _ = certificates
    summary = review(report_bytes(IPHONE), reference_certificate_sha256=sha256(original),
                     observed_certificate_der=original)
    assert summary["status"] == "NO_REPORTED_SERVICE_REPLY"
    assert summary["reported_outcome"] == "NO_SERVICE_RESPONSE"


def test_same_subject_and_key_do_not_make_a_changed_leaf_certificate_match(certificates):
    original, changed = certificates
    summary = review(reached(), reference_certificate_sha256=sha256(original), observed_certificate_der=changed)
    assert summary["status"] == "CERTIFICATE_REFERENCE_MISMATCH"


def test_different_or_reformatted_report_cannot_reuse_the_review_digest():
    original = reached()
    with pytest.raises(ValueError, match="^reviewed_report_mismatch$"):
        review_identity(original + b"\n", **IPHONE, expected_report_sha256=sha256(original))
    with pytest.raises(ValueError, match="^trial_build_mismatch$"):
        review_identity(original, **{**IPHONE, "expected_build": "14.2"}, expected_report_sha256=sha256(original))


@pytest.mark.parametrize("field", ["expected_report_sha256", "reference_certificate_sha256"])
@pytest.mark.parametrize("digest", ["f" * 63, "G" * 64, "a" * 64 + "\n"])
def test_invalid_digest_labels_are_rejected(field, digest):
    with pytest.raises(ValueError, match="invalid_.*sha256"):
        review(reached(), **{field: digest})


@pytest.mark.parametrize("transform", [lambda der: b"", lambda der: der[:-1], lambda der: der + b"\x00",
                                      lambda der: b"x" * (MAX_CERTIFICATE_BYTES + 1)])
def test_only_one_bounded_der_certificate_is_accepted(transform, certificates):
    malformed = transform(certificates[0])
    with pytest.raises(ValueError, match="^invalid_certificate$"):
        review(reached(), reference_certificate_sha256=sha256(malformed), observed_certificate_der=malformed)


def test_cli_reads_private_files_without_writing_or_echoing_identity_data(tmp_path, certificates):
    original, changed = certificates
    report = reached()
    report_file = tmp_path / "private-trial.txt"
    cert_file = tmp_path / "private-peer.der"
    report_file.write_bytes(report)
    cert_file.write_bytes(original)
    command = [sys.executable, str(SCRIPT), str(report_file), "--expected-platform", "iPhone/iPad",
               "--expected-version", "1.0.0", "--expected-build", "14.1", "--report-sha256", sha256(report),
               "--reference-certificate-sha256", sha256(original), "--observed-certificate", str(cert_file)]

    match = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(match.stdout)["status"] == "CERTIFICATE_BYTES_MATCH_UNVERIFIED"
    assert sha256(original) not in match.stdout and str(cert_file) not in match.stdout
    assert report_file.read_bytes() == report and cert_file.read_bytes() == original
    assert set(tmp_path.iterdir()) == {report_file, cert_file}

    cert_file.write_bytes(changed)
    mismatch = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert mismatch.returncode == 1
    assert json.loads(mismatch.stdout)["status"] == "CERTIFICATE_REFERENCE_MISMATCH"

    cert_file.unlink()
    cert_file.symlink_to(report_file)
    invalid = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert invalid.returncode == 2 and not invalid.stdout
    assert "INVALID_VIZIO_IDENTITY_REVIEW" in invalid.stderr
    assert "private-" not in invalid.stderr and sha256(original) not in invalid.stderr
