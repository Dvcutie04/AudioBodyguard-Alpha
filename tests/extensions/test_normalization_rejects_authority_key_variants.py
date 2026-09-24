import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_authority_key_case_and_whitespace_variants_fail_closed():
    keys=(
        "SIGNATURE",
        " signature ",
        "Lease_ID",
        " POLICY_DIGEST ",
        "Authorization_Digest",
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
