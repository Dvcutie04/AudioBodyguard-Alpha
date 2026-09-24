import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_extension_id_requires_nonempty_dotted_segments():
    cases=(
        "aqss..adapter",
        ".aqss.adapter",
        "aqss.adapter.",
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
