from dataclasses import fields
import pytest

def test_extension_proposal_is_declarative_and_has_no_authority():
    from src.extensions.proposal import ExtensionProposal
    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="audio.volume.set",
        target_id="living_room_tv",
        operation="SET_VOLUME",
        parameters={"volume":25},
    )
    names={f.name for f in fields(proposal)}
    forbidden={
        "authorized",
        "authorization_digest",
        "capability_lease",
        "capability_lease_digest",
        "lease_id",
        "signature",
        "issuer_id",
        "commit",
        "actuate",
        "physical_authority",
    }
    assert names.isdisjoint(forbidden)
    assert proposal.extension_id=="aqss.test.tv.adapter"
    assert proposal.operation=="SET_VOLUME"

def test_extension_proposal_is_immutable():
    from src.extensions.proposal import ExtensionProposal
    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="audio.volume.set",
        target_id="living_room_tv",
        operation="SET_VOLUME",
        parameters={"volume":25},
    )
    with pytest.raises(Exception):
        proposal.operation="POWER_OFF"
