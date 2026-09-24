import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError

def test_noncanonical_semantic_case_rejects_before_candidate_construction(monkeypatch):
    import src.extensions.normalization as normalization

    calls=[]

    class ForbiddenCandidate:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("candidate construction must not occur")

    monkeypatch.setattr(normalization, "NormalizedCandidate", ForbiddenCandidate)

    proposal=ExtensionProposal(
        extension_id="AQSS.TEST.TV.ADAPTER",
        capability="device.configuration.set",
        target_id="living_room_tv",
        operation="CONFIGURE",
        parameters={"volume":10},
    )

    with pytest.raises(NormalizationAuthorityError):
        normalization.normalize_proposal(proposal)

    assert calls==[]
