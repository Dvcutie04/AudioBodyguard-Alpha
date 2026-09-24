import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_extension_id_and_operation_require_canonical_case():
    cases=(
        {"extension_id":"AQSS.TEST.TV.ADAPTER","operation":"CONFIGURE"},
        {"extension_id":"aqss.test.tv.adapter","operation":"configure"},
        {"extension_id":"Aqss.Test.Tv.Adapter","operation":"Configure"},
    )

    for case in cases:
        proposal=ExtensionProposal(
            extension_id=case["extension_id"],
            capability="device.configuration.set",
            target_id="living_room_tv",
            operation=case["operation"],
            parameters={"volume":10},
        )

        with pytest.raises(NormalizationAuthorityError):
            normalize_proposal(proposal)
