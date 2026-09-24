import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_parameter_keys_with_surrounding_whitespace_fail_closed():
    cases=(
        {" volume":"10"},
        {"mode ":"eco"},
        {" target ":"living_room"},
        {"outer":{" nested ":"value"}},
        {"items":[{" padded ":"value"}]},
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
