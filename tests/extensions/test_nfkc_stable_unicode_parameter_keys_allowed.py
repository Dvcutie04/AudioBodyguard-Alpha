from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import normalize_proposal

def test_nfkc_stable_unicode_parameter_keys_are_allowed():
    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="device.configuration.set",
        target_id="living_room_tv",
        operation="CONFIGURE",
        parameters={"温度":22,"設定":"eco","nested":{"詳細":3}},
    )

    candidate=normalize_proposal(proposal)

    assert candidate.parameters["温度"]==22
    assert candidate.parameters["設定"]=="eco"
    assert candidate.parameters["nested"]["詳細"]==3
