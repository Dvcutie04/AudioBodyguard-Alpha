import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_unicode_confusable_authority_keys_fail_closed():
    cases=(
        {"ＳＩＧＮＡＴＵＲＥ":"forged"},
        {"ｌｅａｓｅ＿ｉｄ":"forged"},
        {"ｉｓｓｕｅｒ＿ｉｄ":"forged"},
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
