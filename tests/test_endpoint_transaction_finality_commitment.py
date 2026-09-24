def test_endpoint_finality_protected_headers_match_esp256_golden_vector():
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_protected_headers
    encoded=encode_endpoint_finality_protected_headers(kid=b"k")
    assert type(encoded) is bytes
    assert encoded.hex()=="a2012804416b"


def test_endpoint_finality_external_aad_matches_v1_golden_vector():
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_external_aad
    encoded=encode_endpoint_finality_external_aad(namespace=b"n")
    assert type(encoded) is bytes
    assert encoded.hex()=="83781e415153532f656e64706f696e742d66696e616c6974792f636f6e7465787401416e"


def test_endpoint_finality_signing_input_matches_v1_golden_vector():
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_signing_input
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    encoded=encode_endpoint_finality_signing_input(claims=claims,kid=b"k",namespace=b"n")
    assert type(encoded) is bytes
    assert encoded.hex()=="846a5369676e61747572653146a2012804416b582483781e415153532f656e64706f696e742d66696e616c6974792f636f6e7465787401416e585b83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f6"


def test_endpoint_finality_proof_digest_matches_v1_golden_vector():
    from src.device_fabric.endpoint_transaction_finality_commitment import compute_endpoint_finality_proof_digest
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    digest=compute_endpoint_finality_proof_digest(claims=claims,kid=b"k",namespace=b"n")
    assert type(digest) is str
    assert digest=="0a4aedfa0461efeebdf8f822e0edeae6b0eeac2e8c1e82ea11ee2a91aeb250d0"


def test_endpoint_finality_cose_sign1_matches_v1_golden_vector():
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_cose_sign1
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    encoded=encode_endpoint_finality_cose_sign1(claims=claims,kid=b"k",signature=bytes(range(64)))
    assert type(encoded) is bytes
    assert encoded.hex()==("d28446a2012804416ba0585b83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f65840"+"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f")


def test_endpoint_finality_digest_binds_claims_kid_and_namespace():
    from dataclasses import replace
    from src.device_fabric.endpoint_transaction_finality_commitment import compute_endpoint_finality_proof_digest
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    original=compute_endpoint_finality_proof_digest(claims=claims,kid=b"k",namespace=b"n")
    assert compute_endpoint_finality_proof_digest(claims=replace(claims,proof_id="q"),kid=b"k",namespace=b"n")!=original
    assert compute_endpoint_finality_proof_digest(claims=claims,kid=b"j",namespace=b"n")!=original
    assert compute_endpoint_finality_proof_digest(claims=claims,kid=b"k",namespace=b"m")!=original


def test_endpoint_finality_commitment_rejects_invalid_opaque_inputs():
    import pytest
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_protected_headers,encode_endpoint_finality_external_aad,encode_endpoint_finality_cose_sign1
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    class BytesSubclass(bytes):
        pass
    assert encode_endpoint_finality_protected_headers(kid=b"k"*64).startswith(bytes.fromhex("a20128045840"))
    assert encode_endpoint_finality_external_aad(namespace=b"n"*64).endswith(b"n"*64)
    for kid in (None,b"",b"k"*65,bytearray(b"k"),BytesSubclass(b"k")):
        with pytest.raises(ValueError,match="finality protected kid is invalid"):
            encode_endpoint_finality_protected_headers(kid=kid)
    for namespace in (None,b"",b"n"*65,bytearray(b"n"),BytesSubclass(b"n")):
        with pytest.raises(ValueError,match="finality namespace is invalid"):
            encode_endpoint_finality_external_aad(namespace=namespace)
    for signature in (None,b"",b"s"*63,b"s"*65,bytearray(b"s"*64),BytesSubclass(b"s"*64)):
        with pytest.raises(ValueError,match="finality COSE signature is invalid"):
            encode_endpoint_finality_cose_sign1(claims=claims,kid=b"k",signature=signature)
