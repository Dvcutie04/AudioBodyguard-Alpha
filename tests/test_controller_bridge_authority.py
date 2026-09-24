import time
from dataclasses import replace
from hashlib import sha256

import pytest

from src.control.active_controller_lease import ActiveControllerLeaseAuthority
from src.control.authorized_intent import SignedActionIntent
from src.control.capability_lease import SignedCapabilityLease
from src.control.controller_authority_gate import ControllerAuthorityDecision,ControllerAuthorityGate
from src.control.controller_command_proof import ControllerCommandProofVerifier,SignedControllerCommandProof
from src.control.controller_lease_grant import ControllerLeaseGrantIssuer,ControllerLeaseGrantVerifier
from src.control.remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair,RemoteControllerResultVerifier,SignedAtomicControllerResult
from src.control.crypto_identity import KeyPair
from src.control.device_fabric_bridge import Gen3DeviceFabricBridge
from src.control.intent_firewall import IntentFirewall
from src.device_fabric.contracts import CapabilityLease,PhysicalSnapshot
from src.device_fabric.mocks.mock_tv import MockTVAdapter


class CountingTVAdapter(MockTVAdapter):
    def __init__(self,device_id):
        super().__init__(device_id)
        self.calls=0
        self.last_intent=None

    async def execute_intent(self,*args,**kwargs):
        self.calls+=1
        self.last_intent=kwargs.get("intent") if "intent" in kwargs else (args[0] if args else None)
        return await super().execute_intent(*args,**kwargs)


def _environment():
    now=time.time()
    intent_key=KeyPair.generate("intent-authority")
    controller_authority_key=KeyPair.generate("controller-authority")
    phone=KeyPair.generate("secure-key-a")
    attacker=KeyPair.generate("attacker")
    lease_unsigned=SignedCapabilityLease(device_id="tv_integration_node_1",capability_digest="cap_audio",firmware_identity="v1.0",protocol_version="1.0",issued_at=now-1.0,expires_at=now+60.0,nonce="lease-controller",issuer_id=intent_key.key_id)
    lease=replace(lease_unsigned,signature=intent_key.sign(lease_unsigned.canonical_bytes))
    intent_unsigned=SignedActionIntent(intent_id="controller-bridge-1",device_id="tv_integration_node_1",operation="SET_VOLUME",parameters={"volume":55.0},issuer_id=intent_key.key_id,policy_digest="policy",capability_lease_digest=lease.payload_digest,created_at=now,expires_at=now+30.0,nonce="intent-controller",transaction_id="tx-controller-1",protocol_version="1.0")
    intent=replace(intent_unsigned,signature=intent_key.sign(intent_unsigned.canonical_bytes))
    authority=ActiveControllerLeaseAuthority()
    active=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=now-1.0,ttl_seconds=30.0)
    grant=ControllerLeaseGrantIssuer(authority,controller_authority_key).issue(lease=active,controller_key_id=phone.key_id,nonce="bridge-grant",now=now)
    gate=ControllerAuthorityGate(authority,ControllerLeaseGrantVerifier({controller_authority_key.key_id:controller_authority_key.public_verifier}),ControllerCommandProofVerifier({phone.key_id:phone.public_verifier,attacker.key_id:attacker.public_verifier}))
    adapter=CountingTVAdapter(intent.device_id)
    bridge=Gen3DeviceFabricBridge(IntentFirewall({intent_key.key_id:intent_key.public_verifier}),adapter,controller_authority_gate=gate)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=adapter.device.state,epoch=0,observed_at=now)
    proof_unsigned=SignedControllerCommandProof(grant_digest=sha256(grant.canonical_bytes).hexdigest(),command_id="bridge-command-1",command_sequence=1,action_digest=sha256(intent.canonical_bytes).hexdigest(),controller_key_id=phone.key_id)
    valid=replace(proof_unsigned,signature=phone.sign(proof_unsigned.canonical_bytes))
    forged=replace(proof_unsigned,signature=attacker.sign(proof_unsigned.canonical_bytes))
    return bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active


@pytest.mark.asyncio
async def test_controller_authority_rejections_never_reach_adapter_or_consume_intent():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    missing=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,now=now)
    assert missing.status=="REJECTED"
    assert missing.rejection=="CONTROLLER_AUTHORITY_REQUIRED"
    assert bridge.adapter.calls==0
    rejected=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=forged,now=now)
    assert rejected.status=="REJECTED"
    assert rejected.rejection is ControllerAuthorityDecision.COMMAND_REJECTED
    assert bridge.adapter.calls==0
    accepted=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=now)
    assert accepted.status=="EXECUTED"
    assert bridge.adapter.calls==1


@pytest.mark.asyncio
async def test_exact_action_digest_mismatch_never_reaches_adapter_or_consumes_sequence():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    wrong_unsigned=replace(valid,action_digest=sha256(b"different-signed-intent").hexdigest(),signature="")
    wrong=replace(wrong_unsigned,signature=phone.sign(wrong_unsigned.canonical_bytes))
    rejected=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=wrong,now=now)
    assert rejected.status=="REJECTED"
    assert rejected.rejection is ControllerAuthorityDecision.COMMAND_REJECTED
    assert bridge.adapter.calls==0
    accepted=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=now)
    assert accepted.status=="EXECUTED"
    assert bridge.adapter.calls==1


@pytest.mark.asyncio
async def test_replayed_controller_command_never_reaches_adapter_twice():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    first=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=now)
    assert first.status=="EXECUTED"
    assert bridge.adapter.calls==1
    replay=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=now)
    assert replay.status=="REJECTED"
    assert replay.rejection is ControllerAuthorityDecision.REPLAYED_SEQUENCE
    assert bridge.adapter.calls==1


@pytest.mark.asyncio
async def test_stale_controller_fence_never_reaches_adapter():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    replacement=authority.handoff(current_lease=active,next_controller_id="phone-b",now=now+0.1,ttl_seconds=30.0)
    assert replacement.fencing_token>active.fencing_token
    rejected=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=now+0.2)
    assert rejected.status=="REJECTED"
    assert rejected.rejection is ControllerAuthorityDecision.STALE_FENCE
    assert bridge.adapter.calls==0


@pytest.mark.asyncio
async def test_expired_controller_grant_never_reaches_adapter():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    rejected=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=grant.expires_at)
    assert rejected.status=="REJECTED"
    assert rejected.rejection is ControllerAuthorityDecision.GRANT_REJECTED
    assert bridge.adapter.calls==0


@pytest.mark.asyncio
async def test_controller_evidence_cannot_bypass_unconfigured_bridge():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    unconfigured=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter)
    rejected=await unconfigured.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=now)
    assert rejected.status=="REJECTED"
    assert rejected.rejection=="CONTROLLER_AUTHORITY_UNCONFIGURED"
    assert bridge.adapter.calls==0


@pytest.mark.asyncio
async def test_verified_controller_lineage_reaches_adapter():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=now)
    assert result.status=="EXECUTED"
    assert bridge.adapter.calls==1
    assert bridge.adapter.last_intent.controller_resource_id==grant.resource_id
    assert bridge.adapter.last_intent.controller_id==grant.controller_id
    assert bridge.adapter.last_intent.controller_fencing_token==grant.fencing_token


@pytest.mark.asyncio
async def test_handoff_between_authorization_and_commit_never_reaches_adapter():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    original_validate=bridge.controller_authority_gate.validate
    handed_off=False
    def validate_then_handoff(**kwargs):
        nonlocal handed_off
        decision=original_validate(**kwargs)
        if decision is ControllerAuthorityDecision.ALLOW and not handed_off:
            authority.handoff(current_lease=active,next_controller_id="phone-b",now=now+0.01,ttl_seconds=30.0)
            handed_off=True
        return decision
    bridge.controller_authority_gate.validate=validate_then_handoff
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_command_proof=valid,now=now)
    assert result.status=="REJECTED"
    assert getattr(result.rejection,"name",result.rejection)=="CONTROLLER_FENCE_STALE"
    assert bridge.adapter.calls==0


@pytest.mark.asyncio
async def test_tampered_remote_controller_result_never_reaches_adapter():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    remote_key=P256AuthorityKeyPair.generate("remote-p256-controller-authority")
    request=AtomicControllerRequest(operation="acquire",request_id="remote-bridge-acquire",resource_id=active.resource_id,controller_id=active.controller_id,controller_key_id=phone.key_id,current_fencing_token=0,requested_ttl_seconds=active.expires_at-active.issued_at,challenge="remote-bridge-challenge")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=active.fencing_token,issued_at=active.issued_at,expires_at=active.expires_at,signing_key=remote_key)
    proof_unsigned=SignedControllerCommandProof(grant_digest=sha256(result.canonical_bytes).hexdigest(),command_id="remote-bridge-command-1",command_sequence=1,action_digest=sha256(intent.canonical_bytes).hexdigest(),controller_key_id=phone.key_id)
    proof=replace(proof_unsigned,signature=phone.sign(proof_unsigned.canonical_bytes))
    bridge.controller_authority_gate._remote_result_verifier=RemoteControllerResultVerifier({remote_key.key_id:remote_key.public_verifier})
    tampered=replace(result,fencing_token=result.fencing_token+1)
    rejected=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_request=request,controller_result=tampered,controller_command_proof=proof,now=now)
    assert rejected.status=="REJECTED"
    assert rejected.rejection is ControllerAuthorityDecision.GRANT_REJECTED
    assert bridge.adapter.calls==0


@pytest.mark.asyncio
async def test_valid_remote_controller_result_executes_once_and_replay_is_blocked():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    remote_key=P256AuthorityKeyPair.generate("remote-p256-controller-authority")
    request=AtomicControllerRequest(operation="acquire",request_id="remote-bridge-valid",resource_id=active.resource_id,controller_id=active.controller_id,controller_key_id=phone.key_id,current_fencing_token=0,requested_ttl_seconds=active.expires_at-active.issued_at,challenge="remote-bridge-valid-challenge")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=active.fencing_token,issued_at=active.issued_at,expires_at=active.expires_at,signing_key=remote_key)
    proof_unsigned=SignedControllerCommandProof(grant_digest=sha256(result.canonical_bytes).hexdigest(),command_id="remote-bridge-valid-command",command_sequence=1,action_digest=sha256(intent.canonical_bytes).hexdigest(),controller_key_id=phone.key_id)
    proof=replace(proof_unsigned,signature=phone.sign(proof_unsigned.canonical_bytes))
    bridge.controller_authority_gate._remote_result_verifier=RemoteControllerResultVerifier({remote_key.key_id:remote_key.public_verifier})
    accepted=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_request=request,controller_result=result,controller_command_proof=proof,now=now)
    assert accepted.status=="EXECUTED"
    assert bridge.adapter.calls==1
    assert bridge.adapter.last_intent.controller_resource_id==result.resource_id
    assert bridge.adapter.last_intent.controller_id==result.controller_id
    assert bridge.adapter.last_intent.controller_fencing_token==result.fencing_token
    replay=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_request=request,controller_result=result,controller_command_proof=proof,now=now)
    assert replay.status=="REJECTED"
    assert replay.rejection is ControllerAuthorityDecision.REPLAYED_SEQUENCE
    assert bridge.adapter.calls==1


@pytest.mark.asyncio
async def test_remote_handoff_between_authorization_and_commit_never_reaches_adapter():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    remote_key=P256AuthorityKeyPair.generate("remote-p256-controller-authority")
    request=AtomicControllerRequest(operation="acquire",request_id="remote-bridge-handoff-race",resource_id=active.resource_id,controller_id=active.controller_id,controller_key_id=phone.key_id,current_fencing_token=0,requested_ttl_seconds=active.expires_at-active.issued_at,challenge="remote-bridge-handoff-race-challenge")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=active.fencing_token,issued_at=active.issued_at,expires_at=active.expires_at,signing_key=remote_key)
    proof_unsigned=SignedControllerCommandProof(grant_digest=sha256(result.canonical_bytes).hexdigest(),command_id="remote-bridge-handoff-race-command",command_sequence=1,action_digest=sha256(intent.canonical_bytes).hexdigest(),controller_key_id=phone.key_id)
    proof=replace(proof_unsigned,signature=phone.sign(proof_unsigned.canonical_bytes))
    bridge.controller_authority_gate._remote_result_verifier=RemoteControllerResultVerifier({remote_key.key_id:remote_key.public_verifier})
    original_validate_remote=bridge.controller_authority_gate.validate_remote
    handed_off=False
    def validate_then_handoff(**kwargs):
        nonlocal handed_off
        decision=original_validate_remote(**kwargs)
        if decision is ControllerAuthorityDecision.ALLOW and not handed_off:
            authority.handoff(current_lease=active,next_controller_id="phone-b",now=now+0.01,ttl_seconds=30.0)
            handed_off=True
        return decision
    bridge.controller_authority_gate.validate_remote=validate_then_handoff
    rejected=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_request=request,controller_result=result,controller_command_proof=proof,now=now)
    assert rejected.status=="REJECTED"
    assert getattr(rejected.rejection,"name",rejected.rejection)=="CONTROLLER_FENCE_STALE"
    assert bridge.adapter.calls==0


@pytest.mark.asyncio
async def test_partial_mixed_and_unconfigured_remote_authority_never_reach_adapter():
    bridge,intent,lease,physical,snapshot,grant,valid,forged,now,phone,authority,active=_environment()
    remote_key=P256AuthorityKeyPair.generate("remote-p256-controller-authority")
    request=AtomicControllerRequest(operation="acquire",request_id="remote-bridge-routing",resource_id=active.resource_id,controller_id=active.controller_id,controller_key_id=phone.key_id,current_fencing_token=0,requested_ttl_seconds=active.expires_at-active.issued_at,challenge="remote-bridge-routing-challenge")
    result=SignedAtomicControllerResult.issue(request=request,fencing_token=active.fencing_token,issued_at=active.issued_at,expires_at=active.expires_at,signing_key=remote_key)
    proof_unsigned=SignedControllerCommandProof(grant_digest=sha256(result.canonical_bytes).hexdigest(),command_id="remote-bridge-routing-command",command_sequence=1,action_digest=sha256(intent.canonical_bytes).hexdigest(),controller_key_id=phone.key_id)
    proof=replace(proof_unsigned,signature=phone.sign(proof_unsigned.canonical_bytes))
    bridge.controller_authority_gate._remote_result_verifier=RemoteControllerResultVerifier({remote_key.key_id:remote_key.public_verifier})
    missing_result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_request=request,controller_command_proof=proof,now=now)
    assert missing_result.status=="REJECTED"
    assert missing_result.rejection=="CONTROLLER_AUTHORITY_REQUIRED"
    assert bridge.adapter.calls==0
    missing_request=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_result=result,controller_command_proof=proof,now=now)
    assert missing_request.status=="REJECTED"
    assert missing_request.rejection=="CONTROLLER_AUTHORITY_REQUIRED"
    assert bridge.adapter.calls==0
    mixed=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_grant=grant,controller_request=request,controller_result=result,controller_command_proof=proof,now=now)
    assert mixed.status=="REJECTED"
    assert mixed.rejection=="CONTROLLER_AUTHORITY_INVALID"
    assert bridge.adapter.calls==0
    unconfigured=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter)
    rejected=await unconfigured.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,controller_request=request,controller_result=result,controller_command_proof=proof,now=now)
    assert rejected.status=="REJECTED"
    assert rejected.rejection=="CONTROLLER_AUTHORITY_UNCONFIGURED"
    assert bridge.adapter.calls==0
