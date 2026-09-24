from src.extensions.proposal import ExtensionProposal

def test_extension_proposal_normalizes_to_authority_free_candidate():
    from src.extensions.normalization import normalize_proposal
    proposal=ExtensionProposal(
        extension_id="aqss.test.tv.adapter",
        capability="audio.volume.set",
        target_id="living_room_tv",
        operation="SET_VOLUME",
        parameters={"volume":25},
    )
    candidate=normalize_proposal(proposal)
    assert candidate.extension_id==proposal.extension_id
    assert candidate.target_id==proposal.target_id
    assert candidate.operation==proposal.operation
    assert candidate.parameters==proposal.parameters
    assert not hasattr(candidate,"capability")
    assert not hasattr(candidate,"issuer_id")
    assert not hasattr(candidate,"signature")
    assert not hasattr(candidate,"capability_lease_digest")
    assert not hasattr(candidate,"authorization_digest")
