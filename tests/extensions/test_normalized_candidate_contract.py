from dataclasses import fields
import pytest

def test_normalized_candidate_contains_request_semantics_but_no_authority():
    from src.extensions.normalization import NormalizedCandidate
    candidate=NormalizedCandidate(
        extension_id="aqss.test.tv.adapter",
        target_id="living_room_tv",
        operation="SET_VOLUME",
        parameters={"volume":25},
    )
    names={f.name for f in fields(candidate)}
    assert {"extension_id","target_id","operation","parameters"}.issubset(names)
    forbidden={
        "device_id",
        "issuer_id",
        "policy_digest",
        "capability_lease_digest",
        "lease_id",
        "signature",
        "authorization_digest",
        "transaction_id",
        "commit_authority",
        "physical_authority",
    }
    assert names.isdisjoint(forbidden)

def test_normalized_candidate_parameters_are_immutable():
    from src.extensions.normalization import NormalizedCandidate
    candidate=NormalizedCandidate(
        extension_id="aqss.test.tv.adapter",
        target_id="living_room_tv",
        operation="SET_VOLUME",
        parameters={"audio":{"volume":25}},
    )
    with pytest.raises(TypeError):
        candidate.parameters["audio"]["volume"]=100
