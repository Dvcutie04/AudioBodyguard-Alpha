def test_endpoint_finality_envelope_decodes_c2_golden_wire():
    from src.device_fabric.endpoint_transaction_finality_envelope import decode_endpoint_finality_cose_sign1
    wire=bytes.fromhex("d28446a2012804416ba0585b83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f65840"+"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f")
    decoded=decode_endpoint_finality_cose_sign1(wire)
    assert decoded.kid==b"k"
    assert decoded.signature==bytes(range(64))
    assert decoded.protected==bytes.fromhex("a2012804416b")
    assert decoded.payload==bytes.fromhex("83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f6")
    assert decoded.claims.proof_id=="p"


def test_endpoint_finality_envelope_rejects_malformed_wires():
    import pytest
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_cose_sign1
    from src.device_fabric.endpoint_transaction_finality_envelope import decode_endpoint_finality_cose_sign1
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    wire=encode_endpoint_finality_cose_sign1(claims=claims,kid=b"k",signature=bytes(range(64)))
    assert wire.startswith(bytes.fromhex("d28446a2012804416ba0"))
    class BytesSubclass(bytes):
        pass
    malformed=(None,bytearray(wire),BytesSubclass(wire),bytes(9217),wire[:-1],wire+bytes.fromhex("00"),bytes.fromhex("d812")+wire[1:],wire[:1]+bytes.fromhex("9804")+wire[2:],wire[:5]+bytes.fromhex("26")+wire[6:],wire[:9]+bytes.fromhex("a10101")+wire[10:],wire[:2]+bytes.fromhex("48a30128012804416b")+wire[9:],wire.replace(b"AQSS",b"XQSS",1))
    for candidate in malformed:
        with pytest.raises(ValueError):
            decode_endpoint_finality_cose_sign1(candidate)


def test_endpoint_finality_signature_verification_binds_context_and_payload():
    from dataclasses import replace
    import pytest
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec,utils
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_cose_sign1,encode_endpoint_finality_signing_input
    from src.device_fabric.endpoint_transaction_finality_envelope import verify_endpoint_finality_cose_sign1
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    private_key=ec.derive_private_key(1,ec.SECP256R1())
    signing_input=encode_endpoint_finality_signing_input(claims=claims,kid=b"k",namespace=b"n")
    r,s=utils.decode_dss_signature(private_key.sign(signing_input,ec.ECDSA(hashes.SHA256())))
    signature=r.to_bytes(32,"big")+s.to_bytes(32,"big")
    wire=encode_endpoint_finality_cose_sign1(claims=claims,kid=b"k",signature=signature)
    verified=verify_endpoint_finality_cose_sign1(wire=wire,namespace=b"n",public_key=private_key.public_key())
    assert verified.claims==claims
    assert verified.kid==b"k"
    assert verified.namespace==b"n"
    invalid=((wire,b"m",private_key.public_key()),(wire,b"n",ec.derive_private_key(2,ec.SECP256R1()).public_key()),(encode_endpoint_finality_cose_sign1(claims=claims,kid=b"j",signature=signature),b"n",private_key.public_key()),(encode_endpoint_finality_cose_sign1(claims=replace(claims,proof_id="q"),kid=b"k",signature=signature),b"n",private_key.public_key()),(wire[:-1]+bytes((wire[-1]^1,)),b"n",private_key.public_key()))
    for candidate,namespace,key in invalid:
        with pytest.raises(ValueError):
            verify_endpoint_finality_cose_sign1(wire=candidate,namespace=namespace,public_key=key)


def test_endpoint_finality_signature_verification_rejects_invalid_inputs():
    import pytest
    from cryptography.hazmat.primitives.asymmetric import ec
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_cose_sign1
    from src.device_fabric.endpoint_transaction_finality_envelope import SignatureVerifiedEndpointFinalityEnvelope,verify_endpoint_finality_cose_sign1
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    key=ec.derive_private_key(1,ec.SECP256R1()).public_key()
    wire=encode_endpoint_finality_cose_sign1(claims=claims,kid=b"k",signature=bytes(64))
    with pytest.raises(TypeError,match="requires verification"):
        SignatureVerifiedEndpointFinalityEnvelope()
    for invalid_key in (None,b"k",ec.derive_private_key(1,ec.SECP256R1()),ec.derive_private_key(1,ec.SECP384R1()).public_key()):
        with pytest.raises(ValueError,match="verification key is invalid"):
            verify_endpoint_finality_cose_sign1(wire=wire,namespace=b"n",public_key=invalid_key)
    class BytesSubclass(bytes):
        pass
    for invalid_namespace in (None,b"",b"n"*65,bytearray(b"n"),BytesSubclass(b"n")):
        with pytest.raises(ValueError,match="finality namespace is invalid"):
            verify_endpoint_finality_cose_sign1(wire=wire,namespace=invalid_namespace,public_key=key)
    for signature in (bytes(64),bytes.fromhex("ff"*64)):
        with pytest.raises(ValueError,match="signature verification failed"):
            verify_endpoint_finality_cose_sign1(wire=encode_endpoint_finality_cose_sign1(claims=claims,kid=b"k",signature=signature),namespace=b"n",public_key=key)
