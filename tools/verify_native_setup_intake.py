"""Verify the engineering intake CLI against text captured by native UI checks.

All source/build labels are explicitly supplied by the test harness. This binds
test artifacts to expected labels; it does not authenticate a phone or hardware.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys


def verify_native_setup_intake(source_file, output_directory, *, platform, version, build, source_revision):
    source, output = Path(source_file), Path(output_directory)
    tools = Path(__file__).resolve().parent
    original = source.read_bytes()
    created = subprocess.run([
        sys.executable, str(tools / "mobile_setup_intake.py"), str(source),
        "--output-dir", str(output), "--expected-platform", platform,
        "--expected-version", version, "--expected-build", build,
        "--source-revision", source_revision,
    ], capture_output=True, text=True, check=True)
    assert created.stdout.startswith("PHONE_REPORT_RECORDED_UNVERIFIED\n")
    assert (output / "phone-report.txt").read_bytes() == original, "Intake changed the native shared source"
    summary = json.loads((output / "intake.json").read_text())
    inventory = json.loads((output / "inventory.json").read_text())
    digest = hashlib.sha256(original).hexdigest()
    assert summary["source_sha256"] == digest and summary["source_size_bytes"] == len(original)
    assert summary["source_revision"] == source_revision and summary["source_authentication"] == "Not established"
    assert summary["qualified"] is summary["production_ready"] is False
    assert inventory["qualified"] is inventory["production_ready"] is False
    assert inventory["observed_on"] is None and len(inventory["sections"]) == 8
    assert all(row["status"] == "unknown" for row in inventory["sections"].values())
    assessed = subprocess.run([
        sys.executable, str(tools / "n2b_inventory_record.py"), str(output / "inventory.json"),
        "--evidence-root", str(output), "--expected-revision", source_revision,
    ], capture_output=True, text=True, check=False)
    assert assessed.returncode == 1 and assessed.stdout.startswith("INCOMPLETE_INVENTORY\n"), assessed.stdout
    return {"intake_status": "PHONE_REPORT_RECORDED_UNVERIFIED", "inventory_status": "INCOMPLETE_INVENTORY",
            "source_sha256": digest, "source_bytes": len(original), "declared_source_revision": source_revision,
            "scope": "Native UI test text and engineering CLI only; no owner phone or physical qualification"}
