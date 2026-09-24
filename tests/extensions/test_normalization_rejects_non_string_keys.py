import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_non_string_parameter_keys_fail_closed():
    keys=(
        b"signature",
        123,
        ("policy_digest",),
    )

    for key in keys:
        proposal=ExtensionProposal(
            extension_id="aqss.test.tv.adapter",
            capability="device.configuration.set",
            target_id="living_room_tv",
            operation="CONFIGURE",
            parameters={key:"smuggled"},
        )

        with pytest.raises(NormalizationAuthorityError):
            normalize_proposal(proposal)
