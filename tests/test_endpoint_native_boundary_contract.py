from copy import deepcopy
import json
from pathlib import Path


CONTRACT = Path(__file__).resolve().parents[1] / "contracts/endpoint_native_boundary_v1.json"


def _synthetic_conformance_eligible(trace):
    """Test-only trace oracle; never a production retirement certificate."""
    claim, activation, submission = (trace[key] for key in ("claim", "activation", "submission"))
    native = trace["native"]
    if claim != activation or claim != submission:
        return False
    if any(value is not True for value in trace["protection"].values()):
        return False
    required = ("backend_qualified", "registry_complete", "evidence_authorized", "history_authenticated", "route_enforced", "cut_closed", "admission_closed", "publication_closed")
    if any(native[key] is not True for key in required):
        return False
    times = trace["times"]
    if not (times["issued_at"] <= times["activation_at"] < times["expires_at"] and times["activation_at"] <= times["submission_at"] < times["expires_at"]):
        return False
    if native["output_disposition"] not in ("completed", "discarded"):
        return False
    if not set(native["retained_generations"]).issubset(native["closed_generations"]):
        return False
    if any(item["generation"] <= native["retired_through_generation"] and item["settled"] is not True for item in native["work"]):
        return False
    return native["actual_route_id"] == claim["route_id"] and native["actual_route_epoch"] == claim["route_epoch"]


def test_shared_native_boundary_adversarial_vectors():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["profile_id"] == "AQSS/owned-pcm-gain-lab/v1"
    assert data["capability"] == "test_only_trace_conformance"
    cases = data["cases"]
    assert len(cases) == 18
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["eligible"] for case in cases} == {True, False}
    for case in cases:
        trace = deepcopy(data["baseline"])
        for section, changes in case["changes"].items():
            trace[section].update(changes)
        assert _synthetic_conformance_eligible(trace) is case["eligible"], case["id"]
