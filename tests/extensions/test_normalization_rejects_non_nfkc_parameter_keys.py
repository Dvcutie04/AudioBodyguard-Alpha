import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_parameter_keys_that_change_under_nfkc_fail_closed():
    cases=(
        {"ｖｏｌｕｍｅ":10},
        {"ｍｏｄｅ":"eco"},
        {"outer":{"ｔａｒｇｅｔ":"living_room"}},
        {"items":[{"ｌｅｖｅｌ":5}]},
    )

    for parameters in cases:
        proposal=ExtensionProposal(
            extension_id="aqss.test.tv.adapter",
            capability="device.configuration.set",
            target_id="living_room_tv",
            operation="CONFIGURE",
            parameters=parameters,
        )

        with pytest.raises(NormalizationAuthorityError):
            normalize_proposal(proposal)
