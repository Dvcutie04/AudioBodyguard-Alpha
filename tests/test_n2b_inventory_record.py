"""Synthetic inventory records never establish output qualification."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.n2b_inventory_record import assess, REQUIRED_SECTIONS


ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40


def _inventory(tmp_path):
    evidence = b"Synthetic test data only; no hardware was inspected.\n"
    (tmp_path / "observations.txt").write_bytes(evidence)
    return {
        "schema_version": 1,
        "revision": REVISION,
        "observed_on": "2026-10-24",
        "qualified": False,
        "production_ready": False,
        "sections": {
            name: {
                "status": "reported",
                "details": "Synthetic section description for validator testing.",
                "evidence_refs": ["observations"],
            }
            for name in REQUIRED_SECTIONS
        },
        "evidence": [{
            "id": "observations", "path": "observations.txt",
            "sha256": hashlib.sha256(evidence).hexdigest(),
        }],
    }


def _cli(tmp_path, record, *extra):
    record_path = tmp_path / "inventory.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(ROOT / "tools/n2b_inventory_record.py"),
         str(record_path), "--evidence-root", str(tmp_path), *extra],
        text=True, capture_output=True, check=False,
    )


def test_complete_inventory_remains_unverified_and_does_not_mutate_record(tmp_path):
    record = _inventory(tmp_path)
    before = deepcopy(record)
    assert assess(record, expected_revision=REVISION, evidence_root=tmp_path) == (
        "INVENTORY_RECORDED_UNVERIFIED", []
    )
    assert record == before


def test_unfilled_repository_template_names_every_missing_section(tmp_path):
    record = json.loads((ROOT / "docs/n2b-inventory.template.json").read_text())
    status, problems = assess(record, evidence_root=tmp_path)
    assert status == "INCOMPLETE_INVENTORY"
    for name in REQUIRED_SECTIONS:
        assert any(f"sections.{name}:" in problem for problem in problems)
    assert record["qualified"] is False
    assert record["production_ready"] is False


@pytest.mark.parametrize("section", [
    "host", "output_route", "format", "capture", "ownership", "work",
    "continuity", "consent",
])
@pytest.mark.parametrize("status", ["unknown", "unavailable"])
def test_missing_equipment_or_observations_cannot_complete_inventory(tmp_path, section, status):
    record = _inventory(tmp_path)
    record["sections"][section] = {
        "status": status, "details": None, "evidence_refs": [],
    }
    result, problems = assess(record, evidence_root=tmp_path)
    assert result == "INCOMPLETE_INVENTORY"
    assert any(f"sections.{section}:" in problem for problem in problems)


@pytest.mark.parametrize("details", [None, "", "  ", "UNKNOWN", "pending", "TBD", "todo", "not run"])
def test_placeholder_description_is_not_a_reported_observation(tmp_path, details):
    record = _inventory(tmp_path)
    record["sections"]["capture"]["details"] = details
    assert assess(record, evidence_root=tmp_path)[0] == "INCOMPLETE_INVENTORY"


@pytest.mark.parametrize("claim", ["qualified", "production_ready"])
@pytest.mark.parametrize("value", [True, 0, None, "false"])
def test_positive_or_ambiguous_qualification_claim_overrides_missing_fields(tmp_path, claim, value):
    record = _inventory(tmp_path)
    record[claim] = value
    record["sections"] = {}
    status, problems = assess(record, evidence_root=tmp_path)
    assert status == "INVALID_INVENTORY"
    assert any(claim in problem for problem in problems)


def test_evidence_requires_real_bytes_and_remains_incomplete_when_absent(tmp_path):
    record = _inventory(tmp_path)
    assert assess(record)[0] == "INCOMPLETE_INVENTORY"
    (tmp_path / "observations.txt").unlink()
    status, problems = assess(record, evidence_root=tmp_path)
    assert status == "INCOMPLETE_INVENTORY"
    assert any("evidence[0]" in problem for problem in problems)


def test_changed_evidence_is_invalid_even_with_matching_record_revision(tmp_path):
    record = _inventory(tmp_path)
    (tmp_path / "observations.txt").write_bytes(b"Changed evidence\n")
    status, problems = assess(record, expected_revision=REVISION, evidence_root=tmp_path)
    assert status == "INVALID_INVENTORY"
    assert any("SHA-256 mismatch" in problem for problem in problems)


@pytest.mark.parametrize("path", ["../outside.txt", "/tmp/outside.txt", "https://example.com/evidence", "folder\\outside.txt", "folder/../observations.txt", "./observations.txt", ""])
def test_unsafe_evidence_paths_are_rejected(tmp_path, path):
    record = _inventory(tmp_path)
    record["evidence"][0]["path"] = path
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"


def test_symlink_and_directory_evidence_are_rejected(tmp_path):
    record = _inventory(tmp_path)
    (tmp_path / "alias.txt").symlink_to(tmp_path / "observations.txt")
    record["evidence"][0]["path"] = "alias.txt"
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "alias").symlink_to(tmp_path, target_is_directory=True)
    record["evidence"][0]["path"] = "nested/alias/observations.txt"
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"
    record["evidence"][0]["path"] = "nested"
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"


def test_evidence_can_use_an_ordinary_nested_private_file(tmp_path):
    record = _inventory(tmp_path)
    (tmp_path / "redacted").mkdir()
    (tmp_path / "observations.txt").rename(tmp_path / "redacted" / "observations.txt")
    record["evidence"][0]["path"] = "redacted/observations.txt"
    assert assess(record, evidence_root=tmp_path)[0] == "INVENTORY_RECORDED_UNVERIFIED"


def test_unused_duplicate_or_unresolved_evidence_is_not_silently_accepted(tmp_path):
    record = _inventory(tmp_path)
    record["evidence"].append(deepcopy(record["evidence"][0]))
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"
    record = _inventory(tmp_path)
    record["sections"]["capture"]["evidence_refs"] = ["missing"]
    assert assess(record, evidence_root=tmp_path)[0] == "INCOMPLETE_INVENTORY"
    record = _inventory(tmp_path)
    unused = deepcopy(record["evidence"][0])
    unused.update(id="unused", path="unused.txt")
    record["evidence"].append(unused)
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"


@pytest.mark.parametrize("revision", [None, "main", "a" * 39, "A" * 40, "b" * 40])
def test_source_is_exact_and_bound_to_expected_revision(tmp_path, revision):
    record = _inventory(tmp_path)
    record["revision"] = revision
    assert assess(record, expected_revision=REVISION, evidence_root=tmp_path)[0] != "INVENTORY_RECORDED_UNVERIFIED"


@pytest.mark.parametrize("date", [None, "tomorrow", "2026-02-30", "2026-1-2", "2026-10-24T00:00:00Z"])
def test_inventory_date_must_be_a_complete_valid_calendar_date(tmp_path, date):
    record = _inventory(tmp_path)
    record["observed_on"] = date
    assert assess(record, evidence_root=tmp_path)[0] != "INVENTORY_RECORDED_UNVERIFIED"


@pytest.mark.parametrize("replacement", [None, [], True, "record"])
def test_malformed_top_level_records_do_not_crash(tmp_path, replacement):
    assert assess(replacement, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"


@pytest.mark.parametrize("location,value", [
    ("schema_version", True), ("schema_version", 2),
    ("sections", []), ("evidence", {}), ("evidence", [None]),
])
def test_malformed_structure_does_not_crash_or_complete(tmp_path, location, value):
    record = _inventory(tmp_path)
    record[location] = value
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"


def test_unknown_fields_and_bad_section_shapes_are_rejected(tmp_path):
    record = _inventory(tmp_path)
    record["adapter_authorized"] = True
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"
    record = _inventory(tmp_path)
    record["sections"]["capture"] = []
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"
    record = _inventory(tmp_path)
    record["sections"]["capture"]["evidence_refs"] = [{}]
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"


def test_cli_reports_only_unverified_status_and_never_echoes_inventory_values(tmp_path):
    record = _inventory(tmp_path)
    record["sections"]["host"]["details"] = "Private host description must stay in the record"
    result = _cli(tmp_path, record, "--expected-revision", REVISION)
    assert result.returncode == 0
    assert result.stdout.splitlines()[0] == "INVENTORY_RECORDED_UNVERIFIED"
    assert "N2b–N5 remain pending" in result.stdout
    assert "Private host" not in result.stdout + result.stderr
    assert result.stderr == ""


def test_cli_rejects_duplicate_json_keys_and_invalid_expected_revision(tmp_path):
    record = _inventory(tmp_path)
    path = tmp_path / "duplicate.json"
    path.write_text('{"qualified": true,"qualified":false}', encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/n2b_inventory_record.py"), str(path)],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 2
    assert "INVALID_INVENTORY" in result.stdout
    result = _cli(tmp_path, record, "--expected-revision", "main")
    assert result.returncode == 2


def test_cli_and_evidence_reads_are_bounded(tmp_path):
    record = _inventory(tmp_path)
    (tmp_path / "observations.txt").write_bytes(b"x" * (1024 * 1024 + 1))
    assert assess(record, evidence_root=tmp_path)[0] == "INVALID_INVENTORY"
    path = tmp_path / "oversized.json"
    path.write_bytes(b" " * (128 * 1024 + 1))
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/n2b_inventory_record.py"), str(path)],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 2
    assert result.stdout.splitlines()[0] == "INVALID_INVENTORY"
    assert "Traceback" not in result.stderr
