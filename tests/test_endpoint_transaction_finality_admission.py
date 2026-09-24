def test_endpoint_finality_admission_requires_verified_fresh_bound_proof():
    from dataclasses import replace
    import pytest
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec,utils
    from src.device_fabric.endpoint_transaction_finality_admission import admit_endpoint_finality_assertion
    from src.device_fabric.endpoint_transaction_finality_authority import EndpointFinalityTrustedKey,EndpointFinalityAuthoritySnapshot,AuthorityVerifiedEndpointFinalityEnvelope
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_cose_sign1,encode_endpoint_finality_signing_input,compute_endpoint_finality_proof_digest
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision,EndpointTransactionState
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    private_key=ec.derive_private_key(1,ec.SECP256R1())
    def signed(current_claims):
        signing_input=encode_endpoint_finality_signing_input(claims=current_claims,kid=b"k",namespace=b"n")
        r,s=utils.decode_dss_signature(private_key.sign(signing_input,ec.ECDSA(hashes.SHA256())))
        return encode_endpoint_finality_cose_sign1(claims=current_claims,kid=b"k",signature=r.to_bytes(32,"big")+s.to_bytes(32,"big"))
    trusted=EndpointFinalityTrustedKey(kid=b"k",namespace=b"n",issuer_id="i",audience="a",device_id="d",authority_epoch=1,public_key=private_key.public_key())
    context=dict(wire=signed(claims),trust=EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=(trusted,)),device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,audience="a",issuer_id="i",authority_epoch=1,now=1,current_state=EndpointTransactionState.UNKNOWN,previous_proof_digest=None)
    admitted=admit_endpoint_finality_assertion(**context)
    assert type(admitted.verified) is AuthorityVerifiedEndpointFinalityEnvelope
    assert admitted.accepted_result.claims==claims
    assert admitted.accepted_result.result_state is EndpointTransactionState.NOT_APPLIED
    assert admitted.accepted_result.accepted_at==1
    assert admitted.proof_digest==compute_endpoint_finality_proof_digest(claims=claims,kid=b"k",namespace=b"n")
    for changes in (dict(now=2),dict(transaction_id="other"),dict(current_state=EndpointTransactionState.APPLIED),dict(previous_proof_digest="other"),dict(wire=signed(replace(claims,device_id="other")))):
        with pytest.raises(ValueError):
            admit_endpoint_finality_assertion(**{**context,**changes})
