import pytest
from dataclasses import replace

from src.control.capability_lease import SignedCapabilityLease
from src.control.controller_bound_intent_firewall import ControllerBoundIntentFirewall, ControllerBoundRejectionCode
from src.control.controller_bound_intent_issuer import ControllerBoundIntentIssuer
from src.control.controller_lease_evidence import SignedControllerLeaseEvidence
from src.control.crypto_identity import KeyPair
from src.control.device_fabric_bridge import Gen3DeviceFabricBridge
from src.device_fabric.contracts import CapabilityLease, DeviceState, PhysicalSnapshot
from src.extensions.normalization import NormalizedCandidate


@pytest.mark.asyncio
async def test_controller_bound_bridge_rejects_invalid_controller_evidence_before_physical_commit():
    policy_key=KeyPair.generate("aqss-policy-authority")
    controller_key=KeyPair.generate("aqss-controller-authority")
    capability_data=dict(device_id="device-tv-living-room",capability_digest="capability-digest-7",firmware_identity="fw-1",protocol_version="AQSS-1",issued_at=90.0,expires_at=200.0,nonce="capability-nonce-7",issuer_id=policy_key.key_id)
    capability_unsigned=SignedCapabilityLease(**capability_data,signature="")
    capability=replace(capability_unsigned,signature=policy_key.sign(capability_unsigned.canonical_bytes))
    controller_unsigned=SignedControllerLeaseEvidence(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,issued_at=100.0,expires_at=130.0,issuer_id=controller_key.key_id,nonce="controller-nonce-7",scope=("SET_VOLUME",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id=capability.device_id,operation="SET_VOLUME",parameters={"volume":25})
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-digest-7",intent_id="intent-controller-bridge-7",transaction_id="transaction-controller-bridge-7",nonce="intent-nonce-controller-bridge-7",created_at=110.0,expires_at=120.0)
    from src.control.active_controller_lease import ActiveControllerLeaseAuthority
    authority=ActiveControllerLeaseAuthority()
    for index in range(6):
        authority.acquire(resource_id="tv:living-room",controller_id=f"prior-phone-{index}",now=40.0+(index*10.0),ttl_seconds=10.0)
    active=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    assert active.fencing_token==controller.fencing_token
    firewall=ControllerBoundIntentFirewall(policy_verifiers={policy_key.key_id:policy_key.public_verifier},controller_verifiers={controller_key.key_id:controller_key.public_verifier},active_controller_authority=authority)
    class CountingAdapter:
        class Device:
            class Identity:
                device_id="device-tv-living-room"
            identity=Identity()
            state=DeviceState()
        device=Device()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge=Gen3DeviceFabricBridge(firewall,adapter)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=adapter.device.state,epoch=0,observed_at=110.0)
    missing_evidence=await bridge.authorize_and_commit(intent,capability,physical,snapshot,adapter.device.state,now=110.0)
    assert missing_evidence.status=="REJECTED"
    assert missing_evidence.rejection is ControllerBoundRejectionCode.CONTROLLER_EVIDENCE_REQUIRED
    assert adapter.calls==0
    assert firewall._seen_nonces==set()
    tampered_controller=replace(controller,controller_id="phone-attacker")
    result=await bridge.authorize_and_commit(intent,capability,physical,snapshot,adapter.device.state,controller_evidence=tampered_controller,now=110.0)
    assert result.status=="REJECTED"
    assert result.rejection is ControllerBoundRejectionCode.CONTROLLER_SIGNATURE_INVALID
    assert adapter.calls==0
    successor=authority.handoff(current_lease=active,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    assert successor.fencing_token==controller.fencing_token+1
    stale_result=await bridge.authorize_and_commit(intent,capability,physical,snapshot,adapter.device.state,controller_evidence=controller,now=110.0)
    assert stale_result.status=="REJECTED"
    assert stale_result.rejection is ControllerBoundRejectionCode.STALE_FENCE
    assert adapter.calls==0
    assert firewall._seen_nonces==set()


@pytest.mark.asyncio
async def test_controller_bound_bridge_executes_valid_intent_through_physical_commit():
    import time
    from src.device_fabric.mocks.mock_tv import MockTVAdapter
    current=time.time()
    policy_key=KeyPair.generate("aqss-policy-authority-live")
    controller_key=KeyPair.generate("aqss-controller-authority-live")
    capability_data=dict(device_id="device-tv-living-room",capability_digest="capability-digest-live",firmware_identity="fw-1",protocol_version="AQSS-1",issued_at=current-10.0,expires_at=current+60.0,nonce="capability-nonce-live",issuer_id=policy_key.key_id)
    capability_unsigned=SignedCapabilityLease(**capability_data,signature="")
    capability=replace(capability_unsigned,signature=policy_key.sign(capability_unsigned.canonical_bytes))
    controller_unsigned=SignedControllerLeaseEvidence(resource_id="tv:living-room",controller_id="phone-a",fencing_token=8,issued_at=current-5.0,expires_at=current+30.0,issuer_id=controller_key.key_id,nonce="controller-nonce-live",scope=("SET_VOLUME",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id=capability.device_id,operation="SET_VOLUME",parameters={"volume":25.0})
    authorized_pre=DeviceState(power=False,volume=10.0,muted=False,input_source="HDMI_1")
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-digest-live",intent_id="intent-controller-bridge-live",transaction_id="transaction-controller-bridge-live",nonce="intent-nonce-controller-bridge-live",created_at=current-1.0,expires_at=current+20.0,expected_pre_state_digest=authorized_pre.state_digest)
    firewall=ControllerBoundIntentFirewall(policy_verifiers={policy_key.key_id:policy_key.public_verifier},controller_verifiers={controller_key.key_id:controller_key.public_verifier})
    adapter=MockTVAdapter(capability.device_id)
    bridge=Gen3DeviceFabricBridge(firewall,adapter)
    pre=adapter.device.state
    assert intent.expected_pre_state_digest==pre.state_digest==authorized_pre.state_digest
    physical=CapabilityLease(device_id=intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=current)
    result=await bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,controller_evidence=controller,now=current)
    assert result.status=="EXECUTED"
    assert result.authorization_digest==bridge._authorization_digest(intent)
    assert result.transaction_id==intent.transaction_id
    assert result.capability_digest==capability.payload_digest
    assert adapter.device.state.volume==25.0
    assert adapter._executed_intents=={intent.intent_id}
    assert adapter._highest_controller_fences=={controller.resource_id:(controller.fencing_token,controller.controller_id)}
    replay=await bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,controller_evidence=controller,now=current)
    assert replay.status=="REJECTED"
    assert replay.rejection is ControllerBoundRejectionCode.REPLAY
    assert adapter._executed_intents=={intent.intent_id}
    assert adapter.device.state.volume==25.0


@pytest.mark.asyncio
async def test_controller_bound_bridge_rejects_signed_precondition_drift_before_adapter():
    import time
    current=time.time()
    policy_key=KeyPair.generate("aqss-policy-precondition")
    controller_key=KeyPair.generate("aqss-controller-precondition")
    capability_unsigned=SignedCapabilityLease(device_id="device-tv-precondition",capability_digest="capability-precondition",firmware_identity="fw-1",protocol_version="AQSS-1",issued_at=current-10.0,expires_at=current+60.0,nonce="capability-precondition-nonce",issuer_id=policy_key.key_id,signature="")
    capability=replace(capability_unsigned,signature=policy_key.sign(capability_unsigned.canonical_bytes))
    controller_unsigned=SignedControllerLeaseEvidence(resource_id="tv:precondition",controller_id="phone-a",fencing_token=1,issued_at=current-5.0,expires_at=current+30.0,issuer_id=controller_key.key_id,nonce="controller-precondition-nonce",scope=("SET_VOLUME",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    authorized_pre=DeviceState(volume=5.0)
    drifted_pre=DeviceState(volume=10.0)
    candidate=NormalizedCandidate(extension_id="aqss.ui.media",target_id=capability.device_id,operation="SET_VOLUME",parameters={"volume":25.0})
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-precondition",intent_id="intent-precondition",transaction_id="transaction-precondition",nonce="intent-precondition-nonce",created_at=current-1.0,expires_at=current+20.0,expected_pre_state_digest=authorized_pre.state_digest)
    firewall=ControllerBoundIntentFirewall(policy_verifiers={policy_key.key_id:policy_key.public_verifier},controller_verifiers={controller_key.key_id:controller_key.public_verifier})
    class CountingAdapter:
        calls=0
        class Device:
            class Identity:
                device_id="device-tv-precondition"
            identity=Identity()
            state=drifted_pre
        device=Device()
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("signed precondition drift reached adapter")
    adapter=CountingAdapter()
    bridge=Gen3DeviceFabricBridge(firewall,adapter)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=drifted_pre,epoch=0,observed_at=current)
    result=await bridge.authorize_and_commit(intent,capability,physical,snapshot,authorized_pre,controller_evidence=controller,now=current)
    assert result.status=="REJECTED"
    assert getattr(result.rejection,"name",result.rejection)=="PRECONDITION_DRIFT"
    assert result.receipt is None
    assert result.verification is None
    assert adapter.calls==0


@pytest.mark.asyncio
async def test_bridge_wires_controller_fence_into_physical_commit_boundary():
    import time
    from src.control.active_controller_lease import ActiveControllerLeaseAuthority
    from src.device_fabric.contracts import ActuationReceipt,ActuationStatus
    current=time.time()
    policy_key=KeyPair.generate("aqss-policy-boundary")
    controller_key=KeyPair.generate("aqss-controller-boundary")
    capability_unsigned=SignedCapabilityLease(device_id="device-tv-boundary",capability_digest="capability-boundary",firmware_identity="fw-1",protocol_version="AQSS-1",issued_at=current-10.0,expires_at=current+60.0,nonce="capability-boundary-nonce",issuer_id=policy_key.key_id,signature="")
    capability=replace(capability_unsigned,signature=policy_key.sign(capability_unsigned.canonical_bytes))
    authority=ActiveControllerLeaseAuthority()
    active=authority.acquire(resource_id="tv:boundary",controller_id="phone-a",now=current-5.0,ttl_seconds=30.0)
    controller_unsigned=SignedControllerLeaseEvidence(resource_id=active.resource_id,controller_id=active.controller_id,fencing_token=active.fencing_token,issued_at=active.issued_at,expires_at=active.expires_at,issuer_id=controller_key.key_id,nonce="controller-boundary-nonce",scope=("SET_VOLUME",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    candidate=NormalizedCandidate(extension_id="aqss.ai.primary",target_id=capability.device_id,operation="SET_VOLUME",parameters={"volume":25.0})
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1")
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="policy-boundary",intent_id="intent-boundary",transaction_id="transaction-boundary",nonce="intent-boundary-nonce",created_at=current-1.0,expires_at=current+20.0)
    firewall=ControllerBoundIntentFirewall(policy_verifiers={policy_key.key_id:policy_key.public_verifier},controller_verifiers={controller_key.key_id:controller_key.public_verifier},active_controller_authority=authority)
    class Adapter:
        calls=0
        class Device:
            handed_off=False
            state=DeviceState()
            @property
            def identity(self):
                if not self.handed_off:
                    authority.handoff(current_lease=active,next_controller_id="phone-b",now=current,ttl_seconds=30.0)
                    self.handed_off=True
                class Identity:
                    device_id="device-tv-boundary"
                return Identity()
        device=Device()
        async def execute_intent(self,intent,transaction_digest=None,capability_digest=None):
            self.calls+=1
            return ActuationReceipt(receipt_id="unexpected",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=transaction_digest or "",capability_digest=capability_digest or "")
    adapter=Adapter()
    bridge=Gen3DeviceFabricBridge(firewall,adapter)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=adapter.device.state,epoch=0,observed_at=current)
    result=await bridge.authorize_and_commit(intent,capability,physical,snapshot,adapter.device.state,controller_evidence=controller,now=current)
    assert result.status=="REJECTED"
    assert result.rejection.name=="CONTROLLER_FENCE_STALE"
    assert adapter.calls==0
    assert adapter.device.state.volume==0

@pytest.mark.asyncio
async def test_evidence_bound_intro_skip_executes_once_through_controller_fenced_physical_commit():
    import time
    from src.control.active_controller_lease import ActiveControllerLeaseAuthority
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory,DirectiveLifecycleStage
    from src.edge.media_segment_observation import MediaAutomationCandidateAdmission,MediaAutomationCandidateNormalizer,MediaAutomationEligibilityGate,MediaEvidenceSource,MediaSegmentKind,MediaSegmentObservation,MediaSegmentProposalAdapter
    from src.device_fabric.mocks.mock_tv import MockTVAdapter

    current=time.time()
    observation=MediaSegmentObservation(observation_id="observation-controller-1",profile_id="profile-1",device_id="device-tv-living-room",provider_id="provider-1",content_id="series-alpha-episode-1",segment_kind=MediaSegmentKind.INTRO,source=MediaEvidenceSource.METADATA,observed_monotonic=100.0,confidence=1.0,segment_start_seconds=0.0,segment_end_seconds=45.0,evidence_digest="a"*64)
    memory=AdaptiveDirectiveMemory(max_entries=16)
    proposal_adapter=MediaSegmentProposalAdapter(memory)
    key=proposal_adapter.context_key(observation)
    memory.remember(key,action="skip",pinned=True)
    for stage in (DirectiveLifecycleStage.SUGGEST,DirectiveLifecycleStage.SHADOW,DirectiveLifecycleStage.AUTOMATE):
        memory.advance_lifecycle(key,target=stage)
    proposal=proposal_adapter.propose(observation,context_match=1.0,now_monotonic=100.1,max_age_seconds=0.5)
    gate=MediaAutomationEligibilityGate(memory,proposal_adapter)
    normalizer=MediaAutomationCandidateNormalizer(gate)
    candidate=normalizer.normalize(observation,proposal,now_monotonic=100.1,max_age_seconds=0.5)
    assert candidate.operation=="SET_PLAYBACK_POSITION"

    policy_key=KeyPair.generate("aqss-media-policy")
    controller_key=KeyPair.generate("aqss-media-controller")
    capability_unsigned=SignedCapabilityLease(device_id=observation.device_id,capability_digest="media-playback-capability",firmware_identity="fw-1",protocol_version="AQSS-1",issued_at=current-10.0,expires_at=current+60.0,nonce="media-capability-nonce",issuer_id=policy_key.key_id,signature="")
    capability=replace(capability_unsigned,signature=policy_key.sign(capability_unsigned.canonical_bytes))
    authority=ActiveControllerLeaseAuthority()
    active=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=current-5.0,ttl_seconds=30.0)
    controller_unsigned=SignedControllerLeaseEvidence(resource_id=active.resource_id,controller_id=active.controller_id,fencing_token=active.fencing_token,issued_at=active.issued_at,expires_at=active.expires_at,issuer_id=controller_key.key_id,nonce="media-controller-nonce",scope=("SET_PLAYBACK_POSITION",))
    controller=replace(controller_unsigned,signature=controller_key.sign(controller_unsigned.canonical_bytes))
    candidate_admission=MediaAutomationCandidateAdmission(normalizer,observation,proposal,monotonic_clock=lambda:100.1,max_age_seconds=0.5)
    issuer=ControllerBoundIntentIssuer(policy_key,controller_verifiers={controller_key.key_id:controller_key.public_verifier},protocol_version="AQSS-1",candidate_admission=candidate_admission)
    intent=issuer.issue(candidate=candidate,capability_lease=capability,controller_evidence=controller,policy_digest="media-policy-digest",intent_id="intent-media-playback-1",transaction_id="transaction-media-playback-1",nonce="intent-media-playback-nonce",created_at=current-1.0,expires_at=current+20.0)
    firewall=ControllerBoundIntentFirewall(policy_verifiers={policy_key.key_id:policy_key.public_verifier},controller_verifiers={controller_key.key_id:controller_key.public_verifier},active_controller_authority=authority)
    adapter=MockTVAdapter(observation.device_id)
    commit_monotonic=[100.1]
    bridge=Gen3DeviceFabricBridge(firewall,adapter,monotonic_clock=lambda:commit_monotonic[0],monotonic_clock_domain_id=observation.clock_domain_id)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={"set_playback_position"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=current)
    expected=replace(pre,playback_position_seconds=45.0)
    class IndependentObserver:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time(),evidence_digest=observed_evidence_digest)
    observer=IndependentObserver()
    observed_evidence_digest="b"*64
    missing_domain_parameters=dict(intent.parameters)
    missing_domain_parameters.pop("evidence_clock_domain_id")
    missing_domain_unsigned=replace(intent,intent_id="intent-media-playback-missing-domain",parameters=missing_domain_parameters,nonce="intent-media-playback-missing-domain-nonce",transaction_id="transaction-media-playback-missing-domain",signature="")
    missing_domain_intent=replace(missing_domain_unsigned,signature=policy_key.sign(missing_domain_unsigned.canonical_bytes))
    missing_domain=await bridge.authorize_and_commit(missing_domain_intent,capability,physical,snapshot,pre,world_state_evidence_digest=observation.evidence_digest,post_state_observer=observer,observed_state_evidence_digest=observed_evidence_digest,controller_evidence=controller,now=current)
    assert missing_domain.status=="REJECTED"
    assert missing_domain.rejection=="MEDIA_EVIDENCE_CLOCK_DOMAIN_INVALID"
    assert observer.calls==0
    assert adapter._executed_intents==set()
    mismatched_bridge=Gen3DeviceFabricBridge(firewall,adapter,monotonic_clock=lambda:commit_monotonic[0],monotonic_clock_domain_id="process:mismatched-test-domain")
    domain_mismatch=await mismatched_bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,world_state_evidence_digest=observation.evidence_digest,post_state_observer=observer,observed_state_evidence_digest=observed_evidence_digest,controller_evidence=controller,now=current)
    assert domain_mismatch.status=="REJECTED"
    assert domain_mismatch.rejection=="MEDIA_EVIDENCE_CLOCK_DOMAIN_MISMATCH"
    assert observer.calls==0
    assert adapter._executed_intents==set()
    commit_monotonic[0]=99.9
    future=await bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,world_state_evidence_digest=observation.evidence_digest,post_state_observer=observer,observed_state_evidence_digest=observed_evidence_digest,controller_evidence=controller,now=current)
    assert future.status=="REJECTED"
    assert future.rejection=="MEDIA_EVIDENCE_FRESHNESS_INVALID"
    assert observer.calls==0
    assert adapter._executed_intents==set()
    commit_monotonic[0]=100.6
    stale=await bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,world_state_evidence_digest=observation.evidence_digest,post_state_observer=observer,observed_state_evidence_digest=observed_evidence_digest,controller_evidence=controller,now=current)
    assert stale.status=="REJECTED"
    assert stale.rejection=="MEDIA_EVIDENCE_EXPIRED"
    assert observer.calls==0
    assert adapter._executed_intents==set()
    commit_monotonic[0]=100.1
    invalid_observer=await bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,world_state_evidence_digest=observation.evidence_digest,post_state_observer=object(),observed_state_evidence_digest=observed_evidence_digest,controller_evidence=controller,now=current)
    assert invalid_observer.status=="REJECTED"
    assert invalid_observer.rejection=="MEDIA_POST_STATE_VERIFICATION_REQUIRED"
    assert observer.calls==0
    assert adapter._executed_intents==set()
    unverified=await bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,world_state_evidence_digest=observation.evidence_digest,controller_evidence=controller,now=current)
    assert unverified.status=="REJECTED"
    assert unverified.rejection=="MEDIA_POST_STATE_VERIFICATION_REQUIRED"
    assert observer.calls==0
    assert adapter._executed_intents==set()
    result=await bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,world_state_evidence_digest=observation.evidence_digest,post_state_observer=observer,observed_state_evidence_digest=observed_evidence_digest,controller_evidence=controller,now=current)
    assert result.status=="EXECUTED"
    assert observer.calls==1
    assert result.verification is not None
    assert result.verification.verification_status.name=="VERIFIED"
    assert result.verification.expected_state_digest==expected.state_digest
    assert result.verification.observed_state_digest==expected.state_digest
    assert result.verification.world_state_evidence_digest==observation.evidence_digest
    assert result.verification.observed_state_evidence_digest==observed_evidence_digest
    assert result.verification.world_state_epoch==0
    assert result.verification.observed_state_epoch==1
    assert result.verified_state is None
    assert adapter.device.state.playback_position_seconds==45.0
    assert adapter._executed_intents=={intent.intent_id}
    assert adapter._highest_controller_fences=={active.resource_id:(active.fencing_token,active.controller_id)}
    replay=await bridge.authorize_and_commit(intent,capability,physical,snapshot,pre,world_state_evidence_digest=observation.evidence_digest,post_state_observer=observer,observed_state_evidence_digest=observed_evidence_digest,controller_evidence=controller,now=current)
    assert replay.status=="REJECTED"
    assert replay.rejection is ControllerBoundRejectionCode.REPLAY
    assert observer.calls==1
    assert adapter._executed_intents=={intent.intent_id}
    assert adapter._executed_intents=={intent.intent_id}
    assert adapter.device.state.playback_position_seconds==45.0

