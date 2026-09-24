import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_blank_semantic_fields_fail_closed():
    cases=(
        {"extension_id":""},
        {"extension_id":"   "},
        {"target_id":""},
        {"target_id":"   "},
        {"operation":""},
        {"operation":"   "},
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
            normalize_proposal(proposal)
