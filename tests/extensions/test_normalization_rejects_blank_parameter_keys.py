import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_blank_or_whitespace_only_parameter_keys_fail_closed():
    cases=(
        {"":"value"},
        {"   ":"value"},
        {"outer":{"":"nested"}},
        {"items":[{"   ":"nested"}]},
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
