import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_extension_id_segments_reject_invalid_characters():
    cases=(
        "aqss.test adapter",
        "aqss.test@adapter",
        "aqss.test/adapter",
        "aqss.test:adapter",
    )

    for extension_id in cases:
        proposal=ExtensionProposal(
            extension_id=extension_id,
            capability="device.configuration.set",
            target_id="living_room_tv",
            operation="CONFIGURE",
            parameters={"volume":10},
        )

        with pytest.raises(NormalizationAuthorityError):
            normalize_proposal(proposal)
