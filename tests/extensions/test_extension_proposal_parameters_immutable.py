import pytest

from src.extensions.proposal import ExtensionProposal

def test_extension_proposal_parameters_cannot_change_after_creation():
    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="audio.volume.set",
        target_id="living_room_tv",
        operation="SET_VOLUME",
        parameters={"volume":25},
    )
    with pytest.raises(TypeError):
        proposal.parameters["volume"]=100
    assert proposal.parameters["volume"]==25

def test_nested_extension_proposal_parameters_are_recursively_immutable():
    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="device.configuration.set",
        target_id="living_room_tv",
        operation="CONFIGURE",
        parameters={
            "audio":{"volume":25,"modes":["night","dialog"]},
            "zones":{"living_room","kitchen"},
        },
    )
    with pytest.raises(TypeError):
        proposal.parameters["audio"]["volume"]=100
    with pytest.raises(TypeError):
        proposal.parameters["audio"]["modes"][0]="tampered"
    with pytest.raises(AttributeError):
        proposal.parameters["zones"].add("bedroom")
    assert proposal.parameters["audio"]["volume"]==25
    assert proposal.parameters["audio"]["modes"]==("night","dialog")
    assert proposal.parameters["zones"]==frozenset({"living_room","kitchen"})
