import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError

def test_authority_smuggling_rejection_emits_no_candidate(monkeypatch):
    import src.extensions.normalization as normalization

    calls=[]

    class ForbiddenCandidate:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("NormalizedCandidate must not be constructed after rejection")

    monkeypatch.setattr(normalization, "NormalizedCandidate", ForbiddenCandidate)

    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="device.configuration.set",
        target_id="living_room_tv",
        operation="CONFIGURE",
        parameters={
            "audio":{
                "volume":25,
                "metadata":{"authorization_digest":"smuggled"},
            },
        },
    )

    with pytest.raises(NormalizationAuthorityError):
        normalization.normalize_proposal(proposal)

    assert calls==[]

def test_every_reserved_authority_field_rejects_before_candidate_construction(monkeypatch):
    import src.extensions.normalization as normalization

    calls=[]

    class ForbiddenCandidate:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("candidate construction must not occur")

    monkeypatch.setattr(normalization, "NormalizedCandidate", ForbiddenCandidate)

    forbidden_keys=(
        "signature",
        "lease_id",
        "capability_lease_digest",
        "authorization_digest",
        "issuer_id",
        "policy_digest",
        "transaction_id",
    )

    for key in forbidden_keys:
        proposal=ExtensionProposal(
            extension_id="aqss.test.tv.adapter",
            capability="device.configuration.set",
            target_id="living_room_tv",
            operation="CONFIGURE",
            parameters={"safe":True,key:"smuggled"},
        )

        with pytest.raises(NormalizationAuthorityError):
            normalization.normalize_proposal(proposal)

    assert calls==[]
