import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError

def test_normalization_rejects_authority_smuggling_in_parameters():
    from src.extensions.normalization import normalize_proposal

    forbidden_keys=(
        "signature",
        "lease_id",
        "capability_lease_digest",
        "authorization_digest",
        "issuer_id",
        "policy_digest",
        "transaction_id",
        "expected_pre_state_digest",
    )

    for key in forbidden_keys:
        proposal=ExtensionProposal(
            extension_id="aqss.test.tv.adapter",
            capability="audio.volume.set",
            target_id="living_room_tv",
            operation="SET_VOLUME",
            parameters={"volume":25,key:"smuggled"},
        )
        with pytest.raises(NormalizationAuthorityError):
            normalize_proposal(proposal)

def test_normalization_rejects_nested_authority_smuggling():
    from src.extensions.normalization import normalize_proposal

    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="device.configuration.set",
        target_id="living_room_tv",
        operation="CONFIGURE",
        parameters={
            "audio":{
                "volume":25,
                "metadata":{
                    "authorization_digest":"smuggled"
                },
            },
        },
    )

    with pytest.raises(NormalizationAuthorityError):
        normalize_proposal(proposal)
