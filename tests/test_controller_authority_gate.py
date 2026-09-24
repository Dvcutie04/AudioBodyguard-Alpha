from dataclasses import replace
from hashlib import sha256

from src.control.active_controller_lease import ActiveControllerLeaseAuthority
from src.control.controller_authority_gate import ControllerAuthorityDecision,ControllerAuthorityGate
from src.control.controller_command_proof import ControllerCommandProofVerifier,SignedControllerCommandProof
from src.control.controller_lease_grant import ControllerLeaseGrantIssuer,ControllerLeaseGrantVerifier
from src.control.crypto_identity import KeyPair
from src.control.remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair,RemoteControllerResultVerifier,SignedAtomicControllerResult


def _signed_proof(key,grant,sequence):
    unsigned=SignedControllerCommandProof(grant_digest=sha256(grant.canonical_bytes).hexdigest(),command_id=f"command-{sequence}",command_sequence=sequence,action_digest=f"action-{sequence}",controller_key_id=key.key_id)
    return replace(unsigned,signature=key.sign(unsigned.canonical_bytes))


def test_tri_anchor_gate_rejects_replay_and_resets_sequence_only_for_higher_fence():
    authority=ActiveControllerLeaseAuthority()
    authority_key=KeyPair.generate("controller-authority")
    phone_a=KeyPair.generate("secure-key-a")
    phone_b=KeyPair.generate("secure-key-b")
    grant_issuer=ControllerLeaseGrantIssuer(authority,authority_key)
    gate=ControllerAuthorityGate(authority,ControllerLeaseGrantVerifier({authority_key.key_id:authority_key.public_verifier}),ControllerCommandProofVerifier({phone_a.key_id:phone_a.public_verifier,phone_b.key_id:phone_b.public_verifier}))
    lease_a=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    grant_a=grant_issuer.issue(lease=lease_a,controller_key_id=phone_a.key_id,nonce="grant-a",now=101.0)
    proof_a1=_signed_proof(phone_a,grant_a,1)
    proof_a2=_signed_proof(phone_a,grant_a,2)
    assert gate.validate(grant=grant_a,proof=proof_a1,now=101.0) is ControllerAuthorityDecision.ALLOW
    assert gate.validate(grant=grant_a,proof=proof_a1,now=101.1) is ControllerAuthorityDecision.REPLAYED_SEQUENCE
    assert gate.validate(grant=grant_a,proof=proof_a2,now=101.2) is ControllerAuthorityDecision.ALLOW
    lease_b=authority.handoff(current_lease=lease_a,next_controller_id="phone-b",now=102.0,ttl_seconds=30.0)
    stale_a3=_signed_proof(phone_a,grant_a,3)
    assert gate.validate(grant=grant_a,proof=stale_a3,now=103.0) is ControllerAuthorityDecision.STALE_FENCE
    grant_b=grant_issuer.issue(lease=lease_b,controller_key_id=phone_b.key_id,nonce="grant-b",now=103.0)
    proof_b1=_signed_proof(phone_b,grant_b,1)
    assert gate.validate(grant=grant_b,proof=proof_b1,now=103.0) is ControllerAuthorityDecision.ALLOW


def test_rejected_command_does_not_consume_sequence_watermark():
    authority=ActiveControllerLeaseAuthority()
    authority_key=KeyPair.generate("controller-authority")
    phone=KeyPair.generate("secure-key-a")
    attacker=KeyPair.generate("attacker")
    lease=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    grant=ControllerLeaseGrantIssuer(authority,authority_key).issue(lease=lease,controller_key_id=phone.key_id,nonce="grant-safe",now=101.0)
    gate=ControllerAuthorityGate(authority,ControllerLeaseGrantVerifier({authority_key.key_id:authority_key.public_verifier}),ControllerCommandProofVerifier({phone.key_id:phone.public_verifier,attacker.key_id:attacker.public_verifier}))
    valid=_signed_proof(phone,grant,1)
    forged=replace(valid,signature=attacker.sign(valid.canonical_bytes))
    assert gate.validate(grant=grant,proof=forged,now=101.0) is ControllerAuthorityDecision.COMMAND_REJECTED
    assert gate.validate(grant=grant,proof=valid,now=101.1) is ControllerAuthorityDecision.ALLOW


def test_concurrent_identical_commands_have_exactly_one_winner():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    authority=ActiveControllerLeaseAuthority()
    authority_key=KeyPair.generate("controller-authority")
    phone=KeyPair.generate("secure-key-a")
    lease=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    grant=ControllerLeaseGrantIssuer(authority,authority_key).issue(lease=lease,controller_key_id=phone.key_id,nonce="grant-race",now=101.0)
    gate=ControllerAuthorityGate(authority,ControllerLeaseGrantVerifier({authority_key.key_id:authority_key.public_verifier}),ControllerCommandProofVerifier({phone.key_id:phone.public_verifier}))
    proof=_signed_proof(phone,grant,1)
    barrier=Barrier(16)
    def submit():
        barrier.wait()
        return gate.validate(grant=grant,proof=proof,now=101.0)
    with ThreadPoolExecutor(max_workers=16) as pool:
        decisions=list(pool.map(lambda _:submit(),range(16)))
    assert decisions.count(ControllerAuthorityDecision.ALLOW)==1
    assert decisions.count(ControllerAuthorityDecision.REPLAYED_SEQUENCE)==15


def test_restart_preserves_command_sequence_watermark(tmp_path):
    lease_state=tmp_path/"leases.json"
    command_state=tmp_path/"command-watermarks.json"
    authority_key=KeyPair.generate("controller-authority")
    phone=KeyPair.generate("secure-key-a")
    authority=ActiveControllerLeaseAuthority(state_path=lease_state)
    lease=authority.acquire(resource_id="lock:front-door",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    grant=ControllerLeaseGrantIssuer(authority,authority_key).issue(lease=lease,controller_key_id=phone.key_id,nonce="grant-restart",now=101.0)
    grant_verifier=ControllerLeaseGrantVerifier({authority_key.key_id:authority_key.public_verifier})
    command_verifier=ControllerCommandProofVerifier({phone.key_id:phone.public_verifier})
    gate=ControllerAuthorityGate(authority,grant_verifier,command_verifier,state_path=command_state)
    proof5=_signed_proof(phone,grant,5)
    assert gate.validate(grant=grant,proof=proof5,now=101.0) is ControllerAuthorityDecision.ALLOW
    restarted_authority=ActiveControllerLeaseAuthority(state_path=lease_state)
    restarted_gate=ControllerAuthorityGate(restarted_authority,grant_verifier,command_verifier,state_path=command_state)
    assert restarted_gate.validate(grant=grant,proof=proof5,now=102.0) is ControllerAuthorityDecision.REPLAYED_SEQUENCE
    proof6=_signed_proof(phone,grant,6)
    assert restarted_gate.validate(grant=grant,proof=proof6,now=102.1) is ControllerAuthorityDecision.ALLOW


def test_concurrent_persistent_gates_have_exactly_one_winner(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    lease_state=tmp_path/"leases.json"
    command_state=tmp_path/"command-watermarks.json"
    authority_key=KeyPair.generate("controller-authority")
    phone=KeyPair.generate("secure-key-a")
    authority_a=ActiveControllerLeaseAuthority(state_path=lease_state)
    lease=authority_a.acquire(resource_id="lock:front-door",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    grant=ControllerLeaseGrantIssuer(authority_a,authority_key).issue(lease=lease,controller_key_id=phone.key_id,nonce="grant-multiprocess",now=101.0)
    authority_b=ActiveControllerLeaseAuthority(state_path=lease_state)
    grant_verifier=ControllerLeaseGrantVerifier({authority_key.key_id:authority_key.public_verifier})
    command_verifier=ControllerCommandProofVerifier({phone.key_id:phone.public_verifier})
    gate_a=ControllerAuthorityGate(authority_a,grant_verifier,command_verifier,state_path=command_state)
    gate_b=ControllerAuthorityGate(authority_b,grant_verifier,command_verifier,state_path=command_state)
    proof=_signed_proof(phone,grant,1)
    barrier=Barrier(2)
    def submit(gate):
        barrier.wait()
        return gate.validate(grant=grant,proof=proof,now=101.0)
    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions=list(pool.map(submit,(gate_a,gate_b)))
    assert decisions.count(ControllerAuthorityDecision.ALLOW)==1
    assert decisions.count(ControllerAuthorityDecision.REPLAYED_SEQUENCE)==1


def test_restart_preserves_remote_command_sequence_watermark(tmp_path):
    lease_state=tmp_path/"remote-leases.json"
    command_state=tmp_path/"remote-command-watermarks.json"
    phone=KeyPair.generate("secure-key-a")
    remote_key=P256AuthorityKeyPair.generate("remote-p256-controller-authority")
    authority=ActiveControllerLeaseAuthority(state_path=lease_state)
    lease=authority.acquire(resource_id="lock:front-door",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    request=AtomicControllerRequest(operation="acquire",request_id="remote-gate-restart",resource_id=lease.resource_id,controller_id=lease.controller_id,controller_key_id=phone.key_id,current_fencing_token=0,requested_ttl_seconds=30.0,challenge="remote-gate-restart-challenge")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=lease.fencing_token,issued_at=lease.issued_at,expires_at=lease.expires_at,signing_key=remote_key)
    result_verifier=RemoteControllerResultVerifier({remote_key.key_id:remote_key.public_verifier})
    grant_verifier=ControllerLeaseGrantVerifier({})
    command_verifier=ControllerCommandProofVerifier({phone.key_id:phone.public_verifier})
    gate=ControllerAuthorityGate(authority,grant_verifier,command_verifier,state_path=command_state,remote_result_verifier=result_verifier)
    unsigned5=SignedControllerCommandProof(grant_digest=sha256(result.canonical_bytes).hexdigest(),command_id="remote-command-5",command_sequence=5,action_digest="remote-action-5",controller_key_id=phone.key_id)
    proof5=replace(unsigned5,signature=phone.sign(unsigned5.canonical_bytes))
    assert gate.validate_remote(result=result,request=request,proof=proof5,now=101.0) is ControllerAuthorityDecision.ALLOW
    restarted_authority=ActiveControllerLeaseAuthority(state_path=lease_state)
    restarted_gate=ControllerAuthorityGate(restarted_authority,grant_verifier,command_verifier,state_path=command_state,remote_result_verifier=result_verifier)
    assert restarted_gate.validate_remote(result=result,request=request,proof=proof5,now=102.0) is ControllerAuthorityDecision.REPLAYED_SEQUENCE
    unsigned6=replace(unsigned5,command_id="remote-command-6",command_sequence=6,action_digest="remote-action-6",signature="")
    proof6=replace(unsigned6,signature=phone.sign(unsigned6.canonical_bytes))
    assert restarted_gate.validate_remote(result=result,request=request,proof=proof6,now=102.1) is ControllerAuthorityDecision.ALLOW
