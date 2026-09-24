def test_endpoint_finality_authority_binds_trusted_key_and_active_epoch():
    from dataclasses import replace
    import pytest
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec,utils
    from src.device_fabric.endpoint_transaction_finality_authority import EndpointFinalityTrustedKey,EndpointFinalityAuthoritySnapshot,AuthorityVerifiedEndpointFinalityEnvelope,verify_endpoint_finality_with_authority
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_cose_sign1,encode_endpoint_finality_signing_input
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    private_key=ec.derive_private_key(1,ec.SECP256R1())
    def signed(current_claims,kid=b"k",signer=private_key):
        signing_input=encode_endpoint_finality_signing_input(claims=current_claims,kid=kid,namespace=b"n")
        r,s=utils.decode_dss_signature(signer.sign(signing_input,ec.ECDSA(hashes.SHA256())))
        return encode_endpoint_finality_cose_sign1(claims=current_claims,kid=kid,signature=r.to_bytes(32,"big")+s.to_bytes(32,"big"))
    trusted=EndpointFinalityTrustedKey(kid=b"k",namespace=b"n",issuer_id="i",audience="a",device_id="d",authority_epoch=1,public_key=private_key.public_key())
    snapshot=EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=(trusted,))
    verified=verify_endpoint_finality_with_authority(wire=signed(claims),trust=snapshot,issuer_id="i",audience="a",device_id="d",authority_epoch=1)
    assert type(verified) is AuthorityVerifiedEndpointFinalityEnvelope
    assert verified.trusted_key is trusted
    assert verified.active_authority_epoch==1
    with pytest.raises(TypeError,match="requires authority verification"):
        AuthorityVerifiedEndpointFinalityEnvelope()
    assert verified.claims==claims
    assert verified.kid==b"k"
    assert verified.namespace==b"n"
    failures=((signed(replace(claims,issuer_id="other")),snapshot),(signed(replace(claims,device_id="other")),snapshot),(signed(replace(claims,audience="other")),snapshot),(signed(replace(claims,authority_epoch=2)),snapshot),(signed(claims,kid=b"j"),snapshot),(signed(claims,signer=ec.derive_private_key(2,ec.SECP256R1())),snapshot),(signed(claims),replace(snapshot,active_authority_epoch=2)),(signed(claims),replace(snapshot,keys=(replace(trusted,namespace=b"m"),))))
    for candidate,current_trust in failures:
        with pytest.raises(ValueError):
            verify_endpoint_finality_with_authority(wire=candidate,trust=current_trust,issuer_id="i",audience="a",device_id="d",authority_epoch=1)


def test_endpoint_finality_authority_snapshot_rejects_ambiguous_keys():
    from dataclasses import replace
    import pytest
    from cryptography.hazmat.primitives.asymmetric import ec
    from src.device_fabric.endpoint_transaction_finality_authority import EndpointFinalityTrustedKey,EndpointFinalityAuthoritySnapshot
    key=ec.derive_private_key(1,ec.SECP256R1()).public_key()
    trusted=EndpointFinalityTrustedKey(kid=b"k",namespace=b"n",issuer_id="i",audience="a",device_id="d",authority_epoch=1,public_key=key)
    other_key=ec.derive_private_key(2,ec.SECP256R1()).public_key()
    for duplicate in (trusted,replace(trusted,namespace=b"m"),replace(trusted,public_key=other_key)):
        with pytest.raises(ValueError,match="duplicate finality trusted key identity"):
            EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=(trusted,duplicate))
    for invalid_keys in ((),[trusted],(trusted,)*65,(trusted,None)):
        with pytest.raises(ValueError,match="finality trusted keys are invalid"):
            EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=invalid_keys)
    for bad_epoch in (None,True,0,-1):
        with pytest.raises(ValueError,match="active authority epoch is invalid"):
            EndpointFinalityAuthoritySnapshot(active_authority_epoch=bad_epoch,keys=(trusted,))
    for invalid_key in (None,ec.derive_private_key(1,ec.SECP384R1()).public_key(),ec.derive_private_key(1,ec.SECP256R1())):
        with pytest.raises(ValueError,match="trusted public key is invalid"):
            replace(trusted,public_key=invalid_key)
    for invalid_kid in (b"",b"k"*65,bytearray(b"k")):
        with pytest.raises(ValueError,match="trusted key kid is invalid"):
            replace(trusted,kid=invalid_kid)
    assert EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=(trusted,replace(trusted,issuer_id="other"))).keys[0] is trusted
