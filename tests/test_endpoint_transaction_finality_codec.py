from dataclasses import replace

import pytest

from src.device_fabric.endpoint_transaction_finality_codec import decode_endpoint_finality_assertion_claims,encode_endpoint_finality_assertion_claims
from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision


def test_endpoint_finality_claims_codec_matches_v1_golden_vector():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    encoded=encode_endpoint_finality_assertion_claims(claims)
    assert type(encoded) is bytes
    assert encoded.hex()=="83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f6"


def test_endpoint_finality_claims_codec_preserves_float_type_and_signed_zero():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1.0,not_before=-0.0,expires_at=2.0,previous_proof_digest=None)
    encoded=encode_endpoint_finality_assertion_claims(claims)
    assert encoded.hex()=="83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010ef93c000ff9800010f9400011f6"


def test_endpoint_finality_claims_codec_decodes_v1_golden_vector():
    encoded=bytes.fromhex("83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f6")
    decoded=decode_endpoint_finality_assertion_claims(encoded)
    expected=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    assert decoded==expected
    assert type(decoded.issued_at) is int
    assert type(decoded.not_before) is int
    assert type(decoded.expires_at) is int


def test_endpoint_finality_claims_codec_decodes_float_type_and_signed_zero():
    encoded=bytes.fromhex("83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010ef93c000ff9800010f9400011f6")
    decoded=decode_endpoint_finality_assertion_claims(encoded)
    assert type(decoded.issued_at) is float
    assert type(decoded.not_before) is float
    assert type(decoded.expires_at) is float
    assert decoded.issued_at.hex()==(1.0).hex()
    assert decoded.not_before.hex()==(-0.0).hex()
    assert decoded.expires_at.hex()==(2.0).hex()
    assert encode_endpoint_finality_assertion_claims(decoded)==encoded


def test_endpoint_finality_claims_codec_rejects_noncanonical_equivalent_encodings():
    integer_vector=bytes.fromhex("83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f6")
    float_vector=bytes.fromhex("83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010ef93c000ff9800010f9400011f6")
    noncanonical_integer=integer_vector.replace(bytes((0x01,0xb2)),bytes((0x18,0x01,0xb2)),1)
    noncanonical_float=float_vector.replace(bytes.fromhex("f93c00"),bytes.fromhex("fa3f800000"),1)
    for encoded in (noncanonical_integer,noncanonical_float):
        with pytest.raises(ValueError,match="finality claims encoding is not canonical"):
            decode_endpoint_finality_assertion_claims(encoded)


def test_endpoint_finality_claims_codec_rejects_invalid_frame_structure():
    canonical=bytes.fromhex("83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f6")
    wrong_domain=canonical.replace(b"AQSS/endpoint-finality/claims",b"BQSS/endpoint-finality/claims",1)
    wrong_version=canonical.replace(bytes((0x01,0xb2)),bytes((0x02,0xb2)),1)
    wrong_field_count=canonical.replace(bytes((0xb2,0x00)),bytes((0xb1,0x00)),1)
    duplicate_label=canonical.replace(bytes((0x01,0x61,0x70,0x02)),bytes((0x00,0x61,0x70,0x02)),1)
    trailing_data=canonical+bytes((0x00,))
    for encoded in (wrong_domain,wrong_version,wrong_field_count,duplicate_label,trailing_data):
        with pytest.raises(ValueError):
            decode_endpoint_finality_assertion_claims(encoded)


def test_endpoint_finality_claims_codec_preserves_exact_unicode_scalars():
    base=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    composed=replace(base,proof_id="\u00e9")
    decomposed=replace(base,proof_id="e\u0301")
    composed_bytes=encode_endpoint_finality_assertion_claims(composed)
    decomposed_bytes=encode_endpoint_finality_assertion_claims(decomposed)
    assert composed_bytes!=decomposed_bytes
    assert decode_endpoint_finality_assertion_claims(composed_bytes).proof_id=="\u00e9"
    assert decode_endpoint_finality_assertion_claims(decomposed_bytes).proof_id=="e\u0301"
    assert decode_endpoint_finality_assertion_claims(composed_bytes).proof_id.encode("utf-8")!=decode_endpoint_finality_assertion_claims(decomposed_bytes).proof_id.encode("utf-8")


def test_endpoint_finality_claims_codec_enforces_signed_64_bit_integer_domain():
    base=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    boundary=replace(base,controller_fencing_token=(1<<63)-1)
    encoded=encode_endpoint_finality_assertion_claims(boundary)
    assert decode_endpoint_finality_assertion_claims(encoded).controller_fencing_token==(1<<63)-1
    with pytest.raises(ValueError,match="finality codec integer is invalid"):
        encode_endpoint_finality_assertion_claims(replace(base,controller_fencing_token=1<<63))


def test_endpoint_finality_claims_codec_rejects_invalid_boundary_types():
    class ClaimsSubclass(EndpointFinalityAssertionClaims):
        pass
    class BytesSubclass(bytes):
        pass
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    subclass_claims=ClaimsSubclass(**{field:getattr(claims,field) for field in EndpointFinalityAssertionClaims.__slots__})
    for invalid_claims in (None,object(),{},subclass_claims):
        with pytest.raises(ValueError,match="finality assertion claims are invalid"):
            encode_endpoint_finality_assertion_claims(invalid_claims)
    for invalid_encoding in (None,object(),{},bytearray(),BytesSubclass()):
        with pytest.raises(ValueError,match="finality claims encoding is invalid"):
            decode_endpoint_finality_assertion_claims(invalid_encoding)


def test_endpoint_finality_claims_codec_rejects_invalid_unicode():
    base=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    with pytest.raises(ValueError,match="finality codec text is invalid"):
        encode_endpoint_finality_assertion_claims(replace(base,proof_id="\ud800"))
    canonical=encode_endpoint_finality_assertion_claims(base)
    invalid_utf8=canonical.replace(bytes((0x01,0x61,0x70,0x02)),bytes((0x01,0x61,0xff,0x02)),1)
    with pytest.raises(ValueError,match="finality claims encoding has invalid text"):
        decode_endpoint_finality_assertion_claims(invalid_utf8)


def test_endpoint_finality_claims_codec_rejects_truncation_and_unsupported_scalars():
    canonical=bytes.fromhex("83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f6")
    for length in range(len(canonical)):
        with pytest.raises(ValueError):
            decode_endpoint_finality_assertion_claims(canonical[:length])
    unsupported_scalar=canonical[:-1]+bytes((0xf5,))
    with pytest.raises(ValueError,match="finality claims encoding has an unsupported scalar"):
        decode_endpoint_finality_assertion_claims(unsupported_scalar)


def test_endpoint_finality_claims_codec_rejects_oversized_input_before_parse(monkeypatch):
    from src.device_fabric import endpoint_transaction_finality_codec as codec
    def forbidden_parser(data):
        raise AssertionError("oversized input reached the parser")
    monkeypatch.setattr(codec,"_FinalityClaimsDecoder",forbidden_parser)
    with pytest.raises(ValueError,match="finality claims encoding exceeds maximum size"):
        codec.decode_endpoint_finality_assertion_claims(bytes((0x83,))*8193)


def test_endpoint_finality_claims_codec_rejects_oversized_output():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="x"*8193,issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    with pytest.raises(ValueError,match="finality claims encoding exceeds maximum size"):
        encode_endpoint_finality_assertion_claims(claims)


def test_endpoint_finality_claims_codec_bounds_each_text_field_by_utf8_bytes():
    base=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    fields=("proof_id","issuer_id","audience","device_id","transaction_id","intent_id","capability_digest","authorization_digest","controller_id","reason_code","previous_proof_digest")
    for field in fields:
        boundary=replace(base,**{field:"\u00e9"*128})
        assert getattr(decode_endpoint_finality_assertion_claims(encode_endpoint_finality_assertion_claims(boundary)),field)=="\u00e9"*128
        for oversized in ("x"*257,"\u00e9"*129):
            with pytest.raises(ValueError,match="finality codec text exceeds maximum size"):
                encode_endpoint_finality_assertion_claims(replace(base,**{field:oversized}))


def test_endpoint_finality_claims_codec_rejects_oversized_text_before_copy(monkeypatch):
    from src.device_fabric import endpoint_transaction_finality_codec as codec
    canonical=bytes.fromhex("83781d415153532f656e64706f696e742d66696e616c6974792f636c61696d7301b2000101617002616903616104616405617406616e0761630861680961720a010b6b4e4f545f4150504c4945440c61780d010e010f00100211f6")
    original=bytes((1,0x61,0x70,2))
    assert canonical.count(original)==1
    oversized=canonical.replace(original,bytes((1,0x79,1,1))+b"x"*257+bytes((2,)),1)
    original_take=codec._FinalityClaimsDecoder._take
    def guarded_take(self,length):
        if length>256:
            raise AssertionError("oversized text was copied")
        return original_take(self,length)
    monkeypatch.setattr(codec._FinalityClaimsDecoder,"_take",guarded_take)
    with pytest.raises(ValueError,match="finality claims encoding text exceeds maximum size"):
        codec.decode_endpoint_finality_assertion_claims(oversized)


def test_endpoint_finality_v2_codec_binds_request_digest():
    base=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    claims=replace(base,profile_version=2,request_digest="request-one")
    encoded=encode_endpoint_finality_assertion_claims(claims)
    assert decode_endpoint_finality_assertion_claims(encoded)==claims
    assert encoded!=encode_endpoint_finality_assertion_claims(replace(claims,request_digest="request-two"))
    wrong_version=encoded.replace(bytes((2,0xb3)),bytes((1,0xb3)),1)
    assert wrong_version!=encoded
    with pytest.raises(ValueError):
        decode_endpoint_finality_assertion_claims(wrong_version)
