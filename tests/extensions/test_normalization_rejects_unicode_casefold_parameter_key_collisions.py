import pytest

from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import NormalizationAuthorityError, normalize_proposal

def test_unicode_casefold_parameter_key_collisions_fail_closed():
    cases=(
        {"Straße":1,"STRASSE":2},
        {"outer":{"Maße":1,"MASSE":2}},
        {"items":[{"Straße":"a","strasse":"b"}]},
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
