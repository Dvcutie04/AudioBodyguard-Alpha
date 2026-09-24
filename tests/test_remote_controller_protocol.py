from dataclasses import replace

from src.control.remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair,P256AuthorityPublicVerifier,RemoteControllerResultDecision,RemoteControllerResultVerifier,SignedAtomicControllerResult


def test_signed_result_is_bound_to_exact_canonical_acquisition_request():
    signing_key=P256AuthorityKeyPair.generate("production-controller-authority")
    request=AtomicControllerRequest(operation="acquire",request_id="request-phone-a",resource_id="tv:living-room",controller_id="phone-a",controller_key_id="secure-phone-a-key",current_fencing_token=0,requested_ttl_seconds=30.0,challenge="server-challenge-1")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=1,issued_at=100.0,expires_at=130.0,signing_key=signing_key)
    verifier=RemoteControllerResultVerifier({signing_key.key_id:signing_key.public_verifier})
    assert verifier.validate(result,request=request,now=101.0) is RemoteControllerResultDecision.ALLOW
    mutations=(replace(request,operation="handoff"),replace(request,request_id="request-other"),replace(request,resource_id="door:front"),replace(request,controller_id="phone-b"),replace(request,controller_key_id="attacker-key"),replace(request,current_fencing_token=1),replace(request,requested_ttl_seconds=31.0),replace(request,challenge="server-challenge-2"))
    assert all(verifier.validate(result,request=candidate,now=101.0) is RemoteControllerResultDecision.REQUEST_DIGEST_MISMATCH for candidate in mutations)


def test_request_operation_and_fence_semantics_fail_closed():
    signing_key=P256AuthorityKeyPair.generate("production-controller-authority")
    verifier=RemoteControllerResultVerifier({signing_key.key_id:signing_key.public_verifier})
    valid=AtomicControllerRequest(operation="acquire",request_id="request-valid-acquire",resource_id="tv:living-room",controller_id="phone-a",controller_key_id="secure-phone-a-key",current_fencing_token=0,requested_ttl_seconds=30.0,challenge="server-challenge-valid")
    malformed=(replace(valid,operation="delete"),replace(valid,operation="handoff"),replace(valid,current_fencing_token=1),replace(valid,operation="ACQUIRE"))
    for index,request in enumerate(malformed):
        result=SignedAtomicControllerResult.issue(request=request,fencing_token=index+1,issued_at=100.0,expires_at=130.0,signing_key=signing_key)
        assert verifier.validate(result,request=request,now=101.0) is RemoteControllerResultDecision.MALFORMED
    handoff=replace(valid,operation="handoff",request_id="request-valid-handoff",current_fencing_token=7,challenge="server-challenge-handoff")
    handoff_result=SignedAtomicControllerResult.issue(request=handoff,fencing_token=8,issued_at=102.0,expires_at=132.0,signing_key=signing_key)
    assert verifier.validate(handoff_result,request=handoff,now=103.0) is RemoteControllerResultDecision.ALLOW


def test_result_tampering_unknown_issuer_and_time_window_fail_closed():
    trusted=P256AuthorityKeyPair.generate("trusted-controller-authority")
    attacker=P256AuthorityKeyPair.generate("attacker-controller-authority")
    request=AtomicControllerRequest(operation="acquire",request_id="request-security-proof",resource_id="tv:living-room",controller_id="phone-a",controller_key_id="secure-phone-a-key",current_fencing_token=0,requested_ttl_seconds=30.0,challenge="server-challenge-security")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=1,issued_at=100.0,expires_at=130.0,signing_key=trusted)
    verifier=RemoteControllerResultVerifier({trusted.key_id:trusted.public_verifier})
    tampered=(replace(result,fencing_token=2),replace(result,issued_at=99.0),replace(result,expires_at=131.0),replace(result,algorithm="ECDSA_P384_SHA384"),replace(result,signature="AAAA"))
    assert all(verifier.validate(candidate,request=request,now=101.0) is RemoteControllerResultDecision.INVALID_SIGNATURE for candidate in tampered)
    rebound=(replace(result,resource_id="door:front"),replace(result,controller_id="phone-b"),replace(result,controller_key_id="attacker-key"))
    assert all(verifier.validate(candidate,request=request,now=101.0) is RemoteControllerResultDecision.REQUEST_DIGEST_MISMATCH for candidate in rebound)
    attacker_result=SignedAtomicControllerResult.issue(request=request,fencing_token=1,issued_at=100.0,expires_at=130.0,signing_key=attacker)
    assert verifier.validate(attacker_result,request=request,now=101.0) is RemoteControllerResultDecision.UNKNOWN_ISSUER
    assert verifier.validate(result,request=request,now=99.0) is RemoteControllerResultDecision.NOT_YET_VALID
    assert verifier.validate(result,request=request,now=130.0) is RemoteControllerResultDecision.EXPIRED


def test_malformed_remote_protocol_values_fail_closed_without_exceptions():
    signing_key=P256AuthorityKeyPair.generate("trusted-controller-authority")
    request=AtomicControllerRequest(operation="acquire",request_id="request-malformed-proof",resource_id="tv:living-room",controller_id="phone-a",controller_key_id="secure-phone-a-key",current_fencing_token=0,requested_ttl_seconds=30.0,challenge="server-challenge-malformed")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=1,issued_at=100.0,expires_at=130.0,signing_key=signing_key)
    verifier=RemoteControllerResultVerifier({signing_key.key_id:signing_key.public_verifier})
    malformed_requests=(replace(request,operation=""),replace(request,request_id=" "),replace(request,resource_id=None),replace(request,controller_id=7),replace(request,controller_key_id=""),replace(request,challenge=" "),replace(request,current_fencing_token=True),replace(request,current_fencing_token=-1),replace(request,requested_ttl_seconds=True),replace(request,requested_ttl_seconds=0.0),replace(request,requested_ttl_seconds=float("nan")),replace(request,requested_ttl_seconds=float("inf")))
    assert all(verifier.validate(result,request=candidate,now=101.0) is RemoteControllerResultDecision.MALFORMED for candidate in malformed_requests)
    malformed_results=(replace(result,request_digest=""),replace(result,resource_id=None),replace(result,controller_id=" "),replace(result,controller_key_id=7),replace(result,issuer_id=""),replace(result,algorithm=None),replace(result,signature=""),replace(result,fencing_token=True),replace(result,fencing_token=0),replace(result,issued_at=float("nan")),replace(result,issued_at=float("inf")),replace(result,expires_at=float("nan")),replace(result,expires_at=100.0))
    assert all(verifier.validate(candidate,request=request,now=101.0) is RemoteControllerResultDecision.MALFORMED for candidate in malformed_results)
    assert all(verifier.validate(result,request=request,now=value) is RemoteControllerResultDecision.MALFORMED for value in (True,float("nan"),float("inf"),"101"))
    assert verifier.validate(object(),request=request,now=101.0) is RemoteControllerResultDecision.MALFORMED
    assert verifier.validate(result,request=object(),now=101.0) is RemoteControllerResultDecision.MALFORMED


def test_p256_public_verifier_spki_round_trip_and_rejects_invalid_keys():
    import base64
    import pytest
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    signing_key=P256AuthorityKeyPair.generate("portable-controller-authority")
    encoded=signing_key.public_verifier.export_spki_base64()
    imported=P256AuthorityPublicVerifier.from_spki_base64(signing_key.key_id,encoded)
    request=AtomicControllerRequest(operation="acquire",request_id="request-portable-verifier",resource_id="tv:living-room",controller_id="phone-a",controller_key_id="secure-phone-a-key",current_fencing_token=0,requested_ttl_seconds=30.0,challenge="server-challenge-portable")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=1,issued_at=100.0,expires_at=130.0,signing_key=signing_key)
    verifier=RemoteControllerResultVerifier({signing_key.key_id:imported})
    assert verifier.validate(result,request=request,now=101.0) is RemoteControllerResultDecision.ALLOW
    wrong_curve=ec.generate_private_key(ec.SECP384R1()).public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    with pytest.raises(ValueError,match="invalid P-256 public verifier"):
        P256AuthorityPublicVerifier.from_spki_base64("wrong-curve",base64.b64encode(wrong_curve).decode("ascii"))
    for malformed in ("","not-base64","AAAA"):
        with pytest.raises(ValueError,match="invalid P-256 public verifier"):
            P256AuthorityPublicVerifier.from_spki_base64("portable-controller-authority",malformed)


def test_signed_result_must_advance_handoff_fence_and_respect_requested_ttl():
    signing_key=P256AuthorityKeyPair.generate("trusted-controller-authority")
    verifier=RemoteControllerResultVerifier({signing_key.key_id:signing_key.public_verifier})
    handoff=AtomicControllerRequest(operation="handoff",request_id="request-fence-advance",resource_id="tv:living-room",controller_id="phone-b",controller_key_id="secure-phone-b-key",current_fencing_token=7,requested_ttl_seconds=30.0,challenge="server-challenge-fence")
    for invalid_token in (1,6,7):
        result=SignedAtomicControllerResult.issue(request=handoff,fencing_token=invalid_token,issued_at=100.0,expires_at=130.0,signing_key=signing_key)
        assert verifier.validate(result,request=handoff,now=101.0) is RemoteControllerResultDecision.MALFORMED
    excessive=SignedAtomicControllerResult.issue(request=handoff,fencing_token=8,issued_at=100.0,expires_at=130.000001,signing_key=signing_key)
    assert verifier.validate(excessive,request=handoff,now=101.0) is RemoteControllerResultDecision.MALFORMED
    valid=SignedAtomicControllerResult.issue(request=handoff,fencing_token=8,issued_at=100.0,expires_at=125.0,signing_key=signing_key)
    assert verifier.validate(valid,request=handoff,now=101.0) is RemoteControllerResultDecision.ALLOW
