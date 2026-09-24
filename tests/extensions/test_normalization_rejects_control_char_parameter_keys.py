import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_control_characters_in_parameter_keys_fail_closed():
    cases=(
        {"device\nmode":"eco"},
        {"volume\tlevel":10},
        {"tar\x00get":"living_room"},
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
