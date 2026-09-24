from dataclasses import replace
from hashlib import sha256

from src.control.controller_command_proof import ControllerCommandDecision,ControllerCommandProofVerifier,SignedControllerCommandProof
from src.control.controller_lease_grant import SignedControllerLeaseGrant
from src.control.crypto_identity import KeyPair


def test_controller_command_requires_bound_key_and_exact_signed_payload():
    phone=KeyPair.generate("secure-key-a")
    attacker=KeyPair.generate("secure-key-attacker")
    grant=SignedControllerLeaseGrant(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,controller_key_id=phone.key_id,issued_at=100.0,expires_at=130.0,nonce="grant-6",issuer_id="controller-authority",signature="authority-signature")
    grant_digest=sha256(grant.canonical_bytes).hexdigest()
    unsigned=SignedControllerCommandProof(grant_digest=grant_digest,command_id="command-1",command_sequence=1,action_digest="action-digest-1",controller_key_id=phone.key_id)
    proof=replace(unsigned,signature=phone.sign(unsigned.canonical_bytes))
    verifier=ControllerCommandProofVerifier({phone.key_id:phone.public_verifier,attacker.key_id:attacker.public_verifier})
    assert verifier.validate(proof,grant) is ControllerCommandDecision.ALLOW
    forged=replace(unsigned,signature=attacker.sign(unsigned.canonical_bytes))
    assert verifier.validate(forged,grant) is ControllerCommandDecision.INVALID_SIGNATURE
    stolen_unsigned=replace(unsigned,controller_key_id=attacker.key_id)
    stolen=replace(stolen_unsigned,signature=attacker.sign(stolen_unsigned.canonical_bytes))
    assert verifier.validate(stolen,grant) is ControllerCommandDecision.KEY_MISMATCH
    wrong_grant_unsigned=replace(unsigned,grant_digest="wrong-grant-digest")
    wrong_grant=replace(wrong_grant_unsigned,signature=phone.sign(wrong_grant_unsigned.canonical_bytes))
    assert verifier.validate(wrong_grant,grant) is ControllerCommandDecision.GRANT_MISMATCH
    assert verifier.validate(replace(proof,action_digest="action-digest-2"),grant) is ControllerCommandDecision.INVALID_SIGNATURE
    assert verifier.validate(replace(proof,command_sequence=2),grant) is ControllerCommandDecision.INVALID_SIGNATURE


def test_controller_command_malformed_values_fail_closed_without_exception():
    phone=KeyPair.generate("secure-key-a")
    grant=SignedControllerLeaseGrant(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,controller_key_id=phone.key_id,issued_at=100.0,expires_at=130.0,nonce="grant-7",issuer_id="controller-authority",signature="authority-signature")
    grant_digest=sha256(grant.canonical_bytes).hexdigest()
    unsigned=SignedControllerCommandProof(grant_digest=grant_digest,command_id="command-1",command_sequence=1,action_digest="action-digest-1",controller_key_id=phone.key_id)
    sign=lambda candidate:replace(candidate,signature=phone.sign(candidate.canonical_bytes))
    proof=sign(unsigned)
    verifier=ControllerCommandProofVerifier({phone.key_id:phone.public_verifier})
    malformed=(replace(unsigned,grant_digest=""),replace(unsigned,command_id=""),replace(unsigned,command_sequence=True),replace(unsigned,command_sequence=0),replace(unsigned,action_digest=""),replace(unsigned,controller_key_id=""))
    assert all(verifier.validate(sign(candidate),grant) is ControllerCommandDecision.MALFORMED for candidate in malformed)
    assert verifier.validate(replace(proof,signature=""),grant) is ControllerCommandDecision.MALFORMED
    assert verifier.validate(None,grant) is ControllerCommandDecision.MALFORMED
    assert verifier.validate(proof,None) is ControllerCommandDecision.MALFORMED
