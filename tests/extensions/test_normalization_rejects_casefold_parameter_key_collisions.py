import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_parameter_key_casefold_collisions_fail_closed():
    cases=(
        {"Mode":"eco","mode":"sport"},
        {"VOLUME":10,"volume":20},
        {"outer":{"Target":"a","target":"b"}},
        {"items":[{"Level":1,"level":2}]},
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
