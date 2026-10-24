"""Check a private N2b inventory and hashes of its local evidence files.

This reads records only. It does not discover hardware, play or record audio,
authenticate observations, authorize an adapter, or qualify an AQSS gate.
"""

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import stat


REQUIRED_SECTIONS = (
    "host", "output_route", "format", "capture", "ownership", "work",
    "continuity", "consent",
)
_TOP_KEYS = {
    "schema_version", "revision", "observed_on", "qualified",
    "production_ready", "sections", "evidence",
}
_SECTION_KEYS = {"status", "details", "evidence_refs"}
_EVIDENCE_KEYS = {"id", "path", "sha256"}
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_PLACEHOLDERS = {"", "unknown", "pending", "todo", "tbd", "not run", "example"}
_MAX_RECORD_BYTES = 128 * 1024
_MAX_EVIDENCE_BYTES = 1024 * 1024
_MAX_EVIDENCE_FILES = 32


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _shape(value, keys, label, invalid, incomplete):
    if not isinstance(value, dict):
        invalid.append(f"{label}: must be an object")
        return False
    if value.keys() - keys:
        invalid.append(f"{label}: unrecognized fields")
    for key in sorted(keys - value.keys()):
        incomplete.append(f"{label}.{key}: missing")
    return True


def _relative_path(value):
    # Records use ordinary relative POSIX paths, including on Windows.
    if not isinstance(value, str) or not value or len(value) > 1024:
        return False
    if "\\" in value or ":" in value or any(ord(char) < 32 for char in value):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def _check_file(root, relative, digest, label, invalid, incomplete):
    """Read one bounded regular file from an explicitly chosen stable directory."""
    try:
        path = root
        for part in relative.split("/"):
            path = path / part
            if path.is_symlink():
                invalid.append(f"{label}: symlink evidence is not accepted")
                return
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            invalid.append(f"{label}: file is outside evidence root")
            return
        # Check before open too, so a directory or FIFO is not treated as data.
        if not stat.S_ISREG(resolved.stat().st_mode):
            invalid.append(f"{label}: evidence must be a regular file")
            return
        with resolved.open("rb") as stream:
            content = stream.read(_MAX_EVIDENCE_BYTES + 1)
        if len(content) > _MAX_EVIDENCE_BYTES:
            invalid.append(f"{label}: evidence exceeds 1 MiB")
        elif hashlib.sha256(content).hexdigest() != digest:
            invalid.append(f"{label}: SHA-256 mismatch")
    except (OSError, ValueError, RuntimeError):
        incomplete.append(f"{label}: local evidence file is unavailable")


def assess(record, *, expected_revision=None, evidence_root=None):
    """Return (status, problems); even a complete record remains unverified."""
    invalid, incomplete = [], []
    if not _shape(record, _TOP_KEYS, "record", invalid, incomplete):
        return "INVALID_INVENTORY", invalid
    if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        invalid.append("schema_version: must be integer 1")
    revision = record.get("revision")
    if revision is None:
        incomplete.append("revision: not recorded")
    elif not _matches(_REVISION, revision):
        invalid.append("revision: must be an exact lowercase 40-character commit SHA")
    if expected_revision is not None:
        if not _matches(_REVISION, expected_revision):
            invalid.append("expected revision: must be an exact lowercase 40-character commit SHA")
        elif revision != expected_revision:
            incomplete.append("revision: does not match expected source revision")
    observed_on = record.get("observed_on")
    if observed_on is None:
        incomplete.append("observed_on: not recorded")
    else:
        try:
            if not _matches(_DATE, observed_on):
                raise ValueError
            date.fromisoformat(observed_on)
        except ValueError:
            invalid.append("observed_on: must be a valid YYYY-MM-DD date")
    for claim in ("qualified", "production_ready"):
        if record.get(claim) is not False:
            invalid.append(f"{claim}: inventory records must explicitly retain false")

    refs = set()
    sections = record.get("sections")
    if _shape(sections, set(REQUIRED_SECTIONS), "sections", invalid, incomplete):
        for name in REQUIRED_SECTIONS:
            label = f"sections.{name}"
            if name not in sections:
                incomplete.append(f"{label}: not recorded")
                continue
            section = sections[name]
            if not _shape(section, _SECTION_KEYS, label, invalid, incomplete):
                continue
            status = section.get("status")
            if status in ("unknown", "unavailable"):
                incomplete.append(f"{label}: {status}")
            elif status != "reported":
                invalid.append(f"{label}: status must be unknown, unavailable or reported")
            details = section.get("details")
            if details is not None and (not isinstance(details, str) or len(details) > 8192):
                invalid.append(f"{label}: details must be null or text up to 8192 characters")
            elif status == "reported" and (
                details is None or details.strip().lower() in _PLACEHOLDERS
            ):
                incomplete.append(f"{label}: observed details missing")
            section_refs = section.get("evidence_refs")
            if not isinstance(section_refs, list) or len(section_refs) > _MAX_EVIDENCE_FILES:
                invalid.append(f"{label}: evidence_refs must be a list of at most 32 IDs")
            elif any(not _matches(_ID, ref) for ref in section_refs):
                invalid.append(f"{label}: evidence_refs contain an invalid ID")
            else:
                if len(set(section_refs)) != len(section_refs):
                    invalid.append(f"{label}: duplicate evidence reference")
                refs.update(section_refs)
                if status == "reported" and not section_refs:
                    incomplete.append(f"{label}: evidence reference missing")

    evidence = record.get("evidence")
    entries = {}
    paths = set()
    if not isinstance(evidence, list) or len(evidence) > _MAX_EVIDENCE_FILES:
        invalid.append("evidence: must be a list of at most 32 files")
    else:
        for index, entry in enumerate(evidence):
            label = f"evidence[{index}]"
            if not _shape(entry, _EVIDENCE_KEYS, label, invalid, incomplete):
                continue
            identity, path, digest = (entry.get(key) for key in ("id", "path", "sha256"))
            if not _matches(_ID, identity):
                invalid.append(f"{label}: invalid evidence ID")
                continue
            if identity in entries:
                invalid.append(f"{label}: duplicate evidence ID")
                continue
            entries[identity] = (path, digest, label)
            if not _relative_path(path):
                invalid.append(f"{label}: invalid relative evidence path")
            elif path in paths:
                invalid.append(f"{label}: duplicate evidence path")
            else:
                paths.add(path)
            if not _matches(_DIGEST, digest):
                invalid.append(f"{label}: SHA-256 must be a lowercase 64-character digest")
        if refs - entries.keys():
            incomplete.append("evidence: referenced files are not registered")
        if entries.keys() - refs:
            invalid.append("evidence: unreferenced files are not accepted")

    root = None
    if evidence_root is None:
        incomplete.append("evidence: choose the private evidence root to check local files")
    else:
        try:
            root = Path(evidence_root).resolve(strict=True)
            if not root.is_dir():
                raise ValueError
        except (OSError, ValueError, TypeError, RuntimeError):
            incomplete.append("evidence: private evidence root is unavailable")
            root = None
    if root is not None and not invalid:
        for path, digest, label in entries.values():
            _check_file(root, path, digest, label, invalid, incomplete)
    if invalid:
        return "INVALID_INVENTORY", invalid + incomplete
    if incomplete:
        return "INCOMPLETE_INVENTORY", incomplete
    return "INVENTORY_RECORDED_UNVERIFIED", []


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-finite JSON constant")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="Private JSON inventory record")
    parser.add_argument("--evidence-root", type=Path, help="Private directory of stable, redacted evidence files")
    parser.add_argument("--expected-revision", help="Exact source SHA for this inventory")
    args = parser.parse_args()
    try:
        if not args.record.is_file():
            raise ValueError("not a regular record file")
        with args.record.open("rb") as stream:
            raw = stream.read(_MAX_RECORD_BYTES + 1)
        if len(raw) > _MAX_RECORD_BYTES:
            raise ValueError("record exceeds bound")
        record = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (OSError, ValueError, RecursionError):
        print("INVALID_INVENTORY\n- Cannot read a unique-key UTF-8 JSON record within 128 KiB.")
        return 2
    status, problems = assess(
        record, expected_revision=args.expected_revision, evidence_root=args.evidence_root,
    )
    print(status)
    for problem in problems:
        print(f"- {problem}")
    print("N2b–N5 remain pending. File hashes do not authenticate hardware observations.")
    return {"INVENTORY_RECORDED_UNVERIFIED": 0, "INCOMPLETE_INVENTORY": 1, "INVALID_INVENTORY": 2}[status]


if __name__ == "__main__":
    raise SystemExit(main())
