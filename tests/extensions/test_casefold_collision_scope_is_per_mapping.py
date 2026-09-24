from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import normalize_proposal

def test_casefold_collision_scope_is_per_mapping():
    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="device.configuration.set",
        target_id="living_room_tv",
        operation="CONFIGURE",
        parameters={
            "left":{"Mode":"eco"},
            "right":{"mode":"sport"},
        },
    )

    candidate=normalize_proposal(proposal)

    assert candidate.parameters["left"]["Mode"]=="eco"
    assert candidate.parameters["right"]["mode"]=="sport"
