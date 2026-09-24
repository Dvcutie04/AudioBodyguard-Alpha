from src.control.capability_lease import SignedCapabilityLease
from src.control.controller_bound_intent_firewall import ControllerBoundIntentFirewall, ControllerBoundRejectionCode
from src.control.controller_bound_intent_issuer import ControllerBoundIntentIssuer
from src.control.controller_lease_evidence import SignedControllerLeaseEvidence
from src.control.crypto_identity import KeyPair
from src.extensions.normalization import NormalizedCandidate


def _environment():
    from dataclasses import replace
    policy_key=KeyPair.generate("aqss-policy-authority")
    controller_key=KeyPair.generate("aqss-controller-authority")
    capability_data=dict(device_id="device-tv-living-room",capability_digest="capability-digest-7",firmware_identity="fw-1",protocol_version="AQSS-1",issued_at=90.0,expires_at=200.0,nonce="capability-nonce-7",issuer_id=policy_key.key_id)
    capability_unsigned=SignedCapabilityLease(**capability_data,signature="")
    capability=SignedCapabilityLease(**capability_data,signature=policy_key.sign(capability_unsigned.canonical_bytes))
    controller_unsigned=SignedControllerLeaseEvidence(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,issued_at=100.0,expires_at=130.0,issuer_id=controller_key.key_id,nonce="controller-nonce-7",scope=("SET_VOLUME",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id="device-tv-living-room",operation="SET_VOLUME",parameters={"volume":25})
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-digest-7",intent_id="intent-controller-firewall-7",transaction_id="transaction-controller-firewall-7",nonce="intent-nonce-controller-firewall-7",created_at=110.0,expires_at=120.0)
    firewall=ControllerBoundIntentFirewall(policy_verifiers={policy_key.key_id:policy_key.public_verifier},controller_verifiers={controller_key.key_id:controller_key.public_verifier})
    return firewall,intent,capability,controller,policy_key,controller_key


def test_controller_bound_firewall_allows_once_then_rejects_replay():
    firewall,intent,capability,controller,*_=_environment()
    assert firewall.validate(intent,capability,controller,now=110.0) is intent
    assert firewall.validate(intent,capability,controller,now=111.0) is ControllerBoundRejectionCode.REPLAY


def test_controller_bound_firewall_rejects_every_binding_substitution_without_consuming_nonce():
    from dataclasses import replace
    firewall,intent,capability,controller,policy_key,controller_key=_environment()
    alterations=(
        replace(intent,resource_id="tv:bedroom",signature=""),
        replace(intent,controller_id="phone-b",signature=""),
        replace(intent,controller_lease_digest="controller-evidence-attacker",signature=""),
        replace(intent,fencing_token=8,signature=""),
    )
    for altered in alterations:
        signed=replace(altered,signature=policy_key.sign(altered.canonical_bytes))
        assert firewall.validate(signed,capability,controller,now=110.0) is ControllerBoundRejectionCode.CONTROLLER_BINDING_MISMATCH
    transplanted_unsigned=replace(controller,resource_id="tv:bedroom",controller_id="phone-b",fencing_token=8,nonce="controller-nonce-8",signature="")
    transplanted=replace(transplanted_unsigned,signature=controller_key.sign(transplanted_unsigned.canonical_bytes))
    assert firewall.validate(intent,capability,transplanted,now=110.0) is ControllerBoundRejectionCode.CONTROLLER_BINDING_MISMATCH
    assert firewall._seen_nonces==set()
    assert firewall.validate(intent,capability,controller,now=110.0) is intent


def test_controller_bound_firewall_rejects_signature_lease_device_and_scope_failures_without_consuming_nonce():
    from dataclasses import replace
    firewall,intent,capability,controller,policy_key,controller_key=_environment()
    tampered_intent=replace(intent,parameters={"volume":99})
    assert firewall.validate(tampered_intent,capability,controller,now=110.0) is ControllerBoundRejectionCode.POLICY_SIGNATURE_INVALID
    bad_capability=replace(capability,capability_digest="attacker-capability")
    assert firewall.validate(intent,bad_capability,controller,now=110.0) is ControllerBoundRejectionCode.CAPABILITY_SIGNATURE_INVALID
    wrong_device_unsigned=replace(intent,device_id="device-tv-bedroom",signature="")
    wrong_device=replace(wrong_device_unsigned,signature=policy_key.sign(wrong_device_unsigned.canonical_bytes))
    assert firewall.validate(wrong_device,capability,controller,now=110.0) is ControllerBoundRejectionCode.DEVICE_MISMATCH
    wrong_capability_unsigned=replace(intent,capability_lease_digest="attacker-capability-digest",signature="")
    wrong_capability=replace(wrong_capability_unsigned,signature=policy_key.sign(wrong_capability_unsigned.canonical_bytes))
    assert firewall.validate(wrong_capability,capability,controller,now=110.0) is ControllerBoundRejectionCode.CAPABILITY_MISMATCH
    tampered_controller=replace(controller,controller_id="phone-attacker")
    assert firewall.validate(intent,capability,tampered_controller,now=110.0) is ControllerBoundRejectionCode.CONTROLLER_SIGNATURE_INVALID
    outside_scope_unsigned=replace(intent,operation="POWER_OFF",signature="")
    outside_scope=replace(outside_scope_unsigned,signature=policy_key.sign(outside_scope_unsigned.canonical_bytes))
    assert firewall.validate(outside_scope,capability,controller,now=110.0) is ControllerBoundRejectionCode.SCOPE_MISMATCH
    rogue_key=KeyPair.generate("rogue-controller-authority")
    rogue_unsigned=replace(controller,issuer_id=rogue_key.key_id,nonce="rogue-controller-nonce",signature="")
    rogue=replace(rogue_unsigned,signature=rogue_key.sign(rogue_unsigned.canonical_bytes))
    assert firewall.validate(intent,capability,rogue,now=110.0) is ControllerBoundRejectionCode.CONTROLLER_ISSUER_UNKNOWN
    assert firewall._seen_nonces==set()
    assert firewall.validate(intent,capability,controller,now=110.0) is intent


def test_controller_bound_firewall_rejects_invalid_time_inputs_without_consuming_nonce():
    firewall,intent,capability,controller,*_=_environment()
    for invalid_now in (True,float("nan"),float("inf"),float("-inf")):
        assert firewall.validate(intent,capability,controller,now=invalid_now) is ControllerBoundRejectionCode.INVALID_INPUT
    assert firewall.validate(intent,capability,controller,now=109.999) is ControllerBoundRejectionCode.NOT_YET_VALID
    assert firewall.validate(intent,capability,controller,now=120.0) is ControllerBoundRejectionCode.EXPIRED
    assert firewall._seen_nonces==set()
    assert firewall.validate(intent,capability,controller,now=110.0) is intent


def test_controller_bound_firewall_concurrent_replay_allows_exactly_once():
    import threading
    firewall,intent,capability,controller,*_=_environment()
    start=threading.Barrier(9)
    result_lock=threading.Lock()
    results=[]

    def validate_once():
        start.wait(timeout=5.0)
        result=firewall.validate(intent,capability,controller,now=110.0)
        with result_lock:
            results.append(result)

    threads=[threading.Thread(target=validate_once) for _ in range(8)]
    for thread in threads:
        thread.start()
    start.wait(timeout=5.0)
    for thread in threads:
        thread.join(timeout=5.0)
    assert all(not thread.is_alive() for thread in threads)
    assert sum(result is intent for result in results)==1
    assert results.count(ControllerBoundRejectionCode.REPLAY)==7
    assert firewall._seen_nonces=={(intent.issuer_id,intent.nonce)}


def test_controller_bound_firewall_rejects_signed_stale_fence_after_handoff_without_consuming_nonce():
    from dataclasses import replace
    from src.control.active_controller_lease import ActiveControllerLeaseAuthority
    policy_key=KeyPair.generate("aqss-policy-fence-authority")
    controller_key=KeyPair.generate("aqss-controller-fence-authority")
    capability_data=dict(device_id="device-tv-living-room",capability_digest="capability-fence",firmware_identity="fw-1",protocol_version="AQSS-1",issued_at=90.0,expires_at=200.0,nonce="capability-fence-nonce",issuer_id=policy_key.key_id)
    capability_unsigned=SignedCapabilityLease(**capability_data,signature="")
    capability=replace(capability_unsigned,signature=policy_key.sign(capability_unsigned.canonical_bytes))
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    controller_unsigned=SignedControllerLeaseEvidence(resource_id=first.resource_id,controller_id=first.controller_id,fencing_token=first.fencing_token,issued_at=first.issued_at,expires_at=first.expires_at,issuer_id=controller_key.key_id,nonce="controller-fence-nonce",scope=("SET_VOLUME",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id=capability.device_id,operation="SET_VOLUME",parameters={"volume":25})
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-fence",intent_id="intent-stale-fence",transaction_id="transaction-stale-fence",nonce="intent-stale-fence-nonce",created_at=100.5,expires_at=120.0)
    firewall=ControllerBoundIntentFirewall(policy_verifiers={policy_key.key_id:policy_key.public_verifier},controller_verifiers={controller_key.key_id:controller_key.public_verifier},active_controller_authority=authority)
    allowed_unsigned=replace(intent,intent_id="intent-active-fence",transaction_id="transaction-active-fence",nonce="intent-active-fence-nonce",signature="")
    allowed_intent=replace(allowed_unsigned,signature=policy_key.sign(allowed_unsigned.canonical_bytes))
    assert firewall.validate(allowed_intent,capability,controller,now=100.75) is allowed_intent
    second=authority.handoff(current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    assert second.fencing_token==first.fencing_token+1
    assert firewall.validate(intent,capability,controller,now=102.0) is ControllerBoundRejectionCode.STALE_FENCE
    assert firewall._seen_nonces=={(allowed_intent.issuer_id,allowed_intent.nonce)}
    assert (intent.issuer_id,intent.nonce) not in firewall._seen_nonces


def test_endpoint_admission_binds_signed_volume_to_physical_request():
    import hashlib
    import pytest
    from dataclasses import replace
    from src.device_fabric.contracts import AuthorizedActionIntent,DeviceState
    from src.device_fabric.endpoint_action_admission import EndpointActionVerifier
    _,intent,cap,ev,pk,ck=_environment()
    before=DeviceState()
    signed=replace(intent,expected_pre_state_digest=before.state_digest,signature="")
    signed=replace(signed,signature=pk.sign(signed.canonical_bytes))
    action=AuthorizedActionIntent(intent_id=signed.intent_id,lease_id=cap.payload_digest,action="set_volume",device_id=signed.device_id,operation="set_volume",target_state=DeviceState(volume=25),expected_pre_state=before,authorization_digest=hashlib.sha256(signed.canonical_bytes).hexdigest(),deadline_at=signed.expires_at,transaction_id=signed.transaction_id,capability_digest=cap.payload_digest,controller_resource_id=signed.resource_id,controller_id=signed.controller_id,controller_fencing_token=signed.fencing_token)
    verifier=EndpointActionVerifier(policy_verifiers={pk.key_id:pk.public_verifier},controller_verifiers={ck.key_id:ck.public_verifier})
    def admit(si,act):
        return verifier.admit(signed_intent=si,capability_lease=cap,controller_evidence=ev,authorized_intent=act,now=110.0)
    for altered in (replace(action,target_state=DeviceState(volume=99)),replace(action,authorization_digest="forged"),replace(action,controller_fencing_token=8),replace(action,expected_pre_state=DeviceState(volume=5))):
        with pytest.raises(ValueError,match="endpoint action"):
            admit(signed,altered)
    with pytest.raises(ValueError,match="endpoint action"):
        admit(replace(signed,parameters={"volume":99}),action)
    assert admit(signed,action)==action
