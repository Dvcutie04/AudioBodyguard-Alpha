import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError

def test_padded_semantic_fields_reject_before_candidate_construction(monkeypatch):
    import src.extensions.normalization as normalization

    calls=[]

    class ForbiddenCandidate:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("candidate construction must not occur")

    monkeypatch.setattr(normalization, "NormalizedCandidate", ForbiddenCandidate)

    cases=(
        {"extension_id":" aqss.test.tv.adapter"},
        {"target_id":"living_room_tv "},
        {"operation":" CONFIGURE"},
    )

    for override in cases:
        fields={
            "extension_id":"aqss.test.tv.adapter",
            "capability":"device.configuration.set",
            "target_id":"living_room_tv",
            "operation":"CONFIGURE",
            "parameters":{},
        }
        fields.update(override)
        proposal=ExtensionProposal(**fields)

        with pytest.raises(NormalizationAuthorityError):
            normalization.normalize_proposal(proposal)

    assert calls==[]
