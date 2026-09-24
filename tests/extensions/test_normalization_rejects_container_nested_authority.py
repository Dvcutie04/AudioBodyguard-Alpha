import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_authority_smuggling_inside_sequence_containers_fails_closed():
    payloads=(
        {"items":[{"signature":"smuggled"}]},
        {"items":({"lease_id":"smuggled"},)},
        {"items":[{"nested":{"policy_digest":"smuggled"}}]},
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
