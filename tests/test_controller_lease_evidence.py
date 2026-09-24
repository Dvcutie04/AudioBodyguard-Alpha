import hashlib
import json
from dataclasses import replace

from src.control.controller_lease_evidence import ControllerEvidenceDecision, ControllerLeaseEvidenceValidator, SignedControllerLeaseEvidence
from src.control.crypto_identity import KeyPair


def _raw(key_id):
    return {
        "resource_id":"tv:living-room",
        "controller_id":"phone-a",
        "fencing_token":7,
        "issued_at":100.0,
        "expires_at":130.0,
        "issuer_id":key_id,
        "nonce":"controller-lease-nonce-7",
        "scope":("POWER","SET_VOLUME"),
    }


def test_controller_evidence_has_exact_canonical_bytes_and_digest():
    key=KeyPair.generate(key_id="controller-authority")
    evidence=SignedControllerLeaseEvidence(**_raw(key.key_id))
    expected=json.dumps({
        "resource_id":"tv:living-room",
        "controller_id":"phone-a",
        "fencing_token":7,
        "issued_at":100.0,
        "expires_at":130.0,
        "issuer_id":"controller-authority",
        "nonce":"controller-lease-nonce-7",
        "scope":["POWER","SET_VOLUME"],
    },sort_keys=True,separators=(",",":")).encode("utf-8")
    assert evidence.canonical_bytes==expected
    assert evidence.evidence_digest==hashlib.sha256(expected).hexdigest()


def test_every_controller_authority_field_is_inside_signature_boundary():
    key=KeyPair.generate(key_id="controller-authority")
    unsigned=SignedControllerLeaseEvidence(**_raw(key.key_id))
    signed=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    assert key.public_verifier.verify(signed.canonical_bytes,signed.signature)
    alterations=(
        replace(signed,resource_id="tv:bedroom"),
        replace(signed,controller_id="phone-b"),
        replace(signed,fencing_token=8),
        replace(signed,issued_at=99.0),
        replace(signed,expires_at=131.0),
        replace(signed,issuer_id="rogue-authority"),
        replace(signed,nonce="controller-lease-nonce-forged"),
        replace(signed,scope=("POWER",)),
    )
    for tampered in alterations:
        assert not key.public_verifier.verify(tampered.canonical_bytes,tampered.signature)


def _signed(key,**changes):
    data={**_raw(key.key_id),**changes}
    unsigned=SignedControllerLeaseEvidence(**data)
    return replace(unsigned,signature=key.sign(unsigned.canonical_bytes))


def test_controller_evidence_validator_allows_once_then_rejects_replay():
    key=KeyPair.generate(key_id="controller-authority")
    validator=ControllerLeaseEvidenceValidator({key.key_id:key.public_verifier})
    evidence=_signed(key)
    assert validator.validate(evidence,now=100.0) is ControllerEvidenceDecision.ALLOW
    assert validator.validate(evidence,now=101.0) is ControllerEvidenceDecision.REPLAY


def test_unknown_issuer_is_rejected():
    trusted=KeyPair.generate(key_id="trusted-authority")
    rogue=KeyPair.generate(key_id="rogue-authority")
    validator=ControllerLeaseEvidenceValidator({trusted.key_id:trusted.public_verifier})
    evidence=_signed(rogue)
    assert validator.validate(evidence,now=101.0) is ControllerEvidenceDecision.ISSUER_UNKNOWN


def test_invalid_signature_does_not_consume_nonce():
    key=KeyPair.generate(key_id="controller-authority")
    validator=ControllerLeaseEvidenceValidator({key.key_id:key.public_verifier})
    valid=_signed(key)
    tampered=replace(valid,controller_id="phone-b")
    assert validator.validate(tampered,now=101.0) is ControllerEvidenceDecision.SIGNATURE_INVALID
    assert validator.validate(valid,now=101.0) is ControllerEvidenceDecision.ALLOW


def test_not_yet_valid_evidence_does_not_consume_nonce():
    key=KeyPair.generate(key_id="controller-authority")
    validator=ControllerLeaseEvidenceValidator({key.key_id:key.public_verifier})
    evidence=_signed(key)
    assert validator.validate(evidence,now=99.999) is ControllerEvidenceDecision.NOT_YET_VALID
    assert validator.validate(evidence,now=100.0) is ControllerEvidenceDecision.ALLOW


def test_evidence_expires_at_exact_boundary_without_consuming_nonce():
    key=KeyPair.generate(key_id="controller-authority")
    validator=ControllerLeaseEvidenceValidator({key.key_id:key.public_verifier})
    evidence=_signed(key)
    assert validator.validate(evidence,now=130.0) is ControllerEvidenceDecision.EXPIRED
    assert validator._seen_nonces==set()


def test_malformed_controller_evidence_is_rejected_at_construction():
    import pytest
    key=KeyPair.generate(key_id="controller-authority")
    invalid_changes=(
        {"resource_id":""},
        {"controller_id":"   "},
        {"fencing_token":True},
        {"fencing_token":0},
        {"fencing_token":-1},
        {"issued_at":True},
        {"issued_at":float("nan")},
        {"issued_at":float("inf")},
        {"expires_at":float("nan")},
        {"expires_at":float("inf")},
        {"expires_at":100.0},
        {"expires_at":99.0},
        {"issuer_id":""},
        {"nonce":"   "},
        {"scope":[]},
        {"scope":()},
        {"scope":("POWER","POWER")},
        {"scope":("POWER","   ")},
        {"signature":None},
    )
    for changes in invalid_changes:
        with pytest.raises(ValueError):
            SignedControllerLeaseEvidence(**{**_raw(key.key_id),**changes})


def test_invalid_validation_inputs_do_not_consume_nonce():
    import pytest
    key=KeyPair.generate(key_id="controller-authority")
    validator=ControllerLeaseEvidenceValidator({key.key_id:key.public_verifier})
    evidence=_signed(key)
    with pytest.raises(ValueError):
        validator.validate(object(),now=101.0)
    for invalid_now in (True,float("nan"),float("inf"),float("-inf")):
        with pytest.raises(ValueError):
            validator.validate(evidence,now=invalid_now)
    assert validator._seen_nonces==set()
    assert validator.validate(evidence,now=101.0) is ControllerEvidenceDecision.ALLOW


def test_concurrent_replay_validation_allows_exactly_once():
    import threading
    key=KeyPair.generate(key_id="controller-authority")
    validator=ControllerLeaseEvidenceValidator({key.key_id:key.public_verifier})
    evidence=_signed(key)
    start=threading.Barrier(9)
    result_lock=threading.Lock()
    results=[]

    def validate_once():
        start.wait(timeout=5.0)
        result=validator.validate(evidence,now=101.0)
        with result_lock:
            results.append(result)

    threads=[threading.Thread(target=validate_once) for _ in range(8)]
    for thread in threads:
        thread.start()
    start.wait(timeout=5.0)
    for thread in threads:
        thread.join(timeout=5.0)
    assert all(not thread.is_alive() for thread in threads)
    assert results.count(ControllerEvidenceDecision.ALLOW)==1
    assert results.count(ControllerEvidenceDecision.REPLAY)==7
    assert validator._seen_nonces=={(key.key_id,evidence.nonce)}
