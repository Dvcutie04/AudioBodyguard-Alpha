import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_non_mapping_top_level_parameters_fail_closed():
    payloads=(
        [],
        (),
        "signature",
        123,
        None,
    )

    for parameters in payloads:
        proposal=ExtensionProposal(
            extension_id="aqss.test.tv.adapter",
            capability="device.configuration.set",
            target_id="living_room_tv",
            operation="CONFIGURE",
            parameters=parameters,
        )

        with pytest.raises(NormalizationAuthorityError):
            normalize_proposal(proposal)
