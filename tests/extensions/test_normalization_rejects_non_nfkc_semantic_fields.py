import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_semantic_fields_that_change_under_nfkc_fail_closed():
    cases=(
        {"extension_id":"ａｑｓｓ.test.tv.adapter","target_id":"living_room_tv","operation":"CONFIGURE"},
        {"extension_id":"aqss.test.tv.adapter","target_id":"ｌｉｖｉｎｇ_room_tv","operation":"CONFIGURE"},
        {"extension_id":"aqss.test.tv.adapter","target_id":"living_room_tv","operation":"ＣＯＮＦＩＧＵＲＥ"},
    )

    for case in cases:
        proposal=ExtensionProposal(
            extension_id=case["extension_id"],
            capability="device.configuration.set",
            target_id=case["target_id"],
            operation=case["operation"],
            parameters={"volume":10},
        )

        with pytest.raises(NormalizationAuthorityError):
            normalize_proposal(proposal)
