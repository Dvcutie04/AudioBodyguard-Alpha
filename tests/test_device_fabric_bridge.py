import time, pytest
from src.control.crypto_identity import KeyPair
from src.control.capability_lease import SignedCapabilityLease
from src.control.authorized_intent import SignedActionIntent
from src.control.intent_firewall import IntentFirewall, AuthRejectionCode
from src.control.device_fabric_bridge import Gen3DeviceFabricBridge
from src.control.media_control_verified_state import VerifiedMediaControlState
from src.control.media_control_prior_state import MediaControlPriorState
from src.control.media_control_undo_candidate import MediaControlUndoCandidate
from src.control.protection_supervisor import ProtectionState, ProtectionSupervisor
from src.control.protection_evidence import ProtectionEvidence, ProtectionEvidenceCoordinator, ProtectionRuntimeMode
from src.control.protection_path_assessment import ProtectionPathAssessment, ProtectionPathReason
from src.device_fabric.mocks.mock_tv import MockTVAdapter
from src.device_fabric.contracts import ActuationReceipt, ActuationStatus, DeviceState, CapabilityLease, PhysicalSnapshot, VerificationStatus
from src.device_fabric.precondition_gate import PreconditionResult
@pytest.fixture
def env():
    key=KeyPair.generate()
    firewall=IntentFirewall(trusted_verifiers={key.key_id:key.public_verifier})
    adapter=MockTVAdapter("tv_integration_node_1")
    now=time.time()
    ld=dict(device_id="tv_integration_node_1",capability_digest="cap_audio",firmware_identity="v1.0",protocol_version="1.0",issued_at=now,expires_at=now+60,nonce="lease_n",issuer_id=key.key_id)
    ls=key.sign(SignedCapabilityLease(**ld,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**ld,signature=ls)
    idata=dict(intent_id="bridge_01",device_id="tv_integration_node_1",operation="SET_VOLUME",parameters={"volume":55.0},issuer_id=key.key_id,policy_digest="policy",capability_lease_digest=lease.payload_digest,created_at=now,expires_at=now+30,nonce="intent_n",transaction_id="tx_bridge_01",protocol_version="1.0")
    sig=key.sign(SignedActionIntent(**idata,signature="").canonical_bytes)
    intent=SignedActionIntent(**idata,signature=sig)
    return Gen3DeviceFabricBridge(firewall,adapter),intent,lease,key
@pytest.mark.asyncio
async def test_bridge_executes(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    result=await bridge.authorize_and_execute(intent,lease,pre)
    assert result.status=="EXECUTED"
    assert result.receipt.device_id=="tv_integration_node_1"
    assert result.transaction_id=="tx_bridge_01"
    assert result.capability_digest==lease.payload_digest
    assert bridge.adapter.device.state.volume==55.0
@pytest.mark.asyncio
async def test_bridge_rejects_bad_lease(env):
    bridge,intent,lease,key=env
    d={k:v for k,v in lease.__dict__.items() if k!="signature"};d["capability_digest"]="forged";bad=SignedCapabilityLease(**d,signature=lease.signature)
    result=await bridge.authorize_and_execute(intent,bad,bridge.adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection=="LEASE_SIGNATURE_INVALID"
    assert bridge.adapter.device.state.volume!=55.0


@pytest.mark.asyncio
async def test_bridge_rejects_replay(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    first=await bridge.authorize_and_execute(intent,lease,pre)
    second=await bridge.authorize_and_execute(intent,lease,pre)
    assert first.status=="EXECUTED"
    assert second.status=="REJECTED"
    assert second.rejection==AuthRejectionCode.AUTH_REPLAY

@pytest.mark.asyncio
async def test_bridge_rejects_tampered_intent(env):
    bridge,intent,lease,key=env
    d={k:v for k,v in intent.__dict__.items() if k!="signature"};d["parameters"]={"volume":56.0}
    bad=SignedActionIntent(**d,signature=intent.signature)
    result=await bridge.authorize_and_execute(bad,lease,bridge.adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection==AuthRejectionCode.AUTH_SIGNATURE_INVALID

@pytest.mark.asyncio
async def test_bridge_rejects_wrong_device(env):
    bridge,intent,lease,key=env
    d={k:v for k,v in intent.__dict__.items() if k!="signature"};d["device_id"]="other_tv"
    sig=key.sign(SignedActionIntent(**d,signature="").canonical_bytes)
    bad=SignedActionIntent(**d,signature=sig)
    result=await bridge.authorize_and_execute(bad,lease,bridge.adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection==AuthRejectionCode.AUTH_DEVICE_MISMATCH

@pytest.mark.asyncio
async def test_bridge_propagates_commit_lineage(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="EXECUTED"
    assert result.authorization_digest==bridge._authorization_digest(intent)
    assert result.transaction_id==intent.transaction_id
    assert result.capability_digest==lease.payload_digest

@pytest.mark.asyncio
async def test_bridge_rejects_receipt_intent_mismatch(env):
    bridge,intent,lease,key=env
    class BadAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
        device=Dev()
        async def execute_intent(self,**kwargs):
            return ActuationReceipt(receipt_id="bad",intent_id="wrong",device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
    bridge.adapter=BadAdapter()
    result=await bridge.authorize_and_execute(intent,lease,DeviceState())
    assert result.status=="FAILED"
    assert result.rejection=="RECEIPT_INTENT_MISMATCH"

@pytest.mark.asyncio
async def test_bridge_rejects_receipt_device_mismatch(env):
    bridge,intent,lease,key=env
    class BadAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
        device=Dev()
        async def execute_intent(self,**kwargs):
            return ActuationReceipt(receipt_id="bad",intent_id=intent.intent_id,device_id="wrong",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
    bridge.adapter=BadAdapter()
    result=await bridge.authorize_and_execute(intent,lease,DeviceState())
    assert result.status=="FAILED"
    assert result.rejection=="RECEIPT_DEVICE_MISMATCH"

@pytest.mark.asyncio
async def test_bridge_handles_adapter_exception(env):
    bridge,intent,lease,key=env
    class BadAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        async def execute_intent(self,**kwargs):
            raise RuntimeError("adapter failure")
    bridge.adapter=BadAdapter()
    result=await bridge.authorize_and_execute(intent,lease,bridge.adapter.device.state)
    assert result.status=="FAILED"
    assert result.rejection.startswith("RuntimeError:")

@pytest.mark.asyncio
async def test_bridge_rejects_issuer_mismatch(env):
    bridge,intent,lease,key=env
    other=KeyPair.generate()
    d=dict(intent.__dict__); d["issuer_id"]=other.key_id
    d["signature"]=""
    sig=other.sign(SignedActionIntent(**d).canonical_bytes)
    d["signature"]=sig; forged=SignedActionIntent(**d)
    result=await bridge.authorize_and_execute(forged,lease,bridge.adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection=="ISSUER_MISMATCH"

@pytest.mark.asyncio
async def test_bridge_rejects_unsupported_operation(env):
    bridge,intent,lease,key=env
    d=dict(intent.__dict__); d["operation"]="DELETE_DEVICE"
    d["signature"]=""
    sig=key.sign(SignedActionIntent(**d).canonical_bytes)
    d["signature"]=sig
    forged=SignedActionIntent(**d)
    result=await bridge.authorize_and_execute(forged,lease,bridge.adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection
@pytest.mark.asyncio
async def test_bridge_unsupported_operation_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    d=dict(intent.__dict__); d["operation"]="DELETE_DEVICE"
    d["signature"]=""
    sig=key.sign(SignedActionIntent(**d).canonical_bytes)
    d["signature"]=sig
    forged=SignedActionIntent(**d)
    result=await bridge.authorize_and_execute(forged,lease,bridge.adapter.device.state)
    assert result.status=="REJECTED"
    assert adapter.calls==0
@pytest.mark.asyncio
async def test_bridge_malformed_operation_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    d=dict(intent.__dict__); d["operation"]=""
    d["signature"]=""
    sig=key.sign(SignedActionIntent(**d).canonical_bytes)
    d["signature"]=sig
    forged=SignedActionIntent(**d)
    result=await bridge.authorize_and_execute(forged,lease,bridge.adapter.device.state)
    assert result.status=="REJECTED"
    assert adapter.calls==0
@pytest.mark.asyncio
async def test_bridge_authorize_and_commit_reaches_physical_gate(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result is not None
    assert result.status=="EXECUTED"

@pytest.mark.asyncio
async def test_bridge_post_state_observer_not_called_on_epoch_drift_rejection(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=1)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not run")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert observer.calls==0
    assert result.status=="REJECTED"
    assert getattr(result.rejection,"name",result.rejection)=="EPOCH_DRIFT"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_rejects_epoch_drift_before_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=7)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=8,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.EPOCH_DRIFT
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_rejects_stale_world_state_before_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=4,max_world_state_age_ms=10)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=4,observed_at=time.time()-1.0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.WORLD_STATE_STALE
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_rejects_precondition_drift_before_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    snapshot_state=adapter.device.state
    expected_pre=DeviceState(volume=11)
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=3)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=snapshot_state,epoch=3,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,expected_pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.PRECONDITION_DRIFT
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_does_not_claim_success_when_post_state_is_wrong(env):
    bridge,intent,lease,key=env
    class LyingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="lying",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=LyingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    assert pre.state_digest!=expected.state_digest
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=pre,epoch=1,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"

@pytest.mark.asyncio
async def test_bridge_accepts_executed_when_post_state_matches_target(env):
    bridge,intent,lease,key=env
    class VerifyingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return ActuationReceipt(receipt_id="verified",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=VerifyingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="EXECUTED"
    assert result.rejection is None
    assert adapter.device.state.state_digest==bridge._translate_state(intent,pre).state_digest

def test_physical_verification_record_preserves_distinct_authorization_and_observation_epochs():
    from src.device_fabric.contracts import PhysicalVerificationRecord
    record=PhysicalVerificationRecord(world_state_epoch=3,observed_state_epoch=9)
    assert record.world_state_epoch==3
    assert record.observed_state_epoch==9

@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_can_mint_physical_verification(env):
    bridge,intent,lease,key=env
    class StaleLocalAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="independent-observation",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=StaleLocalAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            assert device_id=="tv_integration_node_1"
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==1
    assert adapter.device.state.state_digest!=expected.state_digest
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.observed_state_digest==expected.state_digest
    assert result.verification.verification_status==VerificationStatus.VERIFIED

@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_nan_observed_at_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class Adapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="nan-observation",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=Adapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=7,observed_at=float("nan"))
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None

@pytest.mark.asyncio
@pytest.mark.parametrize("observed_at",[float("inf"),float("-inf")])
async def test_bridge_independent_post_state_observer_infinite_observed_at_cannot_mint_verification(env,observed_at):
    bridge,intent,lease,key=env
    class Adapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="infinite-observation",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=Adapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=7,observed_at=observed_at)
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_future_skew_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class Adapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="future-skew-observation",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=Adapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0,max_clock_skew_ms=1000)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=7,observed_at=time.time()+2.0)
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_stale_observation_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class Adapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="stale-observation",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=Adapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0,max_world_state_age_ms=1000)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=7,observed_at=time.time()-2.0)
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_binds_observer_epoch_into_verification(env):
    bridge,intent,lease,key=env
    class StaleLocalAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="independent-observation",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=StaleLocalAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            assert device_id=="tv_integration_node_1"
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=7,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==1
    assert adapter.device.state.state_digest!=expected.state_digest
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.observed_state_digest==expected.state_digest
    assert result.verification.verification_status==VerificationStatus.VERIFIED
    assert result.verification.world_state_epoch==0
    assert result.verification.observed_state_epoch==7

@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_mismatch_overrides_adapter_local_state(env):
    bridge,intent,lease,key=env
    class Adapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return ActuationReceipt(receipt_id="observer-mismatch",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=Adapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=pre,epoch=0,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==1
    assert adapter.device.state.state_digest==expected.state_digest
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_post_state_observer_cancellation_propagates(env):
    import asyncio
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise asyncio.CancelledError()
    observer=Observer()
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert observer.calls==1

@pytest.mark.asyncio
async def test_bridge_post_state_observer_wrong_type_fails_closed(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return {"device_id":device_id}
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert observer.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_post_state_observer_wrong_device_fails_closed(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id="other_device",state=expected,epoch=0,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert observer.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_post_state_observer_exception_fails_closed_without_adapter_fallback(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    bridge.adapter.device.state=expected
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise RuntimeError("observation unavailable")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert observer.calls==1
    assert bridge.adapter.device.state.state_digest==expected.state_digest
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_fails_closed_when_post_state_is_unobservable(env):
    bridge,intent,lease,key=env
    class BlindAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="blind",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=BlindAdapter()
    bridge.adapter=adapter
    pre=DeviceState(volume=10)
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        return None
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"

@pytest.mark.asyncio
async def test_bridge_does_not_trust_committed_receipt_without_verification_evidence(env):
    bridge,intent,lease,key=env
    class PrematureCommitAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return ActuationReceipt(receipt_id="premature_commit",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.COMMITTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=PrematureCommitAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert adapter.device.state.state_digest==bridge._translate_state(intent,pre).state_digest
    assert result.status!="COMMITTED"

def test_bridge_result_has_physical_verification_evidence_slot():
    from src.control.device_fabric_bridge import BridgeResult
    fields=BridgeResult.__dataclass_fields__
    assert "verification" in fields

@pytest.mark.asyncio
async def test_bridge_verified_post_state_binds_physical_evidence(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.intent_id==intent.intent_id
    assert result.verification.device_id=="tv_integration_node_1"
    assert result.verification.receipt_id==result.receipt.receipt_id
    assert result.verification.expected_state_digest==expected.state_digest
    assert result.verification.observed_state_digest==expected.state_digest
    assert result.verification.verification_status==VerificationStatus.VERIFIED

@pytest.mark.asyncio
async def test_bridge_verification_binds_authorization_lineage(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.authorization_digest==result.authorization_digest
    assert result.verification.transaction_id==result.transaction_id
    assert result.verification.capability_digest==result.capability_digest

def test_production_code_does_not_call_legacy_authorize_and_execute():
    from pathlib import Path
    hits=[]
    for path in Path("src").rglob("*.py"):
        data=path.read_bytes()
        if b"authorize_and_execute(" in data and path.as_posix() != "src/control/device_fabric_bridge.py":
            hits.append(path.as_posix())
    assert hits==[]

@pytest.mark.asyncio
async def test_bridge_epoch_drift_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=1)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.EPOCH_DRIFT
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_stale_world_state_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0,max_world_state_age_ms=1)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time()-1.0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.WORLD_STATE_STALE
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_precondition_drift_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    snapshot_state=adapter.device.state
    expected_pre_state=DeviceState(volume=99.0)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=snapshot_state,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,expected_pre_state)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.PRECONDITION_DRIFT
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_physical_device_mismatch_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_WRONG",capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_capability_denied_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities=set(),authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.CAPABILITY_DENIED
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_auth_expired_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    from datetime import datetime, timezone, timedelta
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0,expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.AUTH_EXPIRED
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_converted_world_state_epoch_drift_never_reaches_adapter(env):
    from datetime import datetime, timezone
    from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot

    bridge,intent,lease,key=env

    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0

        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")

    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    world=WorldStateSnapshot(
        target_id=intent.device_id,
        epoch=61,
        observed_at=datetime.now(timezone.utc),
        state={
            "power":pre.power,
            "volume":pre.volume,
            "muted":pre.muted,
            "input_source":pre.input_source,
            "channel":pre.channel,
            "custom_state":dict(pre.custom_state),
        },
        evidence_digest="sha256:bridge-converted-epoch-evidence",
    )
    snapshot=to_physical_snapshot(world)
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=62,
    )

    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)

    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.EPOCH_DRIFT
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_converted_world_state_stale_never_reaches_adapter(env,monkeypatch):
    from datetime import datetime, timezone
    from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot

    bridge,intent,lease,key=env

    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0

        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")

    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    observed=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc)
    world=WorldStateSnapshot(
        target_id=intent.device_id,
        epoch=63,
        observed_at=observed,
        state={
            "power":pre.power,
            "volume":pre.volume,
            "muted":pre.muted,
            "input_source":pre.input_source,
            "channel":pre.channel,
            "custom_state":dict(pre.custom_state),
        },
        evidence_digest="sha256:bridge-converted-stale-evidence",
    )
    snapshot=to_physical_snapshot(world)
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=63,
        max_world_state_age_ms=1000,
    )
    monkeypatch.setattr("src.device_fabric.precondition_gate.time.time",lambda: observed.timestamp()+2.0)

    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)

    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.WORLD_STATE_STALE
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_converted_world_state_precondition_drift_never_reaches_adapter(env):
    from datetime import datetime, timezone
    from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot

    bridge,intent,lease,key=env

    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0

        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")

    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    world=WorldStateSnapshot(
        target_id=intent.device_id,
        epoch=64,
        observed_at=datetime.now(timezone.utc),
        state={
            "power":pre.power,
            "volume":pre.volume,
            "muted":pre.muted,
            "input_source":pre.input_source,
            "channel":pre.channel,
            "custom_state":dict(pre.custom_state),
        },
        evidence_digest="sha256:bridge-converted-precondition-evidence",
    )
    snapshot=to_physical_snapshot(world)
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=64,
    )
    expected_pre_state=DeviceState(
        power=pre.power,
        volume=99.0,
        muted=pre.muted,
        input_source=pre.input_source,
        channel=pre.channel,
        custom_state=dict(pre.custom_state),
    )

    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,expected_pre_state)

    assert expected_pre_state.state_digest!=snapshot.state_digest
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.PRECONDITION_DRIFT
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_converted_world_state_valid_path_executes_and_verifies(env):
    from datetime import datetime, timezone
    from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot

    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    world=WorldStateSnapshot(
        target_id=intent.device_id,
        epoch=65,
        observed_at=datetime.now(timezone.utc),
        state={
            "power":pre.power,
            "volume":pre.volume,
            "muted":pre.muted,
            "input_source":pre.input_source,
            "channel":pre.channel,
            "custom_state":dict(pre.custom_state),
        },
        evidence_digest="sha256:bridge-converted-valid-evidence",
    )
    snapshot=to_physical_snapshot(world)
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=65,
    )

    expected=bridge._translate_state(intent,snapshot.state)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=66,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,snapshot.state,post_state_observer=observer)

    assert result.status=="EXECUTED"
    assert result.rejection is None
    assert result.verification is not None
    assert result.verification.verification_status==VerificationStatus.VERIFIED
    assert result.verification.expected_state_digest==expected.state_digest
    assert result.verification.observed_state_digest==expected.state_digest
    assert bridge.adapter.device.state.state_digest==expected.state_digest

@pytest.mark.asyncio
async def test_bridge_binds_world_state_provenance_into_verification_record(env):
    from datetime import datetime, timezone
    from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot

    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    world=WorldStateSnapshot(
        target_id=intent.device_id,
        epoch=66,
        observed_at=datetime.now(timezone.utc),
        state={
            "power":pre.power,
            "volume":pre.volume,
            "muted":pre.muted,
            "input_source":pre.input_source,
            "channel":pre.channel,
            "custom_state":dict(pre.custom_state),
        },
        evidence_digest="sha256:bridge-bound-world-state-evidence",
    )
    snapshot=to_physical_snapshot(world)
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=66,
    )

    expected=bridge._translate_state(intent,snapshot.state)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=67,observed_at=time.time())

    result=await bridge.authorize_and_commit(
        intent,
        lease,
        physical,
        snapshot,
        snapshot.state,
        world_state_evidence_digest=world.evidence_digest,
        post_state_observer=observer,
    )

    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.world_state_evidence_digest==world.evidence_digest
    assert "world_state_evidence_digest" not in CapabilityLease.__dataclass_fields__
    assert "world_state_evidence_digest" not in PhysicalSnapshot.__dataclass_fields__

@pytest.mark.asyncio
async def test_bridge_world_state_provenance_does_not_change_authorization_lineage(env):
    import hashlib
    from datetime import datetime, timezone
    from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot

    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    world=WorldStateSnapshot(
        target_id=intent.device_id,
        epoch=67,
        observed_at=datetime.now(timezone.utc),
        state={
            "power":pre.power,
            "volume":pre.volume,
            "muted":pre.muted,
            "input_source":pre.input_source,
            "channel":pre.channel,
            "custom_state":dict(pre.custom_state),
        },
        evidence_digest="sha256:provenance-independent-of-authority",
    )
    snapshot=to_physical_snapshot(world)
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=67,
    )
    expected_authorization_digest=hashlib.sha256(intent.canonical_bytes).hexdigest()

    expected=bridge._translate_state(intent,snapshot.state)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=68,observed_at=time.time())

    result=await bridge.authorize_and_commit(
        intent,
        lease,
        physical,
        snapshot,
        snapshot.state,
        world_state_evidence_digest=world.evidence_digest,
        post_state_observer=observer,
    )

    assert result.status=="EXECUTED"
    assert result.authorization_digest==expected_authorization_digest
    assert result.capability_digest==lease.payload_digest
    assert result.transaction_id==intent.transaction_id
    assert result.verification is not None
    assert result.verification.authorization_digest==expected_authorization_digest
    assert result.verification.capability_digest==lease.payload_digest
    assert result.verification.transaction_id==intent.transaction_id
    assert result.verification.world_state_evidence_digest==world.evidence_digest

@pytest.mark.asyncio
async def test_bridge_legacy_physical_commit_defaults_world_state_provenance_to_empty(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=0,
    )
    snapshot=PhysicalSnapshot(
        device_id=intent.device_id,
        state=pre,
        epoch=0,
        observed_at=time.time(),
    )

    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time())

    result=await bridge.authorize_and_commit(
        intent,
        lease,
        physical,
        snapshot,
        pre,
        post_state_observer=observer,
    )

    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.world_state_evidence_digest==""

@pytest.mark.asyncio
async def test_bridge_rejects_explicit_blank_world_state_provenance(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=68,
    )
    snapshot=PhysicalSnapshot(
        device_id=intent.device_id,
        state=pre,
        epoch=68,
        observed_at=time.time(),
    )

    result=await bridge.authorize_and_commit(
        intent,
        lease,
        physical,
        snapshot,
        pre,
        world_state_evidence_digest="   ",
    )

    assert result.status=="REJECTED"
    assert result.rejection=="WORLD_STATE_PROVENANCE_INVALID"
    assert bridge.adapter.device.state.state_digest==pre.state_digest

@pytest.mark.asyncio
async def test_bridge_rejects_explicit_nonstring_world_state_provenance(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=69,
    )
    snapshot=PhysicalSnapshot(
        device_id=intent.device_id,
        state=pre,
        epoch=69,
        observed_at=time.time(),
    )

    result=await bridge.authorize_and_commit(
        intent,
        lease,
        physical,
        snapshot,
        pre,
        world_state_evidence_digest=12345,
    )

    assert result.status=="REJECTED"
    assert result.rejection=="WORLD_STATE_PROVENANCE_INVALID"
    assert bridge.adapter.device.state.state_digest==pre.state_digest

@pytest.mark.asyncio
async def test_bridge_binds_world_state_epoch_into_verification_record(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=74,
    )
    snapshot=PhysicalSnapshot(
        device_id=intent.device_id,
        state=pre,
        epoch=74,
        observed_at=time.time(),
    )

    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=75,observed_at=time.time())

    result=await bridge.authorize_and_commit(
        intent,
        lease,
        physical,
        snapshot,
        pre,
        world_state_evidence_digest="sha256:epoch-74-evidence",
        post_state_observer=observer,
    )

    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.world_state_evidence_digest=="sha256:epoch-74-evidence"
    assert result.verification.world_state_epoch==74

@pytest.mark.asyncio
async def test_bridge_legacy_physical_commit_records_snapshot_epoch_with_empty_provenance(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=75,
    )
    snapshot=PhysicalSnapshot(
        device_id=intent.device_id,
        state=pre,
        epoch=75,
        observed_at=time.time(),
    )

    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=76,observed_at=time.time())

    result=await bridge.authorize_and_commit(
        intent,
        lease,
        physical,
        snapshot,
        pre,
        post_state_observer=observer,
    )

    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.world_state_evidence_digest==""
    assert result.verification.world_state_epoch==75
    assert result.verification.observed_state_epoch==76
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_epoch_drift_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=76)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=77,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:rejected-epoch-evidence")
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.EPOCH_DRIFT
    assert result.verification is None
    assert bridge.adapter.device.state.state_digest==pre.state_digest
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_world_state_stale_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=78,max_world_state_age_ms=10)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=78,observed_at=time.time()-1.0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:rejected-stale-evidence")
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.WORLD_STATE_STALE
    assert result.verification is None
    assert bridge.adapter.device.state.state_digest==pre.state_digest
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_precondition_drift_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    expected_pre=DeviceState(volume=11)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=79)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=79,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,expected_pre,world_state_evidence_digest="sha256:rejected-precondition-evidence")
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.PRECONDITION_DRIFT
    assert result.verification is None
    assert bridge.adapter.device.state.state_digest==pre.state_digest
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_valid_commit_binds_epoch_and_preserves_authorization_lineage(env):
    import hashlib
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=80)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=80,observed_at=time.time())
    expected_authorization_digest=hashlib.sha256(intent.canonical_bytes).hexdigest()
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=81,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:valid-epoch-80-evidence",post_state_observer=observer)
    assert result.status=="EXECUTED"
    assert result.authorization_digest==expected_authorization_digest
    assert result.capability_digest==lease.payload_digest
    assert result.transaction_id==intent.transaction_id
    assert result.verification is not None
    assert result.verification.authorization_digest==expected_authorization_digest
    assert result.verification.capability_digest==lease.payload_digest
    assert result.verification.transaction_id==intent.transaction_id
    assert result.verification.world_state_evidence_digest=="sha256:valid-epoch-80-evidence"
    assert result.verification.world_state_epoch==80
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_valid_commit_binds_observed_post_state_with_provenance_and_epoch(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=81)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=81,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=82,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:valid-post-state-evidence",post_state_observer=observer)
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.verification_status==VerificationStatus.VERIFIED
    assert result.verification.expected_state_digest==expected.state_digest
    assert result.verification.observed_state_digest==expected.state_digest
    assert result.verification.world_state_evidence_digest=="sha256:valid-post-state-evidence"
    assert result.verification.world_state_epoch==81
    assert bridge.adapter.device.state.state_digest==expected.state_digest
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_valid_commit_binds_execution_receipt_with_provenance_and_epoch(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=82)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=82,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=83,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:valid-receipt-evidence",post_state_observer=observer)
    assert result.status=="EXECUTED"
    assert result.receipt is not None
    assert result.verification is not None
    assert result.verification.receipt_id==result.receipt.receipt_id
    assert result.verification.world_state_evidence_digest=="sha256:valid-receipt-evidence"
    assert result.verification.world_state_epoch==82
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_receipt_intent_mismatch_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class BadReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="bad-provenance-receipt",intent_id="wrong",device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=BadReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=83)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=83,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:bad-receipt-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="RECEIPT_INTENT_MISMATCH"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_receipt_device_mismatch_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class BadReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="bad-device-receipt",intent_id=intent.intent_id,device_id="wrong",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=BadReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=84)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=84,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:bad-device-receipt-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="RECEIPT_DEVICE_MISMATCH"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_post_state_mismatch_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class LyingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="lying-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=LyingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=85)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=85,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    assert pre.state_digest!=expected.state_digest
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=pre,epoch=86,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:post-state-mismatch-evidence",post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_unobservable_post_state_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class BlindAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="blind-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=BlindAdapter()
    bridge.adapter=adapter
    pre=DeviceState(volume=10)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=86)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=86,observed_at=time.time())
    async def observer(device_id):
        return None
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:unobservable-post-state-evidence",post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_committed_receipt_requires_matching_observed_post_state_for_verification(env):
    bridge,intent,lease,key=env
    class CommittedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return ActuationReceipt(receipt_id="committed-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.COMMITTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=CommittedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=87)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=87,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=88,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:committed-observed-evidence",post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.expected_state_digest==expected.state_digest
    assert result.verification.observed_state_digest==expected.state_digest
    assert result.verification.world_state_evidence_digest=="sha256:committed-observed-evidence"
    assert result.verification.world_state_epoch==87
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_committed_receipt_with_mismatched_post_state_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class PrematureCommittedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="committed-mismatch-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.COMMITTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=PrematureCommittedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=88)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=88,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    assert pre.state_digest!=expected.state_digest
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=pre,epoch=89,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:committed-mismatch-evidence",post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_duplicate_absorbed_emits_no_new_verification_record(env):
    bridge,intent,lease,key=env
    class DuplicateAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="duplicate-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.DUPLICATE_ABSORBED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=DuplicateAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=89)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=89,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:duplicate-absorbed-evidence")
    assert adapter.calls==1
    assert result.status=="DUPLICATE_ABSORBED"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_post_state_observer_not_called_on_adapter_rejected_receipt(env):
    bridge,intent,lease,key=env
    class RejectedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="observer-not-called-rejected",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.REJECTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=RejectedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=90)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=90,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not run")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="REJECTED"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_provenance_bearing_adapter_rejected_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class RejectedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="rejected-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.REJECTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=RejectedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=90)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=90,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:adapter-rejected-evidence")
    assert adapter.calls==1
    assert result.status=="REJECTED"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_post_state_observer_not_called_on_adapter_failed_receipt(env):
    bridge,intent,lease,key=env
    class FailedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="observer-not-called-failed",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.FAILED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=FailedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=91)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=91,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not run")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="FAILED"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_provenance_bearing_adapter_failed_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class FailedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="failed-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.FAILED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=FailedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=91)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=91,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:adapter-failed-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_unknown_adapter_status_fails_closed_without_verification_record(env):
    bridge,intent,lease,key=env
    class UnknownStatusAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="unknown-status-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status="UNKNOWN_STATUS",transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=UnknownStatusAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=92)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=92,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:unknown-status-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_pending_receipt_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class PendingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="pending-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.PENDING,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=PendingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=93)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=93,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:pending-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_executing_receipt_emits_no_verification_record(env):
    bridge,intent,lease,key=env
    class ExecutingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="executing-provenance-receipt",intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTING,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=ExecutingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=94)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=94,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:executing-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_issuer_mismatch_emits_no_verification_record_and_no_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=CountingAdapter()
    bridge.adapter=adapter
    other=KeyPair.generate()
    d=dict(intent.__dict__);d["issuer_id"]=other.key_id;d["signature"]=""
    d["signature"]=other.sign(SignedActionIntent(**d).canonical_bytes)
    forged=SignedActionIntent(**d)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=forged.device_id,capabilities={forged.operation.lower()},authorized_epoch=95)
    snapshot=PhysicalSnapshot(device_id=forged.device_id,state=pre,epoch=95,observed_at=time.time())
    result=await bridge.authorize_and_commit(forged,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:issuer-mismatch-evidence")
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="ISSUER_MISMATCH"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_invalid_signature_emits_no_verification_record_and_no_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=CountingAdapter()
    bridge.adapter=adapter
    d={k:v for k,v in intent.__dict__.items() if k!="signature"};d["parameters"]={"volume":56.0}
    bad=SignedActionIntent(**d,signature=intent.signature)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=bad.device_id,capabilities={bad.operation.lower()},authorized_epoch=96)
    snapshot=PhysicalSnapshot(device_id=bad.device_id,state=pre,epoch=96,observed_at=time.time())
    result=await bridge.authorize_and_commit(bad,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:invalid-signature-evidence")
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection==AuthRejectionCode.AUTH_SIGNATURE_INVALID
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_auth_device_mismatch_emits_no_verification_record_and_no_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=CountingAdapter()
    bridge.adapter=adapter
    d={k:v for k,v in intent.__dict__.items() if k!="signature"};d["device_id"]="other_tv"
    sig=key.sign(SignedActionIntent(**d,signature="").canonical_bytes)
    bad=SignedActionIntent(**d,signature=sig)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=bad.device_id,capabilities={bad.operation.lower()},authorized_epoch=97)
    snapshot=PhysicalSnapshot(device_id=bad.device_id,state=pre,epoch=97,observed_at=time.time())
    result=await bridge.authorize_and_commit(bad,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:auth-device-mismatch-evidence")
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection==AuthRejectionCode.AUTH_DEVICE_MISMATCH
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_invalid_lease_signature_emits_no_verification_record_and_no_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(intent_id=intent.intent_id,device_id="tv_integration_node_1",status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=CountingAdapter()
    bridge.adapter=adapter
    d={k:v for k,v in lease.__dict__.items() if k!="signature"};d["capability_digest"]="forged"
    bad=SignedCapabilityLease(**d,signature=lease.signature)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=98)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=98,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,bad,physical,snapshot,pre,world_state_evidence_digest="sha256:invalid-lease-signature-evidence")
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="LEASE_SIGNATURE_INVALID"
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_unsupported_operation_emits_no_verification_record_and_no_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    d=dict(intent.__dict__);d["operation"]="DELETE_DEVICE";d["signature"]=""
    d["signature"]=key.sign(SignedActionIntent(**d).canonical_bytes)
    forged=SignedActionIntent(**d)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=forged.device_id,capabilities={forged.operation.lower()},authorized_epoch=99)
    snapshot=PhysicalSnapshot(device_id=forged.device_id,state=pre,epoch=99,observed_at=time.time())
    result=await bridge.authorize_and_commit(forged,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:unsupported-operation-evidence")
    assert result.status=="REJECTED"
    assert result.rejection
    assert adapter.calls==0
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_malformed_operation_emits_no_verification_record_and_no_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    d=dict(intent.__dict__);d["operation"]="";d["signature"]=""
    d["signature"]=key.sign(SignedActionIntent(**d).canonical_bytes)
    forged=SignedActionIntent(**d)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=forged.device_id,capabilities={forged.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=forged.device_id,state=pre,epoch=100,observed_at=time.time())
    result=await bridge.authorize_and_commit(forged,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:malformed-operation-evidence")
    assert result.status=="REJECTED"
    assert result.rejection
    assert adapter.calls==0
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_physical_device_mismatch_emits_no_verification_record_and_no_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_WRONG",capabilities={intent.operation.lower()},authorized_epoch=101)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=101,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:physical-device-mismatch-evidence")
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None
@pytest.mark.asyncio
async def test_bridge_provenance_bearing_capability_denied_emits_no_verification_record_and_no_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities=set(),authorized_epoch=102)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=102,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:capability-denied-evidence")
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.CAPABILITY_DENIED
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_adapter_device_mismatch_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_WRONG"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None


@pytest.mark.asyncio
async def test_legacy_bridge_adapter_device_mismatch_is_typed_and_never_actuates(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_WRONG"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    result=await bridge.authorize_and_execute(intent,lease,adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_missing_adapter_identity_fails_closed_without_actuation_or_verification(env):
    bridge,intent,lease,key=env
    class IdentitylessAdapter:
        class Dev:
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=IdentitylessAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_missing_adapter_device_fails_closed_without_actuation_or_verification(env):
    bridge,intent,lease,key=env
    class DevicelessAdapter:
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=DevicelessAdapter()
    bridge.adapter=adapter
    pre=DeviceState()
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_adapter_identity_fails_closed_without_actuation_or_verification(env):
    bridge,intent,lease,key=env
    class FaultingIdentity:
        @property
        def device_id(self):
            raise RuntimeError("identity unavailable")
    class FaultingIdentityAdapter:
        class Dev:
            identity=FaultingIdentity()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=FaultingIdentityAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_legacy_bridge_faulting_adapter_identity_fails_closed_without_actuation_or_verification(env):
    bridge,intent,lease,key=env
    class FaultingIdentity:
        @property
        def device_id(self):
            raise RuntimeError("identity unavailable")
    class FaultingIdentityAdapter:
        class Dev:
            identity=FaultingIdentity()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=FaultingIdentityAdapter()
    bridge.adapter=adapter
    result=await bridge.authorize_and_execute(intent,lease,adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_legacy_bridge_missing_adapter_identity_fails_closed_without_actuation_or_verification(env):
    bridge,intent,lease,key=env
    class IdentitylessAdapter:
        class Dev:
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=IdentitylessAdapter()
    bridge.adapter=adapter
    result=await bridge.authorize_and_execute(intent,lease,adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_legacy_bridge_missing_adapter_device_fails_closed_without_actuation_or_verification(env):
    bridge,intent,lease,key=env
    class DevicelessAdapter:
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=DevicelessAdapter()
    bridge.adapter=adapter
    pre=DeviceState()
    result=await bridge.authorize_and_execute(intent,lease,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_adapter_device_lookup_fails_closed_without_actuation_or_verification(env):
    bridge,intent,lease,key=env
    class FaultingDeviceAdapter:
        calls=0
        @property
        def device(self):
            raise RuntimeError("device unavailable")
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=FaultingDeviceAdapter()
    bridge.adapter=adapter
    pre=DeviceState()
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_legacy_bridge_faulting_adapter_device_lookup_fails_closed_without_actuation_or_verification(env):
    bridge,intent,lease,key=env
    class FaultingDeviceAdapter:
        calls=0
        @property
        def device(self):
            raise RuntimeError("device unavailable")
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=FaultingDeviceAdapter()
    bridge.adapter=adapter
    result=await bridge.authorize_and_execute(intent,lease,DeviceState())
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls==0
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_missing_adapter_fails_closed_without_verification(env):
    bridge,intent,lease,key=env
    bridge.adapter=None
    pre=DeviceState()
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert result.verification is None

@pytest.mark.asyncio
async def test_legacy_bridge_missing_adapter_fails_closed_without_verification(env):
    bridge,intent,lease,key=env
    bridge.adapter=None
    result=await bridge.authorize_and_execute(intent,lease,DeviceState())
    assert result.status=="REJECTED"
    assert result.rejection==PreconditionResult.DEVICE_MISMATCH
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_post_state_device_lookup_fails_closed_with_receipt_and_no_verification(env):
    bridge,intent,lease,key=env
    class FaultingPostStateAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        _device=Dev()
        device_reads=0
        calls=0
        @property
        def device(self):
            self.device_reads+=1
            if self.device_reads>1:
                raise RuntimeError("post-state device unavailable")
            return self._device
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self._device.state=intent.target_state
            return ActuationReceipt(receipt_id="faulting-post-state-device",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=FaultingPostStateAdapter()
    bridge.adapter=adapter
    pre=adapter._device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        raise RuntimeError("post-state device unavailable")
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.receipt is not None
    assert result.receipt.receipt_id=="faulting-post-state-device"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_post_state_digest_fails_closed_with_receipt_and_no_verification(env):
    bridge,intent,lease,key=env
    class FaultingDigestState:
        @property
        def state_digest(self):
            raise RuntimeError("post-state digest unavailable")
    class FaultingDigestAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=FaultingDigestState()
            return ActuationReceipt(receipt_id="faulting-post-state-digest",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=FaultingDigestAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=FaultingDigestState(),epoch=1,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_MISMATCH"
    assert result.receipt is not None
    assert result.receipt.receipt_id=="faulting-post-state-digest"
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_receipt_intent_id_fails_closed_with_receipt_and_no_verification(env):
    bridge,intent,lease,key=env
    class FaultingIntentReceipt:
        receipt_id="faulting-receipt-intent-id"
        device_id="tv_integration_node_1"
        status=ActuationStatus.EXECUTED
        @property
        def intent_id(self):
            raise RuntimeError("receipt intent id unavailable")
    class FaultingReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return FaultingIntentReceipt()
    adapter=FaultingReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="RECEIPT_INTENT_MISMATCH"
    assert isinstance(result.receipt,FaultingIntentReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_receipt_device_id_fails_closed_with_receipt_and_no_verification(env):
    bridge,intent,lease,key=env
    class FaultingDeviceReceipt:
        receipt_id="faulting-receipt-device-id"
        intent_id=intent.intent_id
        status=ActuationStatus.EXECUTED
        @property
        def device_id(self):
            raise RuntimeError("receipt device id unavailable")
    class FaultingReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return FaultingDeviceReceipt()
    adapter=FaultingReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="RECEIPT_DEVICE_MISMATCH"
    assert isinstance(result.receipt,FaultingDeviceReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_receipt_status_fails_closed_with_receipt_and_no_verification(env):
    bridge,intent,lease,key=env
    class FaultingStatusReceipt:
        receipt_id="faulting-receipt-status"
        intent_id=intent.intent_id
        device_id=intent.device_id
        transaction_id=intent.transaction_id
        capability_digest=lease.payload_digest
        @property
        def status(self):
            raise RuntimeError("receipt status unavailable")
    class FaultingReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return FaultingStatusReceipt()
    adapter=FaultingReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection is None
    assert isinstance(result.receipt,FaultingStatusReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_receipt_id_fails_closed_with_receipt_and_no_verification(env):
    bridge,intent,lease,key=env
    class FaultingReceiptIdReceipt:
        intent_id=intent.intent_id
        device_id=intent.device_id
        status=ActuationStatus.EXECUTED
        transaction_id=intent.transaction_id
        capability_digest=lease.payload_digest
        @property
        def receipt_id(self):
            raise RuntimeError("receipt id unavailable")
    class FaultingReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return FaultingReceiptIdReceipt()
    adapter=FaultingReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection is None
    assert isinstance(result.receipt,FaultingReceiptIdReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_verification_record_constructor_failure_fails_closed_with_receipt(env,monkeypatch):
    bridge,intent,lease,key=env
    class ValidReceipt:
        receipt_id="constructor-failure-receipt"
        intent_id=intent.intent_id
        device_id=intent.device_id
        status=ActuationStatus.EXECUTED
        transaction_id=intent.transaction_id
        capability_digest=lease.payload_digest
    class ExecutingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return ValidReceipt()
    def faulting_verification_record(*args,**kwargs):
        raise RuntimeError("verification record unavailable")
    monkeypatch.setattr("src.control.device_fabric_bridge.PhysicalVerificationRecord",faulting_verification_record)
    adapter=ExecutingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection is None
    assert isinstance(result.receipt,ValidReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_unhashable_receipt_status_fails_closed_with_receipt_and_no_verification(env):
    bridge,intent,lease,key=env
    class UnhashableStatusReceipt:
        receipt_id="unhashable-status-receipt"
        intent_id=intent.intent_id
        device_id=intent.device_id
        transaction_id=intent.transaction_id
        capability_digest=lease.payload_digest
        status=[]
    class UnhashableStatusAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return UnhashableStatusReceipt()
    adapter=UnhashableStatusAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection is None
    assert isinstance(result.receipt,UnhashableStatusReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_receipt_status_comparison_fails_closed_with_receipt_and_no_verification(env):
    bridge,intent,lease,key=env
    class FaultingStatus:
        def __eq__(self,other):
            raise RuntimeError("status comparison unavailable")
        def __hash__(self):
            return 0
    class FaultingStatusReceipt:
        receipt_id="faulting-status-comparison-receipt"
        intent_id=intent.intent_id
        device_id=intent.device_id
        transaction_id=intent.transaction_id
        capability_digest=lease.payload_digest
        status=FaultingStatus()
    class FaultingStatusAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return FaultingStatusReceipt()
    adapter=FaultingStatusAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection is None
    assert isinstance(result.receipt,FaultingStatusReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_receipt_intent_id_comparison_fails_closed_with_receipt(env):
    bridge,intent,lease,key=env
    class FaultingIntentId:
        def __eq__(self,other):
            raise RuntimeError("receipt intent comparison unavailable")
        def __ne__(self,other):
            raise RuntimeError("receipt intent comparison unavailable")
    class FaultingIntentReceipt:
        receipt_id="faulting-intent-comparison-receipt"
        intent_id=FaultingIntentId()
        device_id=intent.device_id
        status=ActuationStatus.EXECUTED
    class FaultingIntentAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return FaultingIntentReceipt()
    adapter=FaultingIntentAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="RECEIPT_INTENT_MISMATCH"
    assert isinstance(result.receipt,FaultingIntentReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_receipt_device_id_comparison_fails_closed_with_receipt(env):
    bridge,intent,lease,key=env
    class FaultingDeviceId:
        def __eq__(self,other):
            raise RuntimeError("receipt device comparison unavailable")
        def __ne__(self,other):
            raise RuntimeError("receipt device comparison unavailable")
    class FaultingDeviceReceipt:
        receipt_id="faulting-device-comparison-receipt"
        intent_id=intent.intent_id
        device_id=FaultingDeviceId()
        status=ActuationStatus.EXECUTED
    class FaultingDeviceAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return FaultingDeviceReceipt()
    adapter=FaultingDeviceAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="RECEIPT_DEVICE_MISMATCH"
    assert isinstance(result.receipt,FaultingDeviceReceipt)
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_adapter_device_id_comparison_rejects_without_actuation(env):
    bridge,intent,lease,key=env
    class FaultingDeviceId:
        def __eq__(self,other):
            raise RuntimeError("adapter device comparison unavailable")
        def __ne__(self,other):
            raise RuntimeError("adapter device comparison unavailable")
    class FaultingIdentityAdapter:
        class Dev:
            class Id:
                device_id=FaultingDeviceId()
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=FaultingIdentityAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert getattr(result.rejection,"name",result.rejection)=="DEVICE_MISMATCH"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_issuer_id_comparison_rejects_without_actuation(env):
    bridge,intent,lease,key=env
    class FaultingIssuerId(str):
        def __eq__(self,other):
            raise RuntimeError("issuer comparison unavailable")
        def __ne__(self,other):
            raise RuntimeError("issuer comparison unavailable")
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    d=dict(intent.__dict__)
    d["issuer_id"]=FaultingIssuerId(intent.issuer_id)
    faulting_intent=SignedActionIntent(**d)
    assert isinstance(faulting_intent.issuer_id,FaultingIssuerId)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=faulting_intent.device_id,capabilities={faulting_intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=faulting_intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(faulting_intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="ISSUER_MISMATCH"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_world_state_provenance_validation_rejects_without_actuation(env):
    bridge,intent,lease,key=env
    class FaultingProvenance(str):
        def strip(self,*args,**kwargs):
            raise RuntimeError("provenance validation unavailable")
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest=FaultingProvenance("sha256:evidence"))
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="WORLD_STATE_PROVENANCE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_lease_verifier_rejects_without_actuation(env):
    bridge,intent,lease,key=env
    class FaultingVerifier:
        def verify(self,*args,**kwargs):
            raise RuntimeError("lease verification unavailable")
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    bridge.firewall.trusted_verifiers[lease.issuer_id]=FaultingVerifier()
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="LEASE_SIGNATURE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_firewall_validation_rejects_without_actuation(env):
    bridge,intent,lease,key=env
    class FaultingFirewall:
        def __init__(self,trusted_verifiers):
            self.trusted_verifiers=trusted_verifiers
        def validate_intent(self,*args,**kwargs):
            raise RuntimeError("intent validation unavailable")
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    bridge.firewall=FaultingFirewall(bridge.firewall.trusted_verifiers)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert getattr(result.rejection,"name",result.rejection)=="AUTH_SIGNATURE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_malformed_firewall_validation_result_rejects_without_actuation(env):
    bridge,intent,lease,key=env
    class MalformedFirewall:
        def __init__(self,trusted_verifiers):
            self.trusted_verifiers=trusted_verifiers
        def validate_intent(self,*args,**kwargs):
            return None
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    bridge.firewall=MalformedFirewall(bridge.firewall.trusted_verifiers)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert getattr(result.rejection,"name",result.rejection)=="AUTH_SIGNATURE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_substituted_firewall_validation_intent_rejects_without_actuation(env):
    from dataclasses import replace
    bridge,intent,lease,key=env
    class SubstitutingFirewall:
        def __init__(self,trusted_verifiers):
            self.trusted_verifiers=trusted_verifiers
        def validate_intent(self,submitted,*args,**kwargs):
            return replace(submitted,intent_id="substituted_intent")
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    bridge.firewall=SubstitutingFirewall(bridge.firewall.trusted_verifiers)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert getattr(result.rejection,"name",result.rejection)=="AUTH_SIGNATURE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_state_translation_rejects_without_actuation(env):
    from dataclasses import replace
    bridge,intent,lease,key=env
    class FaultingOperation(str):
        def upper(self):
            raise RuntimeError("state translation unavailable")
    class PassthroughFirewall:
        def __init__(self,trusted_verifiers):
            self.trusted_verifiers=trusted_verifiers
        def validate_intent(self,submitted,*args,**kwargs):
            return submitted
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    bridge.firewall=PassthroughFirewall(bridge.firewall.trusted_verifiers)
    faulting_intent=replace(intent,operation=FaultingOperation(intent.operation))
    pre=adapter.device.state
    physical=CapabilityLease(device_id=faulting_intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=faulting_intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(faulting_intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="STATE_TRANSLATION_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_operation_normalization_rejects_without_actuation(env):
    from dataclasses import replace
    bridge,intent,lease,key=env
    class FaultingOperation(str):
        def lower(self):
            raise RuntimeError("operation normalization unavailable")
    class PassthroughFirewall:
        def __init__(self,trusted_verifiers):
            self.trusted_verifiers=trusted_verifiers
        def validate_intent(self,submitted,*args,**kwargs):
            return submitted
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    bridge.firewall=PassthroughFirewall(bridge.firewall.trusted_verifiers)
    faulting_intent=replace(intent,operation=FaultingOperation(intent.operation))
    pre=adapter.device.state
    physical=CapabilityLease(device_id=faulting_intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=faulting_intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(faulting_intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="OPERATION_NORMALIZATION_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_authorization_digest_rejects_without_actuation(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    def faulting_digest(*args,**kwargs):
        raise RuntimeError("authorization digest unavailable")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    bridge._authorization_digest=faulting_digest
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="AUTHORIZATION_DIGEST_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_authorized_intent_construction_rejects_without_actuation(env,monkeypatch):
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    calls=[]
    async def forbidden(*args,**kwargs):
        calls.append(1)
        raise AssertionError("adapter must not be called")
    def faulting_constructor(*args,**kwargs):
        raise RuntimeError("authorized intent construction unavailable")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    monkeypatch.setattr(m,"AuthorizedActionIntent",faulting_constructor)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="AUTHORIZED_INTENT_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_commit_gate_construction_rejects_without_actuation(env,monkeypatch):
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    calls=[]
    async def forbidden(*args,**kwargs):
        calls.append(1)
        raise AssertionError("adapter must not be called")
    def faulting_gate(*args,**kwargs):
        raise RuntimeError("commit gate unavailable")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    monkeypatch.setattr(m,"PhysicalCommitGate",faulting_gate)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_commit_invocation_returns_failed_without_adapter_access(env,monkeypatch):
    bridge,intent,lease,key=env
    adapter_calls=[]
    gate_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class FaultingGate:
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise RuntimeError("commit invocation unavailable")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=FaultingGate())
    assert gate_calls==[1]
    assert adapter_calls==[]
    assert result.status=="FAILED"
    assert result.rejection=="COMMIT_EXECUTION_FAILED"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_commit_result_classification_returns_failed_with_receipt(env):
    bridge,intent,lease,key=env
    class HostileResult:
        @property
        def __class__(self):
            raise RuntimeError("commit result classification unavailable")
    hostile=HostileResult()
    class Gate:
        async def commit(self,*args,**kwargs):
            return hostile
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert result.status=="FAILED"
    assert result.rejection=="COMMIT_RESULT_INVALID"
    assert result.receipt is hostile
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_commit_gate_truthiness_rejects_without_invocation(env,monkeypatch):
    bridge,intent,lease,key=env
    gate_calls=[]
    adapter_calls=[]
    class HostileGate:
        def __bool__(self):
            raise RuntimeError("commit gate truthiness unavailable")
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise AssertionError("gate commit must not be called")
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=HostileGate())
    assert gate_calls==[]
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_noncallable_commit_gate_rejects_before_adapter_access(env,monkeypatch):
    bridge,intent,lease,key=env
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class InvalidGate:
        commit=None
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=InvalidGate())
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_commit_attribute_rejects_before_adapter_access(env,monkeypatch):
    bridge,intent,lease,key=env
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class HostileGate:
        @property
        def commit(self):
            raise RuntimeError("commit attribute unavailable")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=HostileGate())
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_missing_commit_attribute_rejects_before_adapter_access(env,monkeypatch):
    bridge,intent,lease,key=env
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class InvalidGate:
        pass
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=InvalidGate())
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_falsey_commit_gate_rejects_without_default_fallback(env,monkeypatch):
    bridge,intent,lease,key=env
    gate_calls=[]
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class FalseyGate:
        def __bool__(self):
            return False
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise AssertionError("falsey gate must not be invoked")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=FalseyGate())
    assert gate_calls==[]
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_falsey_constructed_default_gate_rejects_before_invocation(env,monkeypatch):
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    gate_calls=[]
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class FalseyGate:
        def __bool__(self):
            return False
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise AssertionError("constructed falsey gate must not be invoked")
    monkeypatch.setattr(m,"PhysicalCommitGate",lambda:FalseyGate())
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert gate_calls==[]
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_faulting_constructed_default_gate_truthiness_rejects_before_invocation(env,monkeypatch):
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    gate_calls=[]
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class HostileGate:
        def __bool__(self):
            raise RuntimeError("constructed gate truthiness unavailable")
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise AssertionError("constructed hostile gate must not be invoked")
    monkeypatch.setattr(m,"PhysicalCommitGate",lambda:HostileGate())
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert gate_calls==[]
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_constructed_default_gate_missing_commit_rejects_before_adapter_access(env,monkeypatch):
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class InvalidGate:
        pass
    monkeypatch.setattr(m,"PhysicalCommitGate",lambda:InvalidGate())
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_constructed_default_gate_noncallable_commit_rejects_before_adapter_access(env,monkeypatch):
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class InvalidGate:
        commit=None
    monkeypatch.setattr(m,"PhysicalCommitGate",lambda:InvalidGate())
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_constructed_default_gate_faulting_commit_attribute_rejects_before_adapter_access(env,monkeypatch):
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class InvalidGate:
        @property
        def commit(self):
            raise RuntimeError("constructed gate commit attribute unavailable")
    monkeypatch.setattr(m,"PhysicalCommitGate",lambda:InvalidGate())
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_supplied_gate_faulting_commit_attribute_rejects_before_adapter_access(env,monkeypatch):
    bridge,intent,lease,key=env
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class InvalidGate:
        @property
        def commit(self):
            raise RuntimeError("supplied gate commit attribute unavailable")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=InvalidGate())
    assert adapter_calls==[]
    assert result.status=="REJECTED"
    assert result.rejection=="COMMIT_GATE_INVALID"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_constructed_default_gate_commit_exception_returns_execution_failed(env,monkeypatch):
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    gate_calls=[]
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class FailingGate:
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise RuntimeError("constructed gate commit failed")
    monkeypatch.setattr(m,"PhysicalCommitGate",lambda:FailingGate())
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert gate_calls==[1]
    assert adapter_calls==[]
    assert result.status=="FAILED"
    assert result.rejection=="COMMIT_EXECUTION_FAILED"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_supplied_gate_commit_exception_returns_execution_failed(env,monkeypatch):
    bridge,intent,lease,key=env
    gate_calls=[]
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class FailingGate:
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise RuntimeError("supplied gate commit failed")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=FailingGate())
    assert gate_calls==[1]
    assert adapter_calls==[]
    assert result.status=="FAILED"
    assert result.rejection=="COMMIT_EXECUTION_FAILED"
    assert result.receipt is None
    assert result.verification is None

@pytest.mark.asyncio
async def test_bridge_supplied_gate_commit_cancellation_propagates_before_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    gate_calls=[]
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class CancellingGate:
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise asyncio.CancelledError()
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=CancellingGate())
    assert gate_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_constructed_default_gate_commit_cancellation_propagates_before_adapter_access(env,monkeypatch):
    import asyncio
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    gate_calls=[]
    adapter_calls=[]
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    class CancellingGate:
        async def commit(self,*args,**kwargs):
            gate_calls.append(1)
            raise asyncio.CancelledError()
    monkeypatch.setattr(m,"PhysicalCommitGate",lambda:CancellingGate())
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert gate_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_default_gate_construction_cancellation_propagates_before_adapter_access(env,monkeypatch):
    import asyncio
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    constructor_calls=[]
    adapter_calls=[]
    def cancelling_constructor():
        constructor_calls.append(1)
        raise asyncio.CancelledError()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(m,"PhysicalCommitGate",cancelling_constructor)
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert constructor_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_supplied_gate_truthiness_cancellation_propagates_before_commit_or_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    truthiness_calls=[]
    commit_calls=[]
    adapter_calls=[]
    class CancellingGate:
        def __bool__(self):
            truthiness_calls.append(1)
            raise asyncio.CancelledError()
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=CancellingGate())
    assert truthiness_calls==[1]
    assert commit_calls==[]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_supplied_gate_commit_attribute_cancellation_propagates_before_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    attribute_calls=[]
    adapter_calls=[]
    class CancellingGate:
        def __getattribute__(self,name):
            if name=="commit":
                attribute_calls.append(1)
                raise asyncio.CancelledError()
            return object.__getattribute__(self,name)
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=CancellingGate())
    assert attribute_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_constructed_default_gate_truthiness_cancellation_propagates_before_commit_or_adapter_access(env,monkeypatch):
    import asyncio
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    constructor_calls=[]
    truthiness_calls=[]
    commit_calls=[]
    adapter_calls=[]
    class CancellingGate:
        def __bool__(self):
            truthiness_calls.append(1)
            raise asyncio.CancelledError()
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    def constructor():
        constructor_calls.append(1)
        return CancellingGate()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(m,"PhysicalCommitGate",constructor)
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert constructor_calls==[1]
    assert truthiness_calls==[1]
    assert commit_calls==[]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_constructed_default_gate_commit_attribute_cancellation_propagates_before_adapter_access(env,monkeypatch):
    import asyncio
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    constructor_calls=[]
    attribute_calls=[]
    adapter_calls=[]
    class CancellingGate:
        def __getattribute__(self,name):
            if name=="commit":
                attribute_calls.append(1)
                raise asyncio.CancelledError()
            return object.__getattribute__(self,name)
    def constructor():
        constructor_calls.append(1)
        return CancellingGate()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(m,"PhysicalCommitGate",constructor)
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert constructor_calls==[1]
    assert attribute_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_supplied_gate_synchronous_commit_invocation_cancellation_propagates_before_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    adapter_calls=[]
    class CancellingGate:
        def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise asyncio.CancelledError()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=CancellingGate())
    assert commit_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_constructed_default_gate_synchronous_commit_invocation_cancellation_propagates_before_adapter_access(env,monkeypatch):
    import asyncio
    import src.control.device_fabric_bridge as m
    bridge,intent,lease,key=env
    constructor_calls=[]
    commit_calls=[]
    adapter_calls=[]
    class CancellingGate:
        def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise asyncio.CancelledError()
    def constructor():
        constructor_calls.append(1)
        return CancellingGate()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(m,"PhysicalCommitGate",constructor)
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert constructor_calls==[1]
    assert commit_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_receipt_intent_attribute_cancellation_propagates_before_later_receipt_or_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    attribute_calls=[]
    adapter_calls=[]
    class CancellingReceipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                attribute_calls.append(name)
                raise asyncio.CancelledError()
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return CancellingReceipt()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert commit_calls==[1]
    assert attribute_calls==["intent_id"]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_receipt_intent_comparison_cancellation_propagates_before_later_receipt_or_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    comparison_calls=[]
    attribute_calls=[]
    adapter_calls=[]
    class CancellingIntentId:
        def __ne__(self,other):
            comparison_calls.append(1)
            raise asyncio.CancelledError()
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                attribute_calls.append(name)
                return CancellingIntentId()
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return Receipt()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert commit_calls==[1]
    assert attribute_calls==["intent_id"]
    assert comparison_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_receipt_device_attribute_cancellation_propagates_before_comparison_status_or_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    attribute_calls=[]
    adapter_calls=[]
    class CancellingReceipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                attribute_calls.append(name)
                raise asyncio.CancelledError()
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return CancellingReceipt()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert commit_calls==[1]
    assert attribute_calls==["intent_id","device_id"]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_receipt_device_comparison_cancellation_propagates_before_status_or_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    comparison_calls=[]
    attribute_calls=[]
    adapter_calls=[]
    class CancellingDeviceId:
        def __ne__(self,other):
            comparison_calls.append(1)
            raise asyncio.CancelledError()
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                attribute_calls.append(name)
                return CancellingDeviceId()
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return Receipt()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert commit_calls==[1]
    assert attribute_calls==["intent_id","device_id"]
    assert comparison_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_receipt_status_attribute_cancellation_propagates_before_classification_or_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    attribute_calls=[]
    adapter_calls=[]
    class CancellingReceipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                attribute_calls.append(name)
                raise asyncio.CancelledError()
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return CancellingReceipt()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert commit_calls==[1]
    assert attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status"]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_receipt_status_hash_cancellation_propagates_before_classification_or_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    hash_calls=[]
    attribute_calls=[]
    adapter_calls=[]
    class CancellingStatus:
        def __hash__(self):
            hash_calls.append(1)
            raise asyncio.CancelledError()
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                attribute_calls.append(name)
                return CancellingStatus()
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return Receipt()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert commit_calls==[1]
    assert attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status"]
    assert hash_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_receipt_status_comparison_cancellation_propagates_before_later_classification_or_adapter_access(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    hash_calls=[]
    comparison_calls=[]
    attribute_calls=[]
    adapter_calls=[]
    class CancellingStatus:
        def __hash__(self):
            hash_calls.append(1)
            return hash(ActuationStatus.COMMITTED)
        def __eq__(self,other):
            comparison_calls.append(1)
            raise asyncio.CancelledError()
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                attribute_calls.append(name)
                return CancellingStatus()
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return Receipt()
    async def forbidden(*args,**kwargs):
        adapter_calls.append(1)
        raise AssertionError("adapter must not be called")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert commit_calls==[1]
    assert attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status"]
    assert hash_calls==[]
    assert comparison_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_post_state_device_access_cancellation_propagates_before_receipt_id_or_status_mapping(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    device_calls=[]
    receipt_attribute_calls=[]
    adapter_calls=[]
    pre=bridge.adapter.device.state
    class Identity:
        device_id=intent.device_id
    class Device:
        identity=Identity()
    class CancellingAdapter:
        @property
        def device(self):
            device_calls.append(1)
            if len(device_calls)==2:
                raise asyncio.CancelledError()
            return Device()
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                receipt_attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                receipt_attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                receipt_attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                receipt_attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                receipt_attribute_calls.append(name)
                return ActuationStatus.EXECUTED
            if name=="receipt_id":
                receipt_attribute_calls.append(name)
                raise AssertionError("receipt_id must not be accessed")
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return Receipt()
    monkeypatch.setattr(bridge,"adapter",CancellingAdapter())
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),post_state_observer=observer)
    assert commit_calls==[1]
    assert device_calls==[1]
    assert receipt_attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status"]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_post_state_attribute_cancellation_propagates_before_receipt_id_or_status_mapping(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    device_calls=[]
    state_calls=[]
    receipt_attribute_calls=[]
    adapter_calls=[]
    pre=bridge.adapter.device.state
    class Identity:
        device_id=intent.device_id
    class IdentityDevice:
        identity=Identity()
    class CancellingStateDevice:
        @property
        def state(self):
            state_calls.append(1)
            raise asyncio.CancelledError()
    class Adapter:
        @property
        def device(self):
            device_calls.append(1)
            return IdentityDevice() if len(device_calls)==1 else CancellingStateDevice()
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                receipt_attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                receipt_attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                receipt_attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                receipt_attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                receipt_attribute_calls.append(name)
                return ActuationStatus.EXECUTED
            if name=="receipt_id":
                receipt_attribute_calls.append(name)
                raise AssertionError("receipt_id must not be accessed")
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return Receipt()
    monkeypatch.setattr(bridge,"adapter",Adapter())
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class CancellingSnapshot(PhysicalSnapshot):
        def __getattribute__(self,name):
            if name=="state":
                state_calls.append(1)
                raise asyncio.CancelledError()
            return super().__getattribute__(name)
    async def observer(device_id):
        return CancellingSnapshot(device_id=device_id,state=pre,epoch=1,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),post_state_observer=observer)
    assert commit_calls==[1]
    assert device_calls==[1]
    assert state_calls==[1]
    assert receipt_attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status"]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_post_state_digest_attribute_cancellation_propagates_before_comparison_receipt_id_or_status_mapping(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    device_calls=[]
    state_calls=[]
    digest_calls=[]
    receipt_attribute_calls=[]
    adapter_calls=[]
    pre=bridge.adapter.device.state
    class Identity:
        device_id=intent.device_id
    class IdentityDevice:
        identity=Identity()
    class CancellingObservedState:
        @property
        def state_digest(self):
            digest_calls.append(1)
            raise asyncio.CancelledError()
    class PostStateDevice:
        @property
        def state(self):
            state_calls.append(1)
            return CancellingObservedState()
    class Adapter:
        @property
        def device(self):
            device_calls.append(1)
            return IdentityDevice() if len(device_calls)==1 else PostStateDevice()
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                receipt_attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                receipt_attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                receipt_attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                receipt_attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                receipt_attribute_calls.append(name)
                return ActuationStatus.EXECUTED
            if name=="receipt_id":
                receipt_attribute_calls.append(name)
                raise AssertionError("receipt_id must not be accessed")
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return Receipt()
    monkeypatch.setattr(bridge,"adapter",Adapter())
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        state_calls.append(1)
        return PhysicalSnapshot(device_id=device_id,state=CancellingObservedState(),epoch=1,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),post_state_observer=observer)
    assert commit_calls==[1]
    assert device_calls==[1]
    assert state_calls==[1]
    assert digest_calls==[1]
    assert receipt_attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status"]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_post_state_digest_comparison_cancellation_propagates_before_receipt_id_or_status_mapping(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    device_calls=[]
    state_calls=[]
    digest_calls=[]
    comparison_calls=[]
    receipt_attribute_calls=[]
    adapter_calls=[]
    pre=bridge.adapter.device.state
    class Identity:
        device_id=intent.device_id
    class IdentityDevice:
        identity=Identity()
    class CancellingDigest:
        def __ne__(self,other):
            comparison_calls.append(1)
            raise asyncio.CancelledError()
    class ObservedState:
        @property
        def state_digest(self):
            digest_calls.append(1)
            return CancellingDigest()
    class PostStateDevice:
        @property
        def state(self):
            state_calls.append(1)
            return ObservedState()
    class Adapter:
        @property
        def device(self):
            device_calls.append(1)
            return IdentityDevice() if len(device_calls)==1 else PostStateDevice()
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                receipt_attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                receipt_attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                receipt_attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                receipt_attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                receipt_attribute_calls.append(name)
                return ActuationStatus.EXECUTED
            if name=="receipt_id":
                receipt_attribute_calls.append(name)
                raise AssertionError("receipt_id must not be accessed")
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            return Receipt()
    monkeypatch.setattr(bridge,"adapter",Adapter())
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        state_calls.append(1)
        return PhysicalSnapshot(device_id=device_id,state=ObservedState(),epoch=1,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),post_state_observer=observer)
    assert commit_calls==[1]
    assert device_calls==[1]
    assert state_calls==[1]
    assert digest_calls==[1]
    assert comparison_calls==[1]
    assert receipt_attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status"]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_receipt_id_attribute_cancellation_propagates_after_post_state_match_before_verification_or_status_mapping(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    device_calls=[]
    state_calls=[]
    receipt_attribute_calls=[]
    adapter_calls=[]
    pre=bridge.adapter.device.state
    class Identity:
        device_id=intent.device_id
    class IdentityDevice:
        identity=Identity()
    class PostStateDevice:
        @property
        def state(self):
            state_calls.append(1)
            return adapter.post_state
    class Adapter:
        post_state=None
        @property
        def device(self):
            device_calls.append(1)
            return IdentityDevice() if len(device_calls)==1 else PostStateDevice()
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    adapter=Adapter()
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                receipt_attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                receipt_attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                receipt_attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                receipt_attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                receipt_attribute_calls.append(name)
                return ActuationStatus.EXECUTED
            if name=="receipt_id":
                receipt_attribute_calls.append(name)
                raise asyncio.CancelledError()
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,authorized,*args,**kwargs):
            commit_calls.append(1)
            adapter.post_state=authorized.target_state
            return Receipt()
    monkeypatch.setattr(bridge,"adapter",adapter)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=adapter.post_state,epoch=1,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),post_state_observer=observer)
    assert commit_calls==[1]
    assert device_calls==[1]
    assert state_calls==[]
    assert receipt_attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status","receipt_id"]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_verification_construction_cancellation_propagates_before_status_mapping(env,monkeypatch):
    import asyncio
    import sys
    bridge,intent,lease,key=env
    commit_calls=[]
    device_calls=[]
    state_calls=[]
    receipt_attribute_calls=[]
    verification_calls=[]
    adapter_calls=[]
    pre=bridge.adapter.device.state
    class Identity:
        device_id=intent.device_id
    class IdentityDevice:
        identity=Identity()
    class PostStateDevice:
        @property
        def state(self):
            state_calls.append(1)
            return adapter.post_state
    class Adapter:
        post_state=None
        @property
        def device(self):
            device_calls.append(1)
            return IdentityDevice() if len(device_calls)==1 else PostStateDevice()
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    adapter=Adapter()
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                receipt_attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                receipt_attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                receipt_attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                receipt_attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                receipt_attribute_calls.append(name)
                return ActuationStatus.EXECUTED
            if name=="receipt_id":
                receipt_attribute_calls.append(name)
                return "receipt-cancellation-proof"
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,authorized,*args,**kwargs):
            commit_calls.append(1)
            adapter.post_state=authorized.target_state
            return Receipt()
    def cancelling_verification_record(*args,**kwargs):
        verification_calls.append(1)
        raise asyncio.CancelledError()
    monkeypatch.setattr(bridge,"adapter",adapter)
    monkeypatch.setattr(sys.modules[bridge.__class__.__module__],"PhysicalVerificationRecord",cancelling_verification_record)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=adapter.post_state,epoch=1,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),post_state_observer=observer)
    assert commit_calls==[1]
    assert device_calls==[1]
    assert state_calls==[]
    assert receipt_attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status","receipt_id"]
    assert verification_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_status_mapping_hash_cancellation_propagates_after_verification(env,monkeypatch):
    import asyncio
    import sys
    bridge,intent,lease,key=env
    commit_calls=[]
    device_calls=[]
    state_calls=[]
    status_comparison_calls=[]
    status_hash_calls=[]
    receipt_attribute_calls=[]
    verification_calls=[]
    adapter_calls=[]
    pre=bridge.adapter.device.state
    module=sys.modules[bridge.__class__.__module__]
    original_verification_record=module.PhysicalVerificationRecord
    class Identity:
        device_id=intent.device_id
    class IdentityDevice:
        identity=Identity()
    class PostStateDevice:
        @property
        def state(self):
            state_calls.append(1)
            return adapter.post_state
    class Adapter:
        post_state=None
        @property
        def device(self):
            device_calls.append(1)
            return IdentityDevice() if len(device_calls)==1 else PostStateDevice()
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    adapter=Adapter()
    class CancellingStatus:
        def __eq__(self,other):
            status_comparison_calls.append(other)
            return other is ActuationStatus.EXECUTED
        def __hash__(self):
            status_hash_calls.append(1)
            raise asyncio.CancelledError()
    status_value=CancellingStatus()
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                receipt_attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                receipt_attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                receipt_attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                receipt_attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                receipt_attribute_calls.append(name)
                return status_value
            if name=="receipt_id":
                receipt_attribute_calls.append(name)
                return "receipt-status-map-cancellation"
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,authorized,*args,**kwargs):
            commit_calls.append(1)
            adapter.post_state=authorized.target_state
            return Receipt()
    def recording_verification_record(*args,**kwargs):
        verification_calls.append(1)
        return original_verification_record(*args,**kwargs)
    monkeypatch.setattr(bridge,"adapter",adapter)
    monkeypatch.setattr(module,"PhysicalVerificationRecord",recording_verification_record)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=adapter.post_state,epoch=1,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),post_state_observer=observer)
    assert commit_calls==[1]
    assert device_calls==[1]
    assert state_calls==[]
    assert receipt_attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status","receipt_id"]
    assert len(status_comparison_calls)>=1
    assert status_hash_calls==[1]
    assert verification_calls==[1]
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_success_result_construction_cancellation_propagates_after_status_mapping(env,monkeypatch):
    import asyncio
    import sys
    bridge,intent,lease,key=env
    commit_calls=[]
    device_calls=[]
    state_calls=[]
    receipt_attribute_calls=[]
    verification_calls=[]
    bridge_result_calls=[]
    adapter_calls=[]
    pre=bridge.adapter.device.state
    module=sys.modules[bridge.__class__.__module__]
    original_verification_record=module.PhysicalVerificationRecord
    class Identity:
        device_id=intent.device_id
    class IdentityDevice:
        identity=Identity()
    class PostStateDevice:
        @property
        def state(self):
            state_calls.append(1)
            return adapter.post_state
    class Adapter:
        post_state=None
        @property
        def device(self):
            device_calls.append(1)
            return IdentityDevice() if len(device_calls)==1 else PostStateDevice()
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    adapter=Adapter()
    class Receipt:
        def __getattribute__(self,name):
            if name=="intent_id":
                receipt_attribute_calls.append(name)
                return intent.intent_id
            if name=="device_id":
                receipt_attribute_calls.append(name)
                return intent.device_id
            if name=="transaction_id":
                receipt_attribute_calls.append(name)
                return intent.transaction_id
            if name=="capability_digest":
                receipt_attribute_calls.append(name)
                return lease.payload_digest
            if name=="status":
                receipt_attribute_calls.append(name)
                return ActuationStatus.EXECUTED
            if name=="receipt_id":
                receipt_attribute_calls.append(name)
                return "receipt-result-construction-cancellation"
            return object.__getattribute__(self,name)
    class Gate:
        async def commit(self,authorized,*args,**kwargs):
            commit_calls.append(1)
            adapter.post_state=authorized.target_state
            return Receipt()
    def recording_verification_record(*args,**kwargs):
        verification_calls.append(1)
        return original_verification_record(*args,**kwargs)
    def cancelling_bridge_result(*args,**kwargs):
        bridge_result_calls.append((args,kwargs))
        raise asyncio.CancelledError()
    monkeypatch.setattr(bridge,"adapter",adapter)
    monkeypatch.setattr(module,"PhysicalVerificationRecord",recording_verification_record)
    monkeypatch.setattr(module,"BridgeResult",cancelling_bridge_result)
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    async def observer(device_id):
        state_calls.append(1)
        return PhysicalSnapshot(device_id=device_id,state=adapter.post_state,epoch=1,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),post_state_observer=observer)
    assert commit_calls==[1]
    assert device_calls==[1]
    assert state_calls==[1]
    assert receipt_attribute_calls==["intent_id","device_id","transaction_id","capability_digest","status","receipt_id"]
    assert verification_calls==[1]
    assert len(bridge_result_calls)==1
    assert bridge_result_calls[0][0][0]=="EXECUTED"
    assert bridge_result_calls[0][1]["verification"] is not None
    assert adapter_calls==[]

@pytest.mark.asyncio
async def test_bridge_lease_validation_cancellation_propagates_before_firewall_adapter_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    validation_calls=[]
    firewall_calls=[]
    adapter_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    def cancelling_validate_lease(value):
        validation_calls.append(value)
        raise asyncio.CancelledError()
    def unexpected_firewall(*args,**kwargs):
        firewall_calls.append(1)
        raise AssertionError("firewall must not be called")
    class Adapter:
        @property
        def device(self):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be accessed")
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",cancelling_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",unexpected_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert validation_calls==[lease]
    assert firewall_calls==[]
    assert adapter_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_intent_issuer_attribute_cancellation_propagates_before_firewall_adapter_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    issuer_attribute_calls=[]
    firewall_calls=[]
    adapter_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    original_intent=intent
    class CancellingIntent:
        def __getattribute__(self,name):
            if name=="issuer_id":
                issuer_attribute_calls.append(name)
                raise asyncio.CancelledError()
            return getattr(original_intent,name)
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def unexpected_firewall(*args,**kwargs):
        firewall_calls.append(1)
        raise AssertionError("firewall must not be called")
    class Adapter:
        @property
        def device(self):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be accessed")
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",unexpected_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(CancellingIntent(),lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert issuer_attribute_calls==["issuer_id"]
    assert firewall_calls==[]
    assert adapter_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_lease_issuer_attribute_cancellation_propagates_before_firewall_adapter_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    lease_issuer_attribute_calls=[]
    firewall_calls=[]
    adapter_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    original_lease=lease
    class CancellingLease:
        def __getattribute__(self,name):
            if name=="issuer_id":
                lease_issuer_attribute_calls.append(name)
                raise asyncio.CancelledError()
            return getattr(original_lease,name)
    cancelling_lease=CancellingLease()
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def unexpected_firewall(*args,**kwargs):
        firewall_calls.append(1)
        raise AssertionError("firewall must not be called")
    class Adapter:
        @property
        def device(self):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be accessed")
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",unexpected_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,cancelling_lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[cancelling_lease]
    assert lease_issuer_attribute_calls==["issuer_id"]
    assert firewall_calls==[]
    assert adapter_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_issuer_comparison_cancellation_propagates_before_firewall_adapter_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    intent_issuer_attribute_calls=[]
    comparison_calls=[]
    firewall_calls=[]
    adapter_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    original_intent=intent
    class CancellingIssuer:
        def __ne__(self,other):
            comparison_calls.append(other)
            raise asyncio.CancelledError()
    cancelling_issuer=CancellingIssuer()
    class ComparingIntent:
        def __getattribute__(self,name):
            if name=="issuer_id":
                intent_issuer_attribute_calls.append(name)
                return cancelling_issuer
            return getattr(original_intent,name)
    comparing_intent=ComparingIntent()
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def unexpected_firewall(*args,**kwargs):
        firewall_calls.append(1)
        raise AssertionError("firewall must not be called")
    class Adapter:
        @property
        def device(self):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be accessed")
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",unexpected_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(comparing_intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert intent_issuer_attribute_calls==["issuer_id"]
    assert comparison_calls==[lease.issuer_id]
    assert firewall_calls==[]
    assert adapter_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_firewall_validation_cancellation_propagates_before_adapter_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    adapter_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def cancelling_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        raise asyncio.CancelledError()
    class Adapter:
        @property
        def device(self):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be accessed")
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",cancelling_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert adapter_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_firewall_result_auth_rejection_classification_cancellation_propagates_before_adapter_or_commit(env,monkeypatch):
    import asyncio
    import importlib
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    classification_calls=[]
    adapter_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    class CancellingClassificationMeta(type):
        def __instancecheck__(cls,value):
            classification_calls.append(value)
            raise asyncio.CancelledError()
    class CancellingAuthRejectionCode(metaclass=CancellingClassificationMeta):
        pass
    class Adapter:
        @property
        def device(self):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be accessed")
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    module=importlib.import_module(bridge.__class__.__module__)
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(module,"AuthRejectionCode",CancellingAuthRejectionCode)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert classification_calls==[intent]
    assert adapter_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_firewall_result_signed_intent_classification_cancellation_propagates_before_adapter_or_commit(env,monkeypatch):
    import asyncio
    import importlib
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    classification_calls=[]
    adapter_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    class CancellingClassificationMeta(type):
        def __instancecheck__(cls,value):
            classification_calls.append(value)
            raise asyncio.CancelledError()
    class CancellingSignedActionIntent(metaclass=CancellingClassificationMeta):
        pass
    class Adapter:
        @property
        def device(self):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be accessed")
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be called")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    module=importlib.import_module(bridge.__class__.__module__)
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(module,"SignedActionIntent",CancellingSignedActionIntent)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert classification_calls==[intent]
    assert adapter_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_pre_authorization_adapter_device_access_cancellation_propagates_before_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    adapter_device_calls=[]
    adapter_execution_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    class Adapter:
        @property
        def device(self):
            adapter_device_calls.append(1)
            raise asyncio.CancelledError()
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert adapter_device_calls==[1]
    assert adapter_execution_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_pre_authorization_adapter_identity_access_cancellation_propagates_before_device_id_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    adapter_device_calls=[]
    identity_calls=[]
    device_id_calls=[]
    adapter_execution_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    class Identity:
        @property
        def device_id(self):
            device_id_calls.append(1)
            raise AssertionError("device_id must not be accessed")
    class Device:
        @property
        def identity(self):
            identity_calls.append(1)
            raise asyncio.CancelledError()
    device=Device()
    class Adapter:
        @property
        def device(self):
            adapter_device_calls.append(1)
            return device
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert adapter_device_calls==[1]
    assert identity_calls==[1]
    assert device_id_calls==[]
    assert adapter_execution_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_pre_authorization_adapter_device_id_access_cancellation_propagates_before_comparison_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    adapter_device_calls=[]
    identity_calls=[]
    device_id_calls=[]
    adapter_execution_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    class Identity:
        @property
        def device_id(self):
            device_id_calls.append(1)
            raise asyncio.CancelledError()
    identity=Identity()
    class Device:
        @property
        def identity(self):
            identity_calls.append(1)
            return identity
    device=Device()
    class Adapter:
        @property
        def device(self):
            adapter_device_calls.append(1)
            return device
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert adapter_device_calls==[1]
    assert identity_calls==[1]
    assert device_id_calls==[1]
    assert adapter_execution_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_pre_authorization_adapter_device_id_comparison_cancellation_propagates_before_mismatch_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    device_id_access_calls=[]
    comparison_calls=[]
    adapter_execution_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    class CancellingDeviceId:
        def __ne__(self,other):
            comparison_calls.append(other)
            raise asyncio.CancelledError()
    cancelling_device_id=CancellingDeviceId()
    class Identity:
        @property
        def device_id(self):
            device_id_access_calls.append(1)
            return cancelling_device_id
    class Device:
        identity=Identity()
    class Adapter:
        device=Device()
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert device_id_access_calls==[1]
    assert comparison_calls==[intent.device_id]
    assert adapter_execution_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_state_translation_cancellation_propagates_after_identity_match_before_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    translation_calls=[]
    adapter_execution_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    def cancelling_translate(actual_intent,actual_state):
        translation_calls.append((actual_intent,actual_state))
        raise asyncio.CancelledError()
    class Identity:
        device_id=intent.device_id
    class Device:
        identity=Identity()
    class Adapter:
        device=Device()
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"_translate_state",cancelling_translate)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert translation_calls==[(intent,snapshot.state)]
    assert adapter_execution_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_operation_normalization_lower_cancellation_propagates_before_digest_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    translation_calls=[]
    lower_calls=[]
    digest_calls=[]
    adapter_execution_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    original_operation=intent.operation
    physical=CapabilityLease(device_id=intent.device_id,capabilities={original_operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    def returning_translate(actual_intent,actual_state):
        translation_calls.append((actual_intent,actual_state))
        return pre
    def forbidden_digest(*args,**kwargs):
        digest_calls.append(1)
        raise AssertionError("authorization digest must not be computed")
    class CancellingOperation:
        def lower(self):
            lower_calls.append(1)
            raise asyncio.CancelledError()
    class Identity:
        device_id=intent.device_id
    class Device:
        identity=Identity()
    class Adapter:
        device=Device()
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    intent.operation=CancellingOperation()
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"_translate_state",returning_translate)
    monkeypatch.setattr(bridge,"_authorization_digest",forbidden_digest)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert translation_calls==[(intent,snapshot.state)]
    assert lower_calls==[1]
    assert digest_calls==[]
    assert adapter_execution_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_authorization_digest_cancellation_propagates_after_normalization_before_construction_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    translation_calls=[]
    lower_calls=[]
    digest_calls=[]
    adapter_execution_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    original_operation=intent.operation
    physical=CapabilityLease(device_id=intent.device_id,capabilities={original_operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    def returning_translate(actual_intent,actual_state):
        translation_calls.append((actual_intent,actual_state))
        return pre
    def cancelling_digest(actual_intent):
        digest_calls.append(actual_intent)
        raise asyncio.CancelledError()
    class RecordingOperation:
        def lower(self):
            lower_calls.append(1)
            return original_operation.lower()
    class Identity:
        device_id=intent.device_id
    class Device:
        identity=Identity()
    class Adapter:
        device=Device()
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not be called")
    intent.operation=RecordingOperation()
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"_translate_state",returning_translate)
    monkeypatch.setattr(bridge,"_authorization_digest",cancelling_digest)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert translation_calls==[(intent,snapshot.state)]
    assert lower_calls==[1]
    assert digest_calls==[intent]
    assert adapter_execution_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_authorized_intent_construction_cancellation_propagates_before_commit_gate_or_actuation(env,monkeypatch):
    import asyncio
    import sys
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    translation_calls=[]
    digest_calls=[]
    construction_calls=[]
    gate_access_calls=[]
    adapter_execution_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    auth_digest="verified-authorization-digest"
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    def returning_translate(actual_intent,actual_state):
        translation_calls.append((actual_intent,actual_state))
        return pre
    def returning_digest(actual_intent):
        digest_calls.append(actual_intent)
        return auth_digest
    def cancelling_authorized_intent(*args,**kwargs):
        construction_calls.append((args,kwargs))
        raise asyncio.CancelledError()
    class Identity:
        device_id=intent.device_id
    class Device:
        identity=Identity()
    class Adapter:
        device=Device()
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        @property
        def commit(self):
            gate_access_calls.append(1)
            raise AssertionError("commit gate must not be accessed")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"_translate_state",returning_translate)
    monkeypatch.setattr(bridge,"_authorization_digest",returning_digest)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    monkeypatch.setattr(sys.modules[bridge.__class__.__module__],"AuthorizedActionIntent",cancelling_authorized_intent)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert translation_calls==[(intent,snapshot.state)]
    assert digest_calls==[intent]
    assert len(construction_calls)==1
    args,kwargs=construction_calls[0]
    assert args==()
    assert kwargs["intent_id"]==intent.intent_id
    assert kwargs["authorization_digest"]==auth_digest
    assert kwargs["target_state"]==pre
    assert gate_access_calls==[]
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_commit_gate_truthiness_cancellation_propagates_before_commit_lookup_or_actuation(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    truthiness_calls=[]
    commit_access_calls=[]
    adapter_execution_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Gate:
        def __bool__(self):
            truthiness_calls.append(1)
            raise asyncio.CancelledError()
        @property
        def commit(self):
            commit_access_calls.append(1)
            raise AssertionError("commit must not be accessed")
    async def forbidden_adapter_execution(*args,**kwargs):
        adapter_execution_calls.append(1)
        raise AssertionError("adapter must not execute")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden_adapter_execution)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert truthiness_calls==[1]
    assert commit_access_calls==[]
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_commit_lookup_cancellation_propagates_after_truthiness_before_commit_or_actuation(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    truthiness_calls=[]
    commit_access_calls=[]
    adapter_execution_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Gate:
        def __bool__(self):
            truthiness_calls.append(1)
            return True
        @property
        def commit(self):
            commit_access_calls.append(1)
            raise asyncio.CancelledError()
    async def forbidden_adapter_execution(*args,**kwargs):
        adapter_execution_calls.append(1)
        raise AssertionError("adapter must not execute")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden_adapter_execution)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert truthiness_calls==[1]
    assert commit_access_calls==[1]
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_commit_cancellation_receives_exact_authorization_boundary_objects_before_actuation(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    commit_calls=[]
    adapter_execution_calls=[]
    pre=bridge.adapter.device.state
    adapter=bridge.adapter
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append((args,kwargs))
            raise asyncio.CancelledError()
    async def forbidden_adapter_execution(*args,**kwargs):
        adapter_execution_calls.append(1)
        raise AssertionError("adapter must not execute")
    monkeypatch.setattr(adapter,"execute_intent",forbidden_adapter_execution)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert len(commit_calls)==1
    args,kwargs=commit_calls[0]
    assert kwargs=={}
    assert len(args)==4
    authorized,actual_physical,actual_snapshot,actual_adapter=args
    assert authorized.intent_id==intent.intent_id
    assert authorized.lease_id==lease.payload_digest
    assert authorized.device_id==intent.device_id
    assert authorized.operation==intent.operation.lower()
    assert authorized.expected_pre_state==pre
    assert actual_physical is physical
    assert actual_snapshot is snapshot
    assert actual_adapter is adapter
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_commit_cancellation_preserves_complete_authorized_intent_projection(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    translation_calls=[]
    digest_calls=[]
    commit_calls=[]
    adapter_execution_calls=[]
    pre=bridge.adapter.device.state
    target=pre
    auth_digest="commit-boundary-authorization-digest"
    normalized_operation=intent.operation.lower()
    physical=CapabilityLease(device_id=intent.device_id,capabilities={normalized_operation},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def returning_translate(actual_intent,actual_state):
        translation_calls.append((actual_intent,actual_state))
        return target
    def returning_digest(actual_intent):
        digest_calls.append(actual_intent)
        return auth_digest
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append((args,kwargs))
            raise asyncio.CancelledError()
    async def forbidden_adapter_execution(*args,**kwargs):
        adapter_execution_calls.append(1)
        raise AssertionError("adapter must not execute")
    monkeypatch.setattr(bridge,"_translate_state",returning_translate)
    monkeypatch.setattr(bridge,"_authorization_digest",returning_digest)
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden_adapter_execution)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert translation_calls==[(intent,snapshot.state)]
    assert digest_calls==[intent]
    assert len(commit_calls)==1
    args,kwargs=commit_calls[0]
    assert kwargs=={}
    authorized=args[0]
    assert authorized.intent_id==intent.intent_id
    assert authorized.lease_id==lease.payload_digest
    assert authorized.action==normalized_operation
    assert authorized.device_id==intent.device_id
    assert authorized.operation==normalized_operation
    assert authorized.target_state is target
    assert authorized.expected_pre_state is pre
    assert authorized.authorization_digest==auth_digest
    assert authorized.deadline_at==intent.expires_at
    assert args[1] is physical
    assert args[2] is snapshot
    assert args[3] is bridge.adapter
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_commit_adapter_argument_access_cancellation_propagates_before_commit_invocation_or_actuation(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    adapter=bridge.adapter
    pre=adapter.device.state
    adapter_access_calls=[]
    commit_calls=[]
    adapter_execution_calls=[]
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append((args,kwargs))
            raise AssertionError("commit must not be invoked")
    async def forbidden_adapter_execution(*args,**kwargs):
        adapter_execution_calls.append(1)
        raise AssertionError("adapter must not execute")
    def adapter_property(actual_bridge):
        adapter_access_calls.append(actual_bridge)
        if len(adapter_access_calls)==2:
            raise asyncio.CancelledError()
        return adapter
    monkeypatch.setattr(adapter,"execute_intent",forbidden_adapter_execution)
    monkeypatch.setattr(type(bridge),"adapter",property(adapter_property),raising=False)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert adapter_access_calls==[bridge,bridge]
    assert commit_calls==[]
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_world_state_provenance_strip_cancellation_propagates_before_lease_firewall_commit_or_actuation(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    strip_calls=[]
    lease_validation_calls=[]
    firewall_calls=[]
    commit_calls=[]
    adapter_execution_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class CancellingProvenance(str):
        def strip(self,*args,**kwargs):
            strip_calls.append((args,kwargs))
            raise asyncio.CancelledError()
    def forbidden_lease_validation(*args,**kwargs):
        lease_validation_calls.append(1)
        raise AssertionError("lease validation must not run")
    def forbidden_firewall(*args,**kwargs):
        firewall_calls.append(1)
        raise AssertionError("firewall must not run")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not run")
    async def forbidden_adapter_execution(*args,**kwargs):
        adapter_execution_calls.append(1)
        raise AssertionError("adapter must not execute")
    monkeypatch.setattr(bridge,"_validate_lease",forbidden_lease_validation)
    monkeypatch.setattr(bridge.firewall,"validate_intent",forbidden_firewall)
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden_adapter_execution)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),world_state_evidence_digest=CancellingProvenance("sha256:evidence"))
    assert strip_calls==[((),{})]
    assert lease_validation_calls==[]
    assert firewall_calls==[]
    assert commit_calls==[]
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_world_state_provenance_stripped_truthiness_cancellation_propagates_before_lease_firewall_commit_or_actuation(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    strip_calls=[]
    truthiness_calls=[]
    lease_validation_calls=[]
    firewall_calls=[]
    commit_calls=[]
    adapter_execution_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class CancellingTruthiness:
        def __bool__(self):
            truthiness_calls.append(1)
            raise asyncio.CancelledError()
    class Provenance(str):
        def strip(self,*args,**kwargs):
            strip_calls.append((args,kwargs))
            return CancellingTruthiness()
    def forbidden_lease_validation(*args,**kwargs):
        lease_validation_calls.append(1)
        raise AssertionError("lease validation must not run")
    def forbidden_firewall(*args,**kwargs):
        firewall_calls.append(1)
        raise AssertionError("firewall must not run")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not run")
    async def forbidden_adapter_execution(*args,**kwargs):
        adapter_execution_calls.append(1)
        raise AssertionError("adapter must not execute")
    monkeypatch.setattr(bridge,"_validate_lease",forbidden_lease_validation)
    monkeypatch.setattr(bridge.firewall,"validate_intent",forbidden_firewall)
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden_adapter_execution)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate(),world_state_evidence_digest=Provenance("sha256:evidence"))
    assert strip_calls==[((),{})]
    assert truthiness_calls==[1]
    assert lease_validation_calls==[]
    assert firewall_calls==[]
    assert commit_calls==[]
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_lease_validation_result_truthiness_cancellation_propagates_before_firewall_commit_or_actuation(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    validation_calls=[]
    truthiness_calls=[]
    firewall_calls=[]
    commit_calls=[]
    adapter_execution_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class CancellingLeaseError:
        def __bool__(self):
            truthiness_calls.append(1)
            raise asyncio.CancelledError()
    def cancelling_result_lease_validation(value):
        validation_calls.append(value)
        return CancellingLeaseError()
    def forbidden_firewall(*args,**kwargs):
        firewall_calls.append(1)
        raise AssertionError("firewall must not run")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not run")
    async def forbidden_adapter_execution(*args,**kwargs):
        adapter_execution_calls.append(1)
        raise AssertionError("adapter must not execute")
    monkeypatch.setattr(bridge,"_validate_lease",cancelling_result_lease_validation)
    monkeypatch.setattr(bridge.firewall,"validate_intent",forbidden_firewall)
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden_adapter_execution)
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert validation_calls==[lease]
    assert truthiness_calls==[1]
    assert firewall_calls==[]
    assert commit_calls==[]
    assert adapter_execution_calls==[]

@pytest.mark.asyncio
async def test_bridge_issuer_comparison_result_truthiness_cancellation_propagates_before_firewall_adapter_or_commit(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    issuer_attribute_calls=[]
    comparison_calls=[]
    truthiness_calls=[]
    firewall_calls=[]
    adapter_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    original_intent=intent
    class CancellingComparisonResult:
        def __bool__(self):
            truthiness_calls.append(1)
            raise asyncio.CancelledError()
    class ComparingIssuer:
        def __ne__(self,other):
            comparison_calls.append(other)
            return CancellingComparisonResult()
    comparing_issuer=ComparingIssuer()
    class ComparingIntent:
        def __getattribute__(self,name):
            if name=="issuer_id":
                issuer_attribute_calls.append(name)
                return comparing_issuer
            return getattr(original_intent,name)
    comparing_intent=ComparingIntent()
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def forbidden_firewall(*args,**kwargs):
        firewall_calls.append(1)
        raise AssertionError("firewall must not run")
    class Adapter:
        @property
        def device(self):
            adapter_calls.append(1)
            raise AssertionError("adapter must not be accessed")
        async def execute_intent(self,*args,**kwargs):
            adapter_calls.append(1)
            raise AssertionError("adapter must not execute")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not run")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",forbidden_firewall)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(comparing_intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert issuer_attribute_calls==["issuer_id"]
    assert comparison_calls==[lease.issuer_id]
    assert truthiness_calls==[1]
    assert firewall_calls==[]
    assert adapter_calls==[]
    assert commit_calls==[]

@pytest.mark.asyncio
async def test_bridge_adapter_device_comparison_result_truthiness_cancellation_propagates_before_translation_commit_or_actuation(env,monkeypatch):
    import asyncio
    bridge,intent,lease,key=env
    lease_validation_calls=[]
    firewall_calls=[]
    comparison_calls=[]
    truthiness_calls=[]
    translation_calls=[]
    adapter_execution_calls=[]
    commit_calls=[]
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class CancellingDeviceMismatchResult:
        def __bool__(self):
            truthiness_calls.append(1)
            raise asyncio.CancelledError()
    class ComparingDeviceId:
        def __ne__(self,other):
            comparison_calls.append(other)
            return CancellingDeviceMismatchResult()
    class Identity:
        device_id=ComparingDeviceId()
    class Device:
        identity=Identity()
    class Adapter:
        device=Device()
        async def execute_intent(self,*args,**kwargs):
            adapter_execution_calls.append(1)
            raise AssertionError("adapter must not execute")
    def recording_validate_lease(value):
        lease_validation_calls.append(value)
        return None
    def returning_firewall(actual_intent,actual_lease):
        firewall_calls.append((actual_intent,actual_lease))
        return actual_intent
    def forbidden_translation(*args,**kwargs):
        translation_calls.append(1)
        raise AssertionError("translation must not run")
    class Gate:
        async def commit(self,*args,**kwargs):
            commit_calls.append(1)
            raise AssertionError("commit must not run")
    monkeypatch.setattr(bridge,"_validate_lease",recording_validate_lease)
    monkeypatch.setattr(bridge.firewall,"validate_intent",returning_firewall)
    monkeypatch.setattr(bridge,"_translate_state",forbidden_translation)
    monkeypatch.setattr(bridge,"adapter",Adapter())
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert lease_validation_calls==[lease]
    assert firewall_calls==[(intent,lease)]
    assert comparison_calls==[intent.device_id]
    assert truthiness_calls==[1]
    assert translation_calls==[]
    assert adapter_execution_calls==[]
    assert commit_calls==[]


@pytest.mark.asyncio
async def test_bridge_nan_observed_at_never_reaches_adapter(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0,max_world_state_age_ms=5000,max_clock_skew_ms=2000)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=float("nan"))
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert getattr(result.rejection,"name",result.rejection)=="WORLD_STATE_STALE"
    assert adapter.calls==0


@pytest.mark.asyncio
async def test_bridge_adapter_local_post_state_alone_cannot_mint_physical_verification(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=None)
    assert result.status=="EXECUTED"
    assert bridge.adapter.device.state.state_digest==bridge._translate_state(intent,pre).state_digest
    assert result.verification is None
    assert result.prior_state is None


@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_binds_distinct_observation_evidence(env):
    bridge,intent,lease,key=env
    class Adapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="observation-evidence",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=Adapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=7,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:authorization-evidence",post_state_observer=observer,observed_state_evidence_digest="sha256:post-observation-evidence")
    assert adapter.calls==1
    assert observer.calls==1
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.world_state_evidence_digest=="sha256:authorization-evidence"
    assert result.verification.observed_state_evidence_digest=="sha256:post-observation-evidence"
    assert result.verification.world_state_epoch==0
    assert result.verification.observed_state_epoch==7
    assert result.verified_state is None


@pytest.mark.asyncio
async def test_bridge_observation_evidence_without_explicit_observer_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,observed_state_evidence_digest="sha256:claimed-independent-observation")
    assert result.status=="REJECTED"
    assert result.rejection=="OBSERVED_STATE_PROVENANCE_INVALID"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before


@pytest.mark.asyncio
async def test_bridge_blank_observation_evidence_with_explicit_observer_rejects_before_actuation(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not be called")
    observer=Observer()
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,observed_state_evidence_digest="   ")
    assert result.status=="REJECTED"
    assert result.rejection=="OBSERVED_STATE_PROVENANCE_INVALID"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before
    assert observer.calls==0


@pytest.mark.asyncio
async def test_bridge_non_string_observation_evidence_with_explicit_observer_rejects_before_actuation(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not be called")
    observer=Observer()
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,observed_state_evidence_digest=12345)
    assert result.status=="REJECTED"
    assert result.rejection=="OBSERVED_STATE_PROVENANCE_INVALID"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before
    assert observer.calls==0


@pytest.mark.asyncio
async def test_bridge_observation_evidence_strip_exception_rejects_before_actuation(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    class EvilStr(str):
        def strip(self,*args,**kwargs):
            raise RuntimeError("strip failed")
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not be called")
    observer=Observer()
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,observed_state_evidence_digest=EvilStr("sha256:value"))
    assert result.status=="REJECTED"
    assert result.rejection=="OBSERVED_STATE_PROVENANCE_INVALID"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before
    assert observer.calls==0


@pytest.mark.asyncio
async def test_bridge_observation_evidence_with_explicit_none_observer_rejects_before_actuation(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=None,observed_state_evidence_digest="sha256:claimed-independent-observation")
    assert result.status=="REJECTED"
    assert result.rejection=="OBSERVED_STATE_PROVENANCE_INVALID"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before


@pytest.mark.asyncio
async def test_bridge_invalid_observation_provenance_rejects_before_lease_validation(env,monkeypatch):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    def forbidden_validate_lease(value):
        raise AssertionError("lease validation must not be called")
    monkeypatch.setattr(bridge,"_validate_lease",forbidden_validate_lease)
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,observed_state_evidence_digest="sha256:claimed-independent-observation")
    assert result.status=="REJECTED"
    assert result.rejection=="OBSERVED_STATE_PROVENANCE_INVALID"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before


@pytest.mark.asyncio
async def test_bridge_rejected_actuation_with_observation_evidence_never_invokes_observer_or_mints_verification(env):
    bridge,intent,lease,key=env
    class RejectedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="rejected-observation-evidence-receipt",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.REJECTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=RejectedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=90)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=90,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not run after rejected actuation")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,observed_state_evidence_digest="sha256:post-observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="REJECTED"
    assert result.verification is None
    assert result.prior_state is None


@pytest.mark.asyncio
async def test_bridge_failed_actuation_with_observation_evidence_never_invokes_observer_or_mints_verification(env):
    bridge,intent,lease,key=env
    class FailedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="failed-observation-evidence-receipt",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.FAILED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=FailedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=91)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=91,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not run after failed actuation")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,observed_state_evidence_digest="sha256:post-observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="FAILED"
    assert result.verification is None
    assert result.prior_state is None


@pytest.mark.asyncio
async def test_bridge_duplicate_absorbed_with_observation_evidence_never_invokes_observer_or_mints_verification(env):
    bridge,intent,lease,key=env
    class DuplicateAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="duplicate-observation-evidence-receipt",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.DUPLICATE_ABSORBED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=DuplicateAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=89)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=89,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not run after duplicate-absorbed actuation")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,observed_state_evidence_digest="sha256:post-observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="DUPLICATE_ABSORBED"
    assert result.verification is None
    assert result.prior_state is None


@pytest.mark.asyncio
@pytest.mark.parametrize("receipt_status",["UNKNOWN_STATUS",ActuationStatus.PENDING,ActuationStatus.EXECUTING])
async def test_bridge_non_executed_transitional_or_unknown_status_with_observation_evidence_never_invokes_observer_or_mints_verification(env,receipt_status):
    bridge,intent,lease,key=env
    class NonExecutedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="non-executed-observation-evidence-receipt",intent_id=intent.intent_id,device_id=intent.device_id,status=receipt_status,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=NonExecutedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=92)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=92,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            raise AssertionError("observer must not run for non-executed status")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,observed_state_evidence_digest="sha256:post-observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="FAILED"
    assert result.verification is None
    assert result.prior_state is None


@pytest.mark.asyncio
async def test_bridge_committed_receipt_with_independent_observer_binds_observation_evidence_and_verifies(env):
    bridge,intent,lease,key=env
    class CommittedAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="committed-independent-observation",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.COMMITTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=CommittedAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=96)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=96,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=97,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:committed-authorization-evidence",post_state_observer=observer,observed_state_evidence_digest="sha256:committed-observation-evidence")
    assert adapter.calls==1
    assert observer.calls==1
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.world_state_evidence_digest=="sha256:committed-authorization-evidence"
    assert result.verification.observed_state_evidence_digest=="sha256:committed-observation-evidence"
    assert result.verification.world_state_epoch==96
    assert result.verification.observed_state_epoch==97
    assert result.verified_state is None


def test_physical_verification_record_has_single_live_producer():
    from pathlib import Path
    hits=[]
    for path in Path("src").rglob("*.py"):
        if path.is_file():
            hits.extend((path,i+1) for i,line in enumerate(path.read_text(errors="ignore").splitlines()) if "PhysicalVerificationRecord(" in line)
    assert len(hits)==1
    assert hits[0][0]==Path("src/control/device_fabric_bridge.py")


@pytest.mark.asyncio
async def test_bridge_executed_without_explicit_post_state_observer_does_not_mint_verification(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=98)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=98,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:no-independent-observer")
    assert result.status=="EXECUTED"
    assert result.receipt is not None
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_omitted_post_state_observer_never_reads_adapter_local_state(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=99)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=99,observed_at=time.time())
    class NoPostCommitStateDevice:
        identity=bridge.adapter.device.identity
        @property
        def state(self):
            raise AssertionError("adapter-local post-state must not be read")
    class Gate:
        async def commit(self,*args,**kwargs):
            bridge.adapter.device=NoPostCommitStateDevice()
            return ActuationReceipt(receipt_id="omitted-observer-no-local-read",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert result.status=="EXECUTED"
    assert result.receipt is not None
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_device_mismatch_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id="wrong-independent-observer-device",state=expected,epoch=101,observed_at=time.time())
    observer=Observer()
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:authorization-evidence",post_state_observer=observer,observed_state_evidence_digest="sha256:wrong-device-observation")
    assert observer.calls==1
    assert result.status=="FAILED"
    assert getattr(result.rejection,"name",result.rejection)=="POST_STATE_MISMATCH"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before


@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_stale_epoch_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=99,observed_at=time.time())
    observer=Observer()
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:authorization-evidence",post_state_observer=observer,observed_state_evidence_digest="sha256:stale-observation")
    assert observer.calls==1
    assert result.status!="EXECUTED"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before


@pytest.mark.asyncio
async def test_bridge_executed_receipt_transaction_provenance_mismatch_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class ProvenanceAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="wrong-transaction-provenance",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id="wrong-transaction-id",capability_digest=lease.payload_digest)
    adapter=ProvenanceAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="FAILED"
    assert getattr(result.rejection,"name",result.rejection)=="RECEIPT_TRANSACTION_MISMATCH"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_commit_boundary_authorized_intent_binds_transaction_and_capability_provenance(env):
    import asyncio
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    captured=[]
    class Gate:
        async def commit(self,authorized,*args,**kwargs):
            captured.append(authorized)
            raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=Gate())
    assert len(captured)==1
    authorized=captured[0]
    assert authorized.transaction_id==intent.transaction_id
    assert authorized.capability_digest==lease.payload_digest


@pytest.mark.asyncio
async def test_bridge_executed_receipt_capability_provenance_mismatch_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class ProvenanceAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="wrong-capability-provenance",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest="wrong-capability-digest")
    adapter=ProvenanceAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="FAILED"
    assert getattr(result.rejection,"name",result.rejection)=="RECEIPT_CAPABILITY_MISMATCH"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_stale_receipt_from_prior_transaction_cannot_mint_verification(env):
    bridge,intent_a,lease,key=env
    d={k:v for k,v in intent_a.__dict__.items() if k!="signature"}
    d["transaction_id"]="tx_bridge_02"
    d["nonce"]="intent_n_02"
    sig=key.sign(SignedActionIntent(**d,signature="").canonical_bytes)
    intent_b=SignedActionIntent(**d,signature=sig)
    class StaleReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="stale-transaction-a-receipt",intent_id=intent_a.intent_id,device_id=intent_a.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent_a.transaction_id,capability_digest=lease.payload_digest)
    adapter=StaleReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent_b.device_id,capabilities={intent_b.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent_b.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent_b,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent_b,lease,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="FAILED"
    assert getattr(result.rejection,"name",result.rejection)=="RECEIPT_TRANSACTION_MISMATCH"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_stale_receipt_from_prior_capability_lease_cannot_mint_verification(env):
    bridge,intent_a,lease_a,key=env
    ld={k:v for k,v in lease_a.__dict__.items() if k!="signature"}
    ld["nonce"]="lease_n_02"
    ls=key.sign(SignedCapabilityLease(**ld,signature="").canonical_bytes)
    lease_b=SignedCapabilityLease(**ld,signature=ls)
    d={k:v for k,v in intent_a.__dict__.items() if k!="signature"}
    d["capability_lease_digest"]=lease_b.payload_digest
    d["nonce"]="intent_n_lease_02"
    sig=key.sign(SignedActionIntent(**d,signature="").canonical_bytes)
    intent_b=SignedActionIntent(**d,signature=sig)
    class StaleCapabilityReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="stale-capability-lease-a-receipt",intent_id=intent_b.intent_id,device_id=intent_b.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent_b.transaction_id,capability_digest=lease_a.payload_digest)
    adapter=StaleCapabilityReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent_b.device_id,capabilities={intent_b.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent_b.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent_b,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent_b,lease_b,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="FAILED"
    assert getattr(result.rejection,"name",result.rejection)=="RECEIPT_CAPABILITY_MISMATCH"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_stale_receipt_from_prior_intent_instance_cannot_mint_verification(env):
    bridge,intent_a,lease,key=env
    d={k:v for k,v in intent_a.__dict__.items() if k!="signature"}
    d["intent_id"]="bridge_02"
    d["nonce"]="intent_instance_n_02"
    sig=key.sign(SignedActionIntent(**d,signature="").canonical_bytes)
    intent_b=SignedActionIntent(**d,signature=sig)
    class StaleIntentReceiptAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="stale-intent-a-receipt",intent_id=intent_a.intent_id,device_id=intent_b.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent_b.transaction_id,capability_digest=lease.payload_digest)
    adapter=StaleIntentReceiptAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent_b.device_id,capabilities={intent_b.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent_b.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent_b,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    observer=Observer()
    result=await bridge.authorize_and_commit(intent_b,lease,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert observer.calls==0
    assert result.status=="FAILED"
    assert getattr(result.rejection,"name",result.rejection)=="RECEIPT_INTENT_MISMATCH"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_empty_receipt_id_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class EmptyReceiptIdAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return ActuationReceipt(receipt_id="",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=EmptyReceiptIdAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_whitespace_receipt_id_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class WhitespaceReceiptIdAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return ActuationReceipt(receipt_id="   ",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=WhitespaceReceiptIdAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_non_string_receipt_id_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class NonStringReceiptIdAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return ActuationReceipt(receipt_id=123,intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    adapter=NonStringReceiptIdAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_missing_receipt_id_attribute_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    class MissingReceiptIdReceipt:
        intent_id=intent.intent_id
        device_id=intent.device_id
        status=ActuationStatus.EXECUTED
        transaction_id=intent.transaction_id
        capability_digest=lease.payload_digest
    class MissingReceiptIdAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=10)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            self.device.state=intent.target_state
            return MissingReceiptIdReceipt()
    adapter=MissingReceiptIdAdapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=101,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer,world_state_evidence_digest="sha256:authorization-evidence",observed_state_evidence_digest="sha256:observation-evidence")
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert isinstance(result.receipt,MissingReceiptIdReceipt)
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_legacy_physical_commit_defaults_observed_state_provenance_to_empty(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.observed_state_evidence_digest==""


@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_equal_epoch_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=100,observed_at=time.time())
    observer=Observer()
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:authorization-evidence",post_state_observer=observer,observed_state_evidence_digest="sha256:equal-epoch-observation")
    assert observer.calls==1
    assert result.status!="EXECUTED"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before


@pytest.mark.asyncio
async def test_bridge_independent_post_state_observer_none_state_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=100)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=100,observed_at=time.time())
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=None,epoch=101,observed_at=time.time())
    observer=Observer()
    calls_before=getattr(bridge.adapter,"calls",0)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:authorization-evidence",post_state_observer=observer,observed_state_evidence_digest="sha256:none-state-observation")
    assert observer.calls==1
    assert result.status=="FAILED"
    assert getattr(result.rejection,"name",result.rejection)=="POST_STATE_MISMATCH"
    assert result.verification is None
    assert getattr(bridge.adapter,"calls",0)==calls_before


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["capability", "epoch"])
async def test_bridge_physical_rejection_never_calls_adapter(env, monkeypatch, case):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities=set() if case=="capability" else {intent.operation.lower()},authorized_epoch=1 if case=="epoch" else 0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    calls=[]
    async def forbidden_execute(*args, **kwargs):
        calls.append((args,kwargs))
        raise AssertionError("rejected physical preconditions must prevent adapter execution")
    monkeypatch.setattr(bridge.adapter,"execute_intent",forbidden_execute)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert calls==[]
    assert result.status=="REJECTED"
    assert result.rejection==(PreconditionResult.CAPABILITY_DENIED if case=="capability" else PreconditionResult.EPOCH_DRIFT)
    assert result.receipt is None


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["current", "stale", "malformed", "missing_memory", "capability", "epoch"])
async def test_bridge_adaptive_commit_freshness(env, monkeypatch, case):
    from dataclasses import replace
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    from src.device_fabric.physical_commit_gate import PhysicalCommitGate
    bridge,intent,lease,key=env
    bridge.adapter.device.state.volume=80.0
    memory=AdaptiveDirectiveMemory(max_entries=2)
    directive_key=("profile_1",intent.device_id,"commercial","channel_alpha")
    memory.remember(directive_key,action="lower_volume")
    memory.feedback(directive_key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(directive_key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    if case=="stale":
        memory.feedback(directive_key,approved=False,reason=FeedbackReason.NEVER_AUTOMATE)
    if case=="malformed":
        proposal=replace(proposal,key=list(directive_key))
    gate=PhysicalCommitGate(adaptive_memory=None if case=="missing_memory" else memory,directive_proposal=proposal)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities=set() if case=="capability" else {intent.operation.lower()},authorized_epoch=1 if case=="epoch" else 0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    calls=[]
    original=bridge.adapter.execute_intent
    async def counted_execute(*args, **kwargs):
        calls.append(1)
        return await original(*args, **kwargs)
    monkeypatch.setattr(bridge.adapter,"execute_intent",counted_execute)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=gate)
    if case=="current":
        assert result.status=="EXECUTED"
        assert len(calls)==1
        assert bridge.adapter.device.state.volume==55.0
    else:
        assert calls==[]
        assert result.status=="REJECTED"
        expected={"capability":"CAPABILITY_DENIED","epoch":"EPOCH_DRIFT"}.get(case,"ADAPTIVE_PROPOSAL_INVALID")
        assert result.rejection.name==expected
        assert result.receipt is None


@pytest.mark.asyncio
@pytest.mark.parametrize("matches", [True,False])
async def test_bridge_proximity_proposal_device_binding(env, monkeypatch, matches):
    from src.edge.proximity_tv_selector import ProximityEvidence, select_nearest_tv
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    from src.device_fabric.physical_commit_gate import PhysicalCommitGate
    bridge,intent,lease,key=env
    bridge.adapter.device.state.volume=80.0
    selected_id=intent.device_id if matches else "other_tv"
    selected=select_nearest_tv([ProximityEvidence(selected_id,2.0,99.0,True)],now=100.0,radius_m=5.0,max_age_s=2.0,ambiguity_m=0.5,switch_margin_m=1.0)
    assert selected==selected_id
    memory=AdaptiveDirectiveMemory(max_entries=2)
    directive_key=("profile_1",selected,"commercial","channel_alpha")
    memory.remember(directive_key,action="lower_volume")
    memory.feedback(directive_key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(directive_key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    assert memory.proposal_is_current(proposal) is True
    gate=PhysicalCommitGate(adaptive_memory=memory,directive_proposal=proposal)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    calls=[]
    original=bridge.adapter.execute_intent
    async def counted_execute(*args, **kwargs):
        calls.append(1)
        return await original(*args, **kwargs)
    monkeypatch.setattr(bridge.adapter,"execute_intent",counted_execute)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=gate)
    if matches:
        assert result.status=="EXECUTED"
        assert calls==[1]
    else:
        assert calls==[]
        assert result.status=="REJECTED"
        assert result.rejection is PreconditionResult.DEVICE_MISMATCH
        assert result.receipt is None


@pytest.mark.asyncio
@pytest.mark.parametrize("action,target,allowed", [("lower_volume",55.0,True),("lower_volume",80.0,False),("lower_volume",90.0,False),("unmapped_action",55.0,False)])
async def test_bridge_adaptive_action_binding(env, monkeypatch, action, target, allowed):
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    from src.device_fabric.physical_commit_gate import PhysicalCommitGate
    bridge,intent,lease,key=env
    bridge.adapter.device.state.volume=80.0
    data={k:v for k,v in intent.__dict__.items() if k!="signature"}
    data["parameters"]={"volume":target}
    signature=key.sign(SignedActionIntent(**data,signature="").canonical_bytes)
    intent=SignedActionIntent(**data,signature=signature)
    memory=AdaptiveDirectiveMemory(max_entries=2)
    directive_key=("profile_1",intent.device_id,"commercial","channel_alpha")
    memory.remember(directive_key,action=action)
    memory.feedback(directive_key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(directive_key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    gate=PhysicalCommitGate(adaptive_memory=memory,directive_proposal=proposal)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    calls=[]
    original=bridge.adapter.execute_intent
    async def counted_execute(*args, **kwargs):
        calls.append(1)
        return await original(*args, **kwargs)
    monkeypatch.setattr(bridge.adapter,"execute_intent",counted_execute)
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=gate)
    if allowed:
        assert result.status=="EXECUTED"
        assert calls==[1]
        assert bridge.adapter.device.state.volume==target
    else:
        assert calls==[]
        assert result.status=="REJECTED"
        assert result.rejection.name=="ADAPTIVE_ACTION_MISMATCH"
        assert result.receipt is None


@pytest.mark.asyncio
async def test_legacy_bridge_timeout_is_indeterminate_and_cancels_transport(env):
    import asyncio

    bridge, intent, lease, key = env

    class HangingAdapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState()

        device = Dev()

        def __init__(self):
            self.calls = 0
            self.cancelled = False

        async def execute_intent(self, intent, transaction_digest=None, capability_digest=None):
            self.calls += 1
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    adapter = HangingAdapter()
    timed_bridge = Gen3DeviceFabricBridge(
        firewall=bridge.firewall,
        adapter=adapter,
        transport_timeout_seconds=0.02,
    )
    result = await asyncio.wait_for(
        timed_bridge.authorize_and_execute(intent, lease, adapter.device.state),
        timeout=0.20,
    )
    assert result.status == "FAILED"
    assert result.rejection == "UNKNOWN_PHYSICAL_STATE"
    assert result.transaction_id == intent.transaction_id
    assert result.capability_digest == lease.payload_digest
    assert result.verification is None
    assert adapter.calls == 1
    assert adapter.cancelled is True


@pytest.mark.asyncio
async def test_bridge_commit_timeout_is_indeterminate_and_cancels_transport(env):
    import asyncio

    bridge, intent, lease, key = env

    class HangingAdapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState()

        device = Dev()

        def __init__(self):
            self.calls = 0
            self.cancelled = False

        async def execute_intent(self, intent, transaction_digest=None, capability_digest=None):
            self.calls += 1
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    adapter = HangingAdapter()
    timed_bridge = Gen3DeviceFabricBridge(
        firewall=bridge.firewall,
        adapter=adapter,
        transport_timeout_seconds=0.02,
    )
    pre = adapter.device.state
    physical = CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=0,
    )
    snapshot = PhysicalSnapshot(
        device_id=intent.device_id,
        state=pre,
        epoch=0,
        observed_at=time.time(),
    )
    result = await asyncio.wait_for(
        timed_bridge.authorize_and_commit(intent, lease, physical, snapshot, pre),
        timeout=0.20,
    )
    assert result.status == "FAILED"
    assert result.rejection == "UNKNOWN_PHYSICAL_STATE"
    assert result.transaction_id == intent.transaction_id
    assert result.capability_digest == lease.payload_digest
    assert result.verification is None
    assert adapter.calls == 1
    assert adapter.cancelled is True


@pytest.mark.asyncio
async def test_bridge_commit_timeout_persists_recovery_required(env, tmp_path):
    import asyncio
    from src.device_fabric.physical_recovery_store import PhysicalRecoveryStatus, PhysicalRecoveryStore

    bridge, intent, lease, key = env

    class HangingAdapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState()

        device = Dev()

        def __init__(self):
            self.calls = 0
            self.cancelled = False

        async def execute_intent(self, intent, transaction_digest=None, capability_digest=None):
            self.calls += 1
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    adapter = HangingAdapter()
    recovery_path = tmp_path / "physical_recovery.sqlite3"
    recovery_store = PhysicalRecoveryStore(recovery_path)
    timed_bridge = Gen3DeviceFabricBridge(
        firewall=bridge.firewall,
        adapter=adapter,
        transport_timeout_seconds=0.02,
        recovery_store=recovery_store,
    )
    pre = adapter.device.state
    target = timed_bridge._translate_state(intent, pre)
    physical = CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=0,
    )
    snapshot = PhysicalSnapshot(
        device_id=intent.device_id,
        state=pre,
        epoch=0,
        observed_at=time.time(),
    )
    result = await asyncio.wait_for(
        timed_bridge.authorize_and_commit(intent, lease, physical, snapshot, pre),
        timeout=0.20,
    )
    pending = PhysicalRecoveryStore(recovery_path).pending()
    assert result.status == "FAILED"
    assert result.rejection == "UNKNOWN_PHYSICAL_STATE"
    assert result.verification is None
    assert adapter.calls == 1
    assert adapter.cancelled is True
    assert len(pending) == 1
    record = pending[0]
    assert record.status is PhysicalRecoveryStatus.RECOVERY_REQUIRED
    assert record.transaction_id == intent.transaction_id
    assert record.intent_id == intent.intent_id
    assert record.device_id == intent.device_id
    assert record.operation == intent.operation
    assert record.target_state_digest == target.state_digest
    assert record.expected_pre_state_digest == pre.state_digest
    assert record.authorization_digest == timed_bridge._authorization_digest(intent)
    assert record.capability_digest == lease.payload_digest
    assert record.precondition_epoch == snapshot.epoch


@pytest.mark.asyncio
async def test_legacy_bridge_timeout_persists_recovery_required(env, tmp_path):
    import asyncio
    from src.device_fabric.physical_recovery_store import PhysicalRecoveryStatus, PhysicalRecoveryStore

    bridge, intent, lease, key = env

    class HangingAdapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState()

        device = Dev()

        def __init__(self):
            self.calls = 0
            self.cancelled = False

        async def execute_intent(self, intent, transaction_digest=None, capability_digest=None):
            self.calls += 1
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    adapter = HangingAdapter()
    recovery_path = tmp_path / "physical_recovery.sqlite3"
    timed_bridge = Gen3DeviceFabricBridge(
        firewall=bridge.firewall,
        adapter=adapter,
        transport_timeout_seconds=0.02,
        recovery_store=PhysicalRecoveryStore(recovery_path),
    )
    pre = adapter.device.state
    target = timed_bridge._translate_state(intent, pre)
    result = await asyncio.wait_for(
        timed_bridge.authorize_and_execute(intent, lease, pre),
        timeout=0.20,
    )
    pending = PhysicalRecoveryStore(recovery_path).pending()
    assert result.status == "FAILED"
    assert result.rejection == "UNKNOWN_PHYSICAL_STATE"
    assert result.verification is None
    assert adapter.calls == 1
    assert adapter.cancelled is True
    assert len(pending) == 1
    record = pending[0]
    assert record.status is PhysicalRecoveryStatus.RECOVERY_REQUIRED
    assert record.transaction_id == intent.transaction_id
    assert record.intent_id == intent.intent_id
    assert record.device_id == intent.device_id
    assert record.operation == intent.operation
    assert record.target_state_digest == target.state_digest
    assert record.expected_pre_state_digest == pre.state_digest
    assert record.authorization_digest == timed_bridge._authorization_digest(intent)
    assert record.capability_digest == lease.payload_digest
    assert record.precondition_epoch is None


@pytest.mark.asyncio
async def test_bridge_timeout_recovery_persistence_failure_is_explicit(env):
    from src.device_fabric.physical_recovery_store import PhysicalRecoveryPersistenceError
    from src.device_fabric.transport import PhysicalTransportTimeout

    bridge, intent, lease, key = env

    class FailingRecoveryStore:
        def __init__(self):
            self.calls = 0

        def record(self, record):
            self.calls += 1
            raise OSError("recovery database unavailable")

    class TimingOutGate:
        def __init__(self):
            self.calls = 0

        async def commit(self, *args, **kwargs):
            self.calls += 1
            raise PhysicalTransportTimeout(intent.transaction_id, lease.payload_digest)

    recovery_store = FailingRecoveryStore()
    gate = TimingOutGate()
    timed_bridge = Gen3DeviceFabricBridge(
        firewall=bridge.firewall,
        adapter=bridge.adapter,
        recovery_store=recovery_store,
    )
    pre = bridge.adapter.device.state
    physical = CapabilityLease(
        device_id=intent.device_id,
        capabilities={intent.operation.lower()},
        authorized_epoch=0,
    )
    snapshot = PhysicalSnapshot(
        device_id=intent.device_id,
        state=pre,
        epoch=0,
        observed_at=time.time(),
    )
    with pytest.raises(PhysicalRecoveryPersistenceError, match="indeterminate physical state could not be persisted") as captured:
        await timed_bridge.authorize_and_commit(intent, lease, physical, snapshot, pre, commit_gate=gate)
    assert isinstance(captured.value.__cause__, OSError)
    assert gate.calls == 1
    assert recovery_store.calls == 1


@pytest.mark.asyncio
async def test_bridge_paused_protection_rejects_before_physical_commit_or_adapter(env):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    guarded.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await guarded.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_PAUSED"
    assert result.receipt is None
    assert result.verification is None
    assert adapter.calls==0


@pytest.mark.asyncio
async def test_legacy_bridge_paused_protection_cannot_bypass_adapter_gate(env):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    guarded.adapter=adapter
    result=await guarded.authorize_and_execute(intent,lease,adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_PAUSED"
    assert result.receipt is None
    assert result.verification is None
    assert adapter.calls==0


@pytest.mark.asyncio
async def test_bridge_rechecks_protection_after_authorization_before_physical_commit(env):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    observed_at=time.time()
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=observed_at,now=observed_at,monotonic_now=time.monotonic())
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    original_validate=guarded.firewall.validate_intent
    def interrupting_validate(candidate,candidate_lease):
        result=original_validate(candidate,candidate_lease)
        supervisor.interrupt("AUDIO_SESSION_INTERRUPTED",now=observed_at+0.1)
        return result
    guarded.firewall.validate_intent=interrupting_validate
    class CommitGate:
        calls=0
        async def commit(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("physical commit must not run after interruption")
    gate=CommitGate()
    pre=guarded.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=observed_at)
    result=await guarded.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=gate)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_PAUSED"
    assert result.receipt is None
    assert result.verification is None
    assert gate.calls==0


@pytest.mark.asyncio
async def test_legacy_bridge_rechecks_protection_before_transport(env):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    observed_at=time.time()
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=observed_at,now=observed_at,monotonic_now=time.monotonic())
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    original_validate=guarded.firewall.validate_intent
    def interrupting_validate(candidate,candidate_lease):
        result=original_validate(candidate,candidate_lease)
        supervisor.interrupt("AUDIO_SESSION_INTERRUPTED",now=observed_at+0.1)
        return result
    guarded.firewall.validate_intent=interrupting_validate
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("transport must not run after interruption")
    adapter=CountingAdapter()
    guarded.adapter=adapter
    result=await guarded.authorize_and_execute(intent,lease,adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_PAUSED"
    assert result.receipt is None
    assert result.verification is None
    assert adapter.calls==0


@pytest.mark.asyncio
@pytest.mark.parametrize("prerequisites,observation_offset,expected",[
    ({"permission_granted":False,"runtime_eligible":True,"sensor_available":True,"connected":True,"authority_valid":True,"protection_path_eligible":True},0.0,"PROTECTION_PAUSED"),
    ({"permission_granted":True,"runtime_eligible":True,"sensor_available":False,"connected":True,"authority_valid":True,"protection_path_eligible":True},0.0,"PROTECTION_DEGRADED"),
    ({"permission_granted":True,"runtime_eligible":True,"sensor_available":True,"connected":True,"authority_valid":False,"protection_path_eligible":True},0.0,"PROTECTION_RECOVERY_REQUIRED"),
    ({"permission_granted":True,"runtime_eligible":True,"sensor_available":True,"connected":True,"authority_valid":True,"protection_path_eligible":False},0.0,"PROTECTION_DEGRADED"),
    ({"permission_granted":True,"runtime_eligible":True,"sensor_available":True,"connected":True,"authority_valid":True,"protection_path_eligible":True},1.0,"PROTECTION_UNKNOWN_PHYSICAL_STATE"),
])
async def test_bridge_all_unavailable_protection_states_reject_without_actuation(env,prerequisites,observation_offset,expected):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    now=time.time()
    supervisor.validate(**prerequisites,observed_at=now+observation_offset,now=now)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    guarded.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=now)
    result=await guarded.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection==expected
    assert result.receipt is None
    assert result.verification is None
    assert adapter.calls==0


@pytest.mark.asyncio
async def test_bridge_protection_rejection_does_not_consume_intent_nonce(env):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    pre=guarded.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    rejected=await guarded.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert rejected.status=="REJECTED"
    assert rejected.rejection=="PROTECTION_PAUSED"
    assert rejected.receipt is None
    assert rejected.verification is None
    assert guarded.adapter.device.state.volume!=55.0
    activated_at=time.time()
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=activated_at,now=activated_at,monotonic_now=time.monotonic())
    executed=await guarded.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert executed.status=="EXECUTED"
    assert executed.receipt is not None
    assert guarded.adapter.device.state.volume==55.0


@pytest.mark.asyncio
async def test_bridge_faulting_protection_supervisor_fails_closed_without_actuation(env,monkeypatch):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    def fault():
        raise RuntimeError("protection status unavailable")
    monkeypatch.setattr(supervisor,"require_automation",fault)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    adapter=CountingAdapter()
    guarded.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await guarded.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_UNKNOWN_PHYSICAL_STATE"
    assert result.receipt is None
    assert result.verification is None
    assert adapter.calls==0


def test_protected_bridge_factory_requires_supervisor(env):
    from src.control.device_fabric_bridge import build_protected_device_fabric_bridge
    bridge,intent,lease,key=env
    with pytest.raises(ValueError,match="ProtectionSupervisor is required"):
        build_protected_device_fabric_bridge(bridge.firewall,bridge.adapter,None)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    protected=build_protected_device_fabric_bridge(bridge.firewall,bridge.adapter,supervisor)
    assert isinstance(protected,Gen3DeviceFabricBridge)
    assert protected.protection_supervisor is supervisor


def test_production_code_does_not_construct_unprotected_bridge_directly():
    import ast
    from pathlib import Path
    violations=[]
    for source_path in Path("src").rglob("*.py"):
        if not source_path.is_file() or source_path.name=="device_fabric_bridge.py":
            continue
        source=source_path.read_text(encoding="utf-8",errors="replace")
        if "Gen3DeviceFabricBridge" not in source:
            continue
        tree=ast.parse(source,filename=str(source_path))
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):
                continue
            called=node.func
            name=called.id if isinstance(called,ast.Name) else called.attr if isinstance(called,ast.Attribute) else None
            if name=="Gen3DeviceFabricBridge":
                violations.append((str(source_path),node.lineno))
    assert violations==[]


@pytest.mark.asyncio
async def test_bridge_rejects_evidence_that_ages_out_before_commit(env):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    observed_at=time.time()-3.0
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=observed_at,now=observed_at,monotonic_now=time.monotonic()-3.0)
    assert supervisor.state is ProtectionState.ACTIVE
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    class CountingAdapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("stale protection evidence must block adapter execution")
    adapter=CountingAdapter()
    guarded.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await guarded.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_DEGRADED"
    assert result.receipt is None
    assert result.verification is None
    assert adapter.calls==0
    assert supervisor.state is ProtectionState.DEGRADED
    assert supervisor.reason=="STALE_EVIDENCE"


def test_bridge_protection_gate_supplies_dual_clocks(env,monkeypatch):
    bridge,intent,lease,key=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    wall_now=time.time()
    monotonic_now=time.monotonic()
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall_now,now=wall_now,monotonic_now=monotonic_now)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    observed={}
    original_gate=supervisor.require_automation
    def recording_gate(*,now=None,monotonic_now=None):
        observed["now"]=now
        observed["monotonic_now"]=monotonic_now
        return original_gate(now=now,monotonic_now=monotonic_now)
    monkeypatch.setattr(supervisor,"require_automation",recording_gate)
    assert guarded._protection_rejection(intent) is None
    assert isinstance(observed["now"],float)
    assert isinstance(observed["monotonic_now"],float)
    assert observed["monotonic_now"]>=monotonic_now


@pytest.mark.asyncio
async def test_bridge_timeout_latches_transaction_bound_unknown_physical_state(env,tmp_path):
    from src.device_fabric.physical_recovery_store import PhysicalRecoveryStore
    from src.device_fabric.transport import PhysicalTransportTimeout
    bridge,intent,lease,key=env
    class TimingOutGate:
        def __init__(self): self.calls=0
        async def commit(self,*args,**kwargs):
            self.calls+=1
            raise PhysicalTransportTimeout(intent.transaction_id,lease.payload_digest)
    wall_now=time.time()
    monotonic_now=time.monotonic()
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall_now,now=wall_now,observed_monotonic=monotonic_now,monotonic_now=monotonic_now)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    protected=Gen3DeviceFabricBridge(firewall=bridge.firewall,adapter=bridge.adapter,recovery_store=store,protection_supervisor=supervisor)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    gate=TimingOutGate()
    result=await protected.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=gate)
    assert result.status=="FAILED"
    assert result.rejection=="UNKNOWN_PHYSICAL_STATE"
    assert gate.calls==1
    assert store.get(intent.transaction_id) is not None
    status=supervisor.status(now=time.time(),monotonic_now=time.monotonic())
    assert status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert status.reason=="POST_CONDITION_UNOBSERVED"
    assert status.automation_allowed is False


@pytest.mark.asyncio
async def test_recovery_persistence_failure_latches_generic_unknown_physical_state(env):
    from src.device_fabric.physical_recovery_store import PhysicalRecoveryPersistenceError
    from src.device_fabric.transport import PhysicalTransportTimeout
    bridge,intent,lease,key=env
    class FailingRecoveryStore:
        def record(self,record): raise OSError("recovery database unavailable")
    class TimingOutGate:
        def __init__(self): self.calls=0
        async def commit(self,*args,**kwargs):
            self.calls+=1
            raise PhysicalTransportTimeout(intent.transaction_id,lease.payload_digest)
    wall_now=time.time()
    monotonic_now=time.monotonic()
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall_now,now=wall_now,observed_monotonic=monotonic_now,monotonic_now=monotonic_now)
    protected=Gen3DeviceFabricBridge(firewall=bridge.firewall,adapter=bridge.adapter,recovery_store=FailingRecoveryStore(),protection_supervisor=supervisor)
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    gate=TimingOutGate()
    with pytest.raises(PhysicalRecoveryPersistenceError):
        await protected.authorize_and_commit(intent,lease,physical,snapshot,pre,commit_gate=gate)
    assert gate.calls==1
    status=supervisor.status(now=time.time(),monotonic_now=time.monotonic())
    assert status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert status.reason=="POST_CONDITION_UNOBSERVED"
    assert status.automation_allowed is False


def test_protected_bridge_construction_rehydrates_pending_physical_recovery(env,tmp_path):
    from src.device_fabric.physical_recovery_store import PhysicalRecoveryRecord, PhysicalRecoveryStatus, PhysicalRecoveryStore
    bridge,intent,lease,key=env
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    store.record(PhysicalRecoveryRecord(transaction_id="tx-startup-pending-001",intent_id="intent-startup-pending-001",device_id=intent.device_id,operation=intent.operation,target_state_digest="a"*64,expected_pre_state_digest="b"*64,authorization_digest="c"*64,capability_digest="d"*64,recorded_at=time.time(),status=PhysicalRecoveryStatus.RECOVERY_REQUIRED))
    wall_now=time.time()
    monotonic_now=time.monotonic()
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall_now,now=wall_now,observed_monotonic=monotonic_now,monotonic_now=monotonic_now)
    assert supervisor.state is ProtectionState.ACTIVE
    protected=Gen3DeviceFabricBridge(firewall=bridge.firewall,adapter=bridge.adapter,recovery_store=store,protection_supervisor=supervisor)
    assert protected.protection_supervisor is supervisor
    status=supervisor.status(now=time.time(),monotonic_now=time.monotonic())
    assert status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert status.reason=="PENDING_PHYSICAL_RECOVERY"
    assert status.automation_allowed is False


@pytest.mark.asyncio
async def test_rehydrated_unknown_state_rejects_before_adapter_call(env,tmp_path):
    from src.device_fabric.physical_recovery_store import PhysicalRecoveryRecord, PhysicalRecoveryStatus, PhysicalRecoveryStore
    bridge,intent,lease,key=env
    class CountingAdapter:
        def __init__(self,device):
            self.device=device
            self.calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called while physical state is unresolved")
    adapter=CountingAdapter(bridge.adapter.device)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    store.record(PhysicalRecoveryRecord(transaction_id="tx-startup-isolation-001",intent_id="intent-startup-isolation-001",device_id=intent.device_id,operation=intent.operation,target_state_digest="a"*64,expected_pre_state_digest="b"*64,authorization_digest="c"*64,capability_digest="d"*64,recorded_at=time.time(),status=PhysicalRecoveryStatus.RECOVERY_REQUIRED))
    wall_now=time.time()
    monotonic_now=time.monotonic()
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall_now,now=wall_now,observed_monotonic=monotonic_now,monotonic_now=monotonic_now)
    protected=Gen3DeviceFabricBridge(firewall=bridge.firewall,adapter=adapter,recovery_store=store,protection_supervisor=supervisor)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await protected.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_UNKNOWN_PHYSICAL_STATE"
    assert adapter.calls==0
    assert supervisor.automation_allowed is False


@pytest.mark.asyncio
async def test_deferred_runtime_evidence_rejects_before_adapter_call(env):
    bridge,intent,lease,key=env
    class CountingAdapter:
        def __init__(self,device):
            self.device=device
            self.calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("deferred runtime must not reach physical adapter")
    adapter=CountingAdapter(bridge.adapter.device)
    wall_now=time.time()
    monotonic_now=time.monotonic()
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    evidence=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE),observed_at=wall_now,observed_monotonic=monotonic_now,runtime_mode=ProtectionRuntimeMode.DEFERRED_MAINTENANCE)
    coordinator=ProtectionEvidenceCoordinator(supervisor,lambda:evidence,wall_clock=lambda:wall_now,monotonic_clock=lambda:monotonic_now)
    assert coordinator.refresh() is ProtectionState.PAUSED
    protected=Gen3DeviceFabricBridge(firewall=bridge.firewall,adapter=adapter,protection_supervisor=supervisor)
    result=await protected.authorize_and_execute(intent,lease,adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_PAUSED"
    assert adapter.calls==0
    assert supervisor.reason=="RUNTIME_MODE_INELIGIBLE"
    assert supervisor.automation_allowed is False


@pytest.mark.asyncio
async def test_dispatched_permission_revocation_rejects_before_adapter_call(env):
    from src.control.protection_evidence_dispatcher import ProtectionEvidenceEventDispatcher
    from src.control.protection_evidence_source import ProtectionEvidenceSource
    bridge,intent,lease,key=env
    class CountingAdapter:
        def __init__(self,device):
            self.device=device
            self.calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("revoked permission must not reach physical adapter")
    adapter=CountingAdapter(bridge.adapter.device)
    wall_now=time.time()
    monotonic_now=time.monotonic()
    path=ProtectionPathAssessment(eligible=True,reason=ProtectionPathReason.ELIGIBLE)
    initial=ProtectionEvidence(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=wall_now,observed_monotonic=monotonic_now,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    revoked=ProtectionEvidence(permission_granted=False,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path=path,observed_at=wall_now+0.001,observed_monotonic=monotonic_now+0.001,runtime_mode=ProtectionRuntimeMode.USER_VISIBLE_CONTINUOUS)
    clock=[wall_now,monotonic_now]
    source=ProtectionEvidenceSource(initial)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    coordinator=ProtectionEvidenceCoordinator(supervisor,source.snapshot,wall_clock=lambda:clock[0],monotonic_clock=lambda:clock[1])
    dispatcher=ProtectionEvidenceEventDispatcher(supervisor,source,coordinator)
    assert coordinator.refresh() is ProtectionState.ACTIVE
    clock[:]=[revoked.observed_at,revoked.observed_monotonic]
    assert dispatcher.apply(revoked) is ProtectionState.PAUSED
    protected=Gen3DeviceFabricBridge(firewall=bridge.firewall,adapter=adapter,protection_supervisor=supervisor)
    result=await protected.authorize_and_execute(intent,lease,adapter.device.state)
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_PAUSED"
    assert result.receipt is None
    assert result.verification is None
    assert adapter.calls==0
    assert source.snapshot() is revoked
    assert supervisor.reason=="PERMISSION_DENIED"
    assert supervisor.automation_allowed is False

@pytest.mark.asyncio
@pytest.mark.parametrize("value",(True,-0.1,float("nan"),float("inf"),"45",None))
async def test_bridge_invalid_playback_position_never_reaches_adapter(env,value):
    bridge,intent,lease,key=env
    original_device=bridge.adapter.device
    class CountingAdapter:
        def __init__(self):
            self.device=original_device
            self.calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("invalid playback position reached adapter")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    data=dict(intent.__dict__)
    data["operation"]="SET_PLAYBACK_POSITION"
    data["parameters"]={"playback_position_seconds":value,"evidence_digest":"f"*64}
    data["signature"]=""
    data["signature"]=key.sign(SignedActionIntent(**data).canonical_bytes)
    playback_intent=SignedActionIntent(**data)
    pre=DeviceState(power=True,volume=10.0,playback_position_seconds=3.0)
    adapter.device.state=pre
    physical=CapabilityLease(device_id=playback_intent.device_id,capabilities={"set_playback_position"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=playback_intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(playback_intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert adapter.calls==0

@pytest.mark.asyncio
@pytest.mark.parametrize("world_digest",(None,"b"*64))
async def test_bridge_media_world_evidence_mismatch_never_reaches_adapter(env,world_digest):
    bridge,intent,lease,key=env
    original_device=bridge.adapter.device
    class CountingAdapter:
        def __init__(self):
            self.device=original_device
            self.calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("mismatched media evidence reached adapter")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    data=dict(intent.__dict__)
    data["operation"]="SET_PLAYBACK_POSITION"
    data["parameters"]={"playback_position_seconds":45.0,"observation_id":"observation-evidence-a","evidence_digest":"a"*64,"observed_monotonic":100.0,"segment_start_seconds":0.0,"segment_end_seconds":45.0,"directive_key":("profile-1",intent.device_id,"show_intro:provider-1","episode-1"),"directive_version":1}
    data["signature"]=""
    data["signature"]=key.sign(SignedActionIntent(**data).canonical_bytes)
    playback_intent=SignedActionIntent(**data)
    pre=DeviceState(power=True,playback_position_seconds=3.0)
    adapter.device.state=pre
    physical=CapabilityLease(device_id=playback_intent.device_id,capabilities={"set_playback_position"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=playback_intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(playback_intent,lease,physical,snapshot,pre,world_state_evidence_digest=world_digest)
    assert result.status=="REJECTED"
    assert result.rejection=="WORLD_STATE_EVIDENCE_MISMATCH"
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_legacy_bridge_rejects_media_playback_before_adapter(env):
    bridge,intent,lease,key=env
    original_device=bridge.adapter.device
    class CountingAdapter:
        def __init__(self):
            self.device=original_device
            self.calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("legacy media request reached adapter")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    data=dict(intent.__dict__)
    data["operation"]="SET_PLAYBACK_POSITION"
    data["parameters"]={"playback_position_seconds":45.0,"evidence_digest":"a"*64}
    data["signature"]=""
    data["signature"]=key.sign(SignedActionIntent(**data).canonical_bytes)
    playback_intent=SignedActionIntent(**data)
    result=await bridge.authorize_and_execute(playback_intent,lease,DeviceState(power=True,playback_position_seconds=3.0))
    assert result.status=="REJECTED"
    assert result.rejection=="PHYSICAL_COMMIT_REQUIRED"
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_rejects_playback_outside_signed_evidence_segment(env):
    bridge,intent,lease,key=env
    original_device=bridge.adapter.device
    class CountingAdapter:
        def __init__(self):
            self.device=original_device
            self.calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("out-of-segment playback request reached adapter")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    evidence_digest="d"*64
    data=dict(intent.__dict__)
    data["operation"]="SET_PLAYBACK_POSITION"
    data["parameters"]={"playback_position_seconds":45.0,"observation_id":"observation-segment-window","evidence_digest":evidence_digest,"observed_monotonic":100.0,"segment_start_seconds":10.0,"segment_end_seconds":45.0,"directive_key":("profile-1",intent.device_id,"show_intro:provider-1","episode-1"),"directive_version":1}
    data["signature"]=""
    data["signature"]=key.sign(SignedActionIntent(**data).canonical_bytes)
    playback_intent=SignedActionIntent(**data)
    pre=DeviceState(power=True,playback_position_seconds=3.0)
    adapter.device.state=pre
    physical=CapabilityLease(device_id=playback_intent.device_id,capabilities={"set_playback_position"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=playback_intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(playback_intent,lease,physical,snapshot,pre,world_state_evidence_digest=evidence_digest)
    assert result.status=="REJECTED"
    assert result.rejection=="PLAYBACK_OUTSIDE_EVIDENCE_SEGMENT"
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_rejects_generic_media_intent_without_controller_binding(env):
    bridge,intent,lease,key=env
    original_device=bridge.adapter.device
    class CountingAdapter:
        def __init__(self):
            self.device=original_device
            self.calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("generic media intent reached adapter")
    adapter=CountingAdapter()
    bridge.adapter=adapter
    evidence_digest="e"*64
    data=dict(intent.__dict__)
    data["operation"]="SET_PLAYBACK_POSITION"
    data["parameters"]={"playback_position_seconds":45.0,"observation_id":"observation-controller-required","evidence_digest":evidence_digest,"observed_monotonic":100.0,"segment_start_seconds":0.0,"segment_end_seconds":45.0,"directive_key":("profile-1",intent.device_id,"show_intro:provider-1","episode-1"),"directive_version":1}
    data["signature"]=""
    data["signature"]=key.sign(SignedActionIntent(**data).canonical_bytes)
    playback_intent=SignedActionIntent(**data)
    pre=DeviceState(power=True,playback_position_seconds=3.0)
    adapter.device.state=pre
    physical=CapabilityLease(device_id=playback_intent.device_id,capabilities={"set_playback_position"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=playback_intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(playback_intent,lease,physical,snapshot,pre,world_state_evidence_digest=evidence_digest)
    assert result.status=="REJECTED"
    assert result.rejection=="CONTROLLER_BOUND_INTENT_REQUIRED"
    assert adapter.calls==0

@pytest.mark.asyncio
async def test_bridge_observer_evidence_digest_mismatch_cannot_mint_verification(env):
    bridge,intent,lease,key=env
    pre=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=120)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=120,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    class Observer:
        calls=0
        async def __call__(self,device_id):
            self.calls+=1
            return PhysicalSnapshot(device_id=device_id,state=expected,epoch=121,observed_at=time.time(),evidence_digest="sha256:observer-evidence")
    observer=Observer()
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,world_state_evidence_digest="sha256:authorization-evidence",post_state_observer=observer,observed_state_evidence_digest="sha256:caller-claim")
    assert observer.calls==1
    assert result.status=="FAILED"
    assert result.rejection=="POST_STATE_EVIDENCE_MISMATCH"
    assert result.receipt is not None
    assert result.verification is None
    assert result.prior_state is None
    assert bridge.adapter.device.state.state_digest==expected.state_digest



@pytest.mark.asyncio
async def test_bridge_media_volume_percent_requires_verified_post_state(env):
    bridge, intent, lease, key = env
    data = dict(intent.__dict__)
    data.update(
        intent_id="media-volume-percent",
        parameters={"volume_percent": 42},
        nonce="media-volume-percent-nonce",
        transaction_id="tx-media-volume-percent",
        signature="",
    )
    unsigned = SignedActionIntent(**data)
    data["signature"] = key.sign(unsigned.canonical_bytes)
    media_intent = SignedActionIntent(**data)

    class Adapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState(volume=10)

        device = Dev()
        calls = 0

        async def execute_intent(self, intent, *args, **kwargs):
            self.calls += 1
            return ActuationReceipt(
                receipt_id="media-volume-receipt",
                intent_id=intent.intent_id,
                device_id="tv_integration_node_1",
                status=ActuationStatus.EXECUTED,
                transaction_id=intent.transaction_id,
                capability_digest=intent.capability_digest,
            )

    adapter = Adapter()
    bridge.adapter = adapter
    pre = adapter.device.state
    expected = DeviceState(
        power=pre.power,
        volume=42,
        muted=pre.muted,
        input_source=pre.input_source,
        channel=pre.channel,
        custom_state=dict(pre.custom_state),
        playback_position_seconds=pre.playback_position_seconds,
    )
    physical = CapabilityLease(
        device_id=media_intent.device_id,
        capabilities={"set_volume"},
        authorized_epoch=0,
    )
    snapshot = PhysicalSnapshot(
        device_id=media_intent.device_id,
        state=pre,
        epoch=0,
        observed_at=time.time(),
        evidence_digest="media-volume-prior-observation",
    )

    class Observer:
        calls = 0

        async def __call__(self, device_id):
            self.calls += 1
            return PhysicalSnapshot(
                device_id=device_id,
                state=expected,
                epoch=1,
                observed_at=time.time(),
                evidence_digest="media-volume-observation",
            )

    observer = Observer()
    result = await bridge.authorize_and_commit(
        media_intent,
        lease,
        physical,
        snapshot,
        pre,
        world_state_evidence_digest="media-volume-prior-observation",
        post_state_observer=observer,
        observed_state_evidence_digest="media-volume-observation",
    )

    assert result.status == "EXECUTED"
    assert adapter.calls == 1
    assert observer.calls == 1
    assert result.verification is not None
    assert result.verification.verification_status is VerificationStatus.VERIFIED
    assert result.verification.observed_state_digest == expected.state_digest
    assert result.verification.observed_state_evidence_digest == "media-volume-observation"
    assert isinstance(result.prior_state, MediaControlPriorState)
    assert result.prior_state.volume_percent == 10
    assert result.prior_state.prior_state_digest == pre.state_digest
    assert result.prior_state.prior_state_evidence_digest == "media-volume-prior-observation"
    assert result.prior_state.transaction_id == media_intent.transaction_id
    assert result.prior_state.authorization_digest == result.authorization_digest
    assert result.prior_state.capability_digest == result.capability_digest
    assert result.prior_state.expected_post_state_digest == result.verification.expected_state_digest
    assert isinstance(result.undo_candidate, MediaControlUndoCandidate)
    assert result.undo_candidate.source_transaction_id == media_intent.transaction_id
    assert result.undo_candidate.expected_current_state_digest == result.verification.observed_state_digest
    assert result.undo_candidate.operation == "set_volume"
    assert dict(result.undo_candidate.parameters) == {"volume_percent": 10}


@pytest.mark.asyncio
async def test_bridge_invalid_media_prior_state_rejects_before_actuation(env):
    bridge,intent,lease,key=env
    data=dict(intent.__dict__)
    data.update(intent_id="media-invalid-prior",parameters={"volume_percent":42},nonce="media-invalid-prior-nonce",transaction_id="tx-media-invalid-prior",signature="")
    unsigned=SignedActionIntent(**data)
    data["signature"]=key.sign(unsigned.canonical_bytes)
    media_intent=SignedActionIntent(**data)
    class Adapter:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState(volume=True)
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            raise AssertionError("invalid prior state must reject before actuation")
    adapter=Adapter()
    bridge.adapter=adapter
    pre=adapter.device.state
    physical=CapabilityLease(device_id=media_intent.device_id,capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=media_intent.device_id,state=pre,epoch=0,observed_at=time.time(),evidence_digest="media-invalid-prior-evidence")
    result=await bridge.authorize_and_commit(media_intent,lease,physical,snapshot,pre,world_state_evidence_digest="media-invalid-prior-evidence")
    assert result.status=="REJECTED"
    assert result.rejection=="PRIOR_STATE_CAPTURE_INVALID"
    assert adapter.calls==0
    assert result.receipt is None
    assert result.verification is None
    assert result.verified_state is None
    assert result.prior_state is None
    assert result.undo_candidate is None


@pytest.mark.parametrize(
    "parameters",
    (
        {"volume_percent": None},
        {"volume_percent": True},
        {"volume_percent": 42.0},
        {"volume_percent": "42"},
        {"volume_percent": -1},
        {"volume_percent": 101},
        {"volume_percent": 42, "extra": True},
        {"volume_percent": 42, "volume": 55},
    ),
)
@pytest.mark.asyncio
async def test_bridge_invalid_media_volume_percent_never_reaches_adapter(
    env,
    parameters,
):
    bridge, intent, lease, key = env
    data = dict(intent.__dict__)
    data.update(
        intent_id="invalid-media-volume-percent",
        parameters=parameters,
        nonce="invalid-media-volume-percent-nonce",
        transaction_id="tx-invalid-media-volume-percent",
        signature="",
    )
    unsigned = SignedActionIntent(**data)
    data["signature"] = key.sign(unsigned.canonical_bytes)
    media_intent = SignedActionIntent(**data)

    class CountingAdapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState(volume=10)

        device = Dev()
        calls = 0

        async def execute_intent(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("adapter must not be called")

    adapter = CountingAdapter()
    bridge.adapter = adapter
    pre = adapter.device.state
    physical = CapabilityLease(
        device_id=media_intent.device_id,
        capabilities={"set_volume"},
        authorized_epoch=0,
    )
    snapshot = PhysicalSnapshot(
        device_id=media_intent.device_id,
        state=pre,
        epoch=0,
        observed_at=time.time(),
    )

    result = await bridge.authorize_and_commit(
        media_intent,
        lease,
        physical,
        snapshot,
        pre,
    )

    assert adapter.calls == 0
    assert result.status == "REJECTED"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_captions_enabled_requires_verified_post_state(env):
    bridge, intent, lease, key = env
    data = dict(intent.__dict__)
    data.update(
        intent_id="media-captions-enabled",
        operation="SET_CAPTIONS_ENABLED",
        parameters={"enabled": True},
        nonce="media-captions-enabled-nonce",
        transaction_id="tx-media-captions-enabled",
        signature="",
    )
    unsigned = SignedActionIntent(**data)
    data["signature"] = key.sign(unsigned.canonical_bytes)
    media_intent = SignedActionIntent(**data)

    class Adapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState(custom_state={"captions_enabled": False})

        device = Dev()
        calls = 0

        async def execute_intent(self, intent, *args, **kwargs):
            self.calls += 1
            self.device.state = intent.target_state
            return ActuationReceipt(
                receipt_id="media-captions-receipt",
                intent_id=intent.intent_id,
                device_id="tv_integration_node_1",
                status=ActuationStatus.EXECUTED,
                transaction_id=intent.transaction_id,
                capability_digest=intent.capability_digest,
            )

    adapter = Adapter()
    bridge.adapter = adapter
    pre = adapter.device.state
    physical = CapabilityLease(
        device_id=media_intent.device_id,
        capabilities={"set_captions_enabled"},
        authorized_epoch=0,
    )
    snapshot = PhysicalSnapshot(
        device_id=media_intent.device_id,
        state=pre,
        epoch=0,
        observed_at=time.time(),
    )

    class Observer:
        calls = 0

        async def __call__(self, device_id):
            self.calls += 1
            return PhysicalSnapshot(
                device_id=device_id,
                state=adapter.device.state,
                epoch=1,
                observed_at=time.time(),
                evidence_digest="media-captions-observation",
            )

    observer = Observer()
    result = await bridge.authorize_and_commit(
        media_intent,
        lease,
        physical,
        snapshot,
        pre,
        post_state_observer=observer,
        observed_state_evidence_digest="media-captions-observation",
    )

    assert result.status == "EXECUTED"
    assert adapter.calls == 1
    assert observer.calls == 1
    assert adapter.device.state.custom_state["captions_enabled"] is True
    assert result.verification is not None
    assert result.verification.verification_status is VerificationStatus.VERIFIED
    assert result.verification.observed_state_digest == adapter.device.state.state_digest
    assert result.verification.observed_state_evidence_digest == "media-captions-observation"


@pytest.mark.parametrize(
    "parameters",
    (
        {},
        {"enabled": None},
        {"enabled": 1},
        {"enabled": "true"},
        {"enabled": True, "extra": False},
    ),
)
@pytest.mark.asyncio
async def test_bridge_invalid_captions_enabled_never_reaches_adapter(
    env,
    parameters,
):
    bridge, intent, lease, key = env
    data = dict(intent.__dict__)
    data.update(
        intent_id="invalid-media-captions-enabled",
        operation="SET_CAPTIONS_ENABLED",
        parameters=parameters,
        nonce="invalid-media-captions-enabled-nonce",
        transaction_id="tx-invalid-media-captions-enabled",
        signature="",
    )
    unsigned = SignedActionIntent(**data)
    data["signature"] = key.sign(unsigned.canonical_bytes)
    media_intent = SignedActionIntent(**data)

    class CountingAdapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState(custom_state={"captions_enabled": False})

        device = Dev()
        calls = 0

        async def execute_intent(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("adapter must not be called")

    adapter = CountingAdapter()
    bridge.adapter = adapter
    pre = adapter.device.state
    physical = CapabilityLease(
        device_id=media_intent.device_id,
        capabilities={"set_captions_enabled"},
        authorized_epoch=0,
    )
    snapshot = PhysicalSnapshot(
        device_id=media_intent.device_id,
        state=pre,
        epoch=0,
        observed_at=time.time(),
    )

    result = await bridge.authorize_and_commit(
        media_intent,
        lease,
        physical,
        snapshot,
        pre,
    )

    assert adapter.calls == 0
    assert result.status == "REJECTED"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_eq_preset_requires_verified_post_state(env):
    bridge, intent, lease, key = env
    data = dict(intent.__dict__)
    data.update(intent_id="media-eq-preset", operation="SET_EQ_PRESET", parameters={"preset": "DIALOGUE"}, nonce="media-eq-preset-nonce", transaction_id="tx-media-eq-preset", signature="")
    unsigned = SignedActionIntent(**data)
    data["signature"] = key.sign(unsigned.canonical_bytes)
    media_intent = SignedActionIntent(**data)

    class Adapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState(custom_state={"eq_preset": "FLAT", "eq_bands": [{"frequency_hz": 1000.0, "gain_db": 1.0}], "room_mode": "quiet"})

        device = Dev()
        calls = 0

        async def execute_intent(self, intent, *args, **kwargs):
            self.calls += 1
            self.device.state = intent.target_state
            return ActuationReceipt(receipt_id="media-eq-preset-receipt", intent_id=intent.intent_id, device_id="tv_integration_node_1", status=ActuationStatus.EXECUTED, transaction_id=intent.transaction_id, capability_digest=intent.capability_digest)

    adapter = Adapter()
    bridge.adapter = adapter
    pre = adapter.device.state
    physical = CapabilityLease(device_id=media_intent.device_id, capabilities={"set_eq_preset"}, authorized_epoch=0)
    snapshot = PhysicalSnapshot(device_id=media_intent.device_id, state=pre, epoch=0, observed_at=time.time())

    class Observer:
        calls = 0

        async def __call__(self, device_id):
            self.calls += 1
            return PhysicalSnapshot(device_id=device_id, state=adapter.device.state, epoch=1, observed_at=time.time(), evidence_digest="media-eq-preset-observation")

    observer = Observer()
    result = await bridge.authorize_and_commit(media_intent, lease, physical, snapshot, pre, post_state_observer=observer, observed_state_evidence_digest="media-eq-preset-observation")

    assert result.status == "EXECUTED"
    assert adapter.calls == 1
    assert observer.calls == 1
    assert adapter.device.state.custom_state["eq_preset"] == "DIALOGUE"
    assert "eq_bands" not in adapter.device.state.custom_state
    assert adapter.device.state.custom_state["room_mode"] == "quiet"
    assert result.verification is not None
    assert result.verification.verification_status is VerificationStatus.VERIFIED
    assert result.verification.observed_state_digest == adapter.device.state.state_digest
    assert result.verification.observed_state_evidence_digest == "media-eq-preset-observation"
    assert isinstance(result.verified_state, VerifiedMediaControlState)
    assert result.verified_state.device_id == media_intent.device_id
    assert result.verified_state.eq_preset.value == "DIALOGUE"
    assert result.verified_state.observed_state_digest == result.verification.observed_state_digest


@pytest.mark.parametrize(
    "parameters",
    (
        {},
        {"preset": None},
        {"preset": True},
        {"preset": 1},
        {"preset": "dialogue"},
        {"preset": "UNKNOWN"},
        {"preset": "DIALOGUE", "extra": True},
    ),
)
@pytest.mark.asyncio
async def test_bridge_invalid_eq_preset_never_reaches_adapter(env, parameters):
    bridge, intent, lease, key = env
    data = dict(intent.__dict__)
    data.update(intent_id="invalid-media-eq-preset", operation="SET_EQ_PRESET", parameters=parameters, nonce="invalid-media-eq-preset-nonce", transaction_id="tx-invalid-media-eq-preset", signature="")
    unsigned = SignedActionIntent(**data)
    data["signature"] = key.sign(unsigned.canonical_bytes)
    media_intent = SignedActionIntent(**data)

    class CountingAdapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState(custom_state={"eq_preset": "FLAT"})

        device = Dev()
        calls = 0

        async def execute_intent(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("adapter must not be called")

    adapter = CountingAdapter()
    bridge.adapter = adapter
    pre = adapter.device.state
    physical = CapabilityLease(device_id=media_intent.device_id, capabilities={"set_eq_preset"}, authorized_epoch=0)
    snapshot = PhysicalSnapshot(device_id=media_intent.device_id, state=pre, epoch=0, observed_at=time.time())
    result = await bridge.authorize_and_commit(media_intent, lease, physical, snapshot, pre)

    assert adapter.calls == 0
    assert result.status == "REJECTED"
    assert result.verification is None
    assert result.verified_state is None


@pytest.mark.asyncio
async def test_bridge_eq_bands_requires_verified_post_state(env):
    bridge, intent, lease, key = env
    requested_bands = [
        {"frequency_hz": 250, "gain_db": -2},
        {"frequency_hz": 1000.0, "gain_db": 3.5},
        {"frequency_hz": 4000, "gain_db": 1},
    ]
    expected_bands = [
        {"frequency_hz": 250.0, "gain_db": -2.0},
        {"frequency_hz": 1000.0, "gain_db": 3.5},
        {"frequency_hz": 4000.0, "gain_db": 1.0},
    ]
    data = dict(intent.__dict__)
    data.update(intent_id="media-eq-bands", operation="SET_EQ_BANDS", parameters={"bands": requested_bands}, nonce="media-eq-bands-nonce", transaction_id="tx-media-eq-bands", signature="")
    unsigned = SignedActionIntent(**data)
    data["signature"] = key.sign(unsigned.canonical_bytes)
    media_intent = SignedActionIntent(**data)

    class Adapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState(custom_state={"eq_preset": "MUSIC", "eq_bands": [{"frequency_hz": 500.0, "gain_db": 0.0}], "room_mode": "quiet"})

        device = Dev()
        calls = 0

        async def execute_intent(self, intent, *args, **kwargs):
            self.calls += 1
            self.device.state = intent.target_state
            return ActuationReceipt(receipt_id="media-eq-bands-receipt", intent_id=intent.intent_id, device_id="tv_integration_node_1", status=ActuationStatus.EXECUTED, transaction_id=intent.transaction_id, capability_digest=intent.capability_digest)

    adapter = Adapter()
    bridge.adapter = adapter
    pre = adapter.device.state
    physical = CapabilityLease(device_id=media_intent.device_id, capabilities={"set_eq_bands"}, authorized_epoch=0)
    snapshot = PhysicalSnapshot(device_id=media_intent.device_id, state=pre, epoch=0, observed_at=time.time())

    class Observer:
        calls = 0

        async def __call__(self, device_id):
            self.calls += 1
            return PhysicalSnapshot(device_id=device_id, state=adapter.device.state, epoch=1, observed_at=time.time(), evidence_digest="media-eq-bands-observation")

    observer = Observer()
    result = await bridge.authorize_and_commit(media_intent, lease, physical, snapshot, pre, post_state_observer=observer, observed_state_evidence_digest="media-eq-bands-observation")

    assert result.status == "EXECUTED"
    assert adapter.calls == 1
    assert observer.calls == 1
    assert adapter.device.state.custom_state["eq_bands"] == expected_bands
    assert all(type(band["frequency_hz"]) is float and type(band["gain_db"]) is float for band in adapter.device.state.custom_state["eq_bands"])
    assert "eq_preset" not in adapter.device.state.custom_state
    assert adapter.device.state.custom_state["room_mode"] == "quiet"
    assert result.verification is not None
    assert result.verification.verification_status is VerificationStatus.VERIFIED
    assert result.verification.observed_state_digest == adapter.device.state.state_digest
    assert result.verification.observed_state_evidence_digest == "media-eq-bands-observation"
    assert isinstance(result.verified_state, VerifiedMediaControlState)
    assert result.verified_state.eq_preset is None
    assert [(band.frequency_hz, band.gain_db) for band in result.verified_state.eq_bands] == [(250.0, -2.0), (1000.0, 3.5), (4000.0, 1.0)]
    assert result.verified_state.observed_state_digest == result.verification.observed_state_digest


@pytest.mark.parametrize(
    "parameters",
    (
        {},
        {"bands": None},
        {"bands": ({"frequency_hz": 1000, "gain_db": 0},)},
        {"bands": []},
        {"bands": [{"frequency_hz": 1000, "gain_db": 0}] * 11},
        {"bands": [None]},
        {"bands": [{"frequency_hz": 1000}]},
        {"bands": [{"frequency_hz": 1000, "gain_db": 0, "extra": True}]},
        {"bands": [{"frequency_hz": True, "gain_db": 0}]},
        {"bands": [{"frequency_hz": "1000", "gain_db": 0}]},
        {"bands": [{"frequency_hz": 19.9, "gain_db": 0}]},
        {"bands": [{"frequency_hz": 20000.1, "gain_db": 0}]},
        {"bands": [{"frequency_hz": 1000, "gain_db": True}]},
        {"bands": [{"frequency_hz": 1000, "gain_db": "0"}]},
        {"bands": [{"frequency_hz": 1000, "gain_db": -12.1}]},
        {"bands": [{"frequency_hz": 1000, "gain_db": 12.1}]},
        {"bands": [{"frequency_hz": 1000, "gain_db": 0}, {"frequency_hz": 1000, "gain_db": 1}]},
        {"bands": [{"frequency_hz": 1000, "gain_db": 0}, {"frequency_hz": 500, "gain_db": 1}]},
        {"bands": [{"frequency_hz": 1000, "gain_db": 0}], "extra": True},
    ),
)
@pytest.mark.asyncio
async def test_bridge_invalid_eq_bands_never_reaches_adapter(env, parameters):
    bridge, intent, lease, key = env
    data = dict(intent.__dict__)
    data.update(intent_id="invalid-media-eq-bands", operation="SET_EQ_BANDS", parameters=parameters, nonce="invalid-media-eq-bands-nonce", transaction_id="tx-invalid-media-eq-bands", signature="")
    unsigned = SignedActionIntent(**data)
    data["signature"] = key.sign(unsigned.canonical_bytes)
    media_intent = SignedActionIntent(**data)

    class CountingAdapter:
        class Dev:
            class Id:
                device_id = "tv_integration_node_1"

            identity = Id()
            state = DeviceState(custom_state={"eq_preset": "FLAT"})

        device = Dev()
        calls = 0

        async def execute_intent(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("adapter must not be called")

    adapter = CountingAdapter()
    bridge.adapter = adapter
    pre = adapter.device.state
    physical = CapabilityLease(device_id=media_intent.device_id, capabilities={"set_eq_bands"}, authorized_epoch=0)
    snapshot = PhysicalSnapshot(device_id=media_intent.device_id, state=pre, epoch=0, observed_at=time.time())
    result = await bridge.authorize_and_commit(media_intent, lease, physical, snapshot, pre)

    assert adapter.calls == 0
    assert result.status == "REJECTED"
    assert result.verification is None


@pytest.mark.asyncio
async def test_bridge_durable_not_applied_tombstone_rejects_late_delivery_without_receipt(env,tmp_path):
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    from src.device_fabric.fenced_transport import FencedPhysicalTransport
    bridge,intent,lease,key=env
    class CountingDelegate:
        def __init__(self,transport):
            self.device=transport.device
            self._transport=transport
            self.calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return await self._transport.execute_intent(intent,*args,**kwargs)
    delegate=CountingDelegate(bridge.adapter)
    class AcceptingFenceStore:
        def __init__(self):
            self.calls=0
        def accept(self,resource_id,controller_id,token):
            self.calls+=1
            return True
    path=tmp_path/"endpoint-finality.sqlite3"
    EndpointTransactionFinalityStore(path).record_not_applied(intent.transaction_id,device_id=intent.device_id)
    finality_store=EndpointTransactionFinalityStore(path)
    fence_store=AcceptingFenceStore()
    bridge.adapter=FencedPhysicalTransport(delegate,fence_store,transaction_finality_store=finality_store)
    pre=delegate.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=901)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=901,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert result.status=="REJECTED"
    assert result.receipt is None
    assert result.verification is None
    assert fence_store.calls==0
    assert delegate.calls==0


@pytest.mark.asyncio
async def test_bridge_invalidation_inside_commit_blocks_dispatch(env):
    from src.device_fabric.physical_commit_gate import PhysicalCommitGate
    from src.device_fabric.precondition_gate import PreconditionGate
    bridge,intent,lease,_=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    wall,mono=time.time(),time.monotonic()
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall,now=wall,observed_monotonic=mono,monotonic_now=mono)
    class InterruptingGate(PreconditionGate):
        def evaluate(self,*args):
            decision=super().evaluate(*args)
            assert decision is PreconditionResult.ALLOW
            supervisor.interrupt("AUDIO_SESSION_INTERRUPTED",now=time.time(),monotonic_now=time.monotonic())
            return decision
    class Spy:
        def __init__(self,device):
            self.device=device
            self.calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter invoked after interruption")
    adapter=Spy(bridge.adapter.device)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,adapter,protection_supervisor=supervisor)
    before=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=before,epoch=0,observed_at=wall)
    result=await guarded.authorize_and_commit(intent,lease,physical,snapshot,before,commit_gate=PhysicalCommitGate(precondition_gate=InterruptingGate()))
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.rejection=="PROTECTION_PAUSED"
    assert result.receipt is None and result.verification is None


@pytest.mark.asyncio
async def test_protected_active_commit_preserves_lineage(env):
    bridge,intent,lease,_=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    wall,mono=time.time(),time.monotonic()
    assert supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall,now=wall,observed_monotonic=mono,monotonic_now=mono) is ProtectionState.ACTIVE
    guarded=Gen3DeviceFabricBridge(bridge.firewall,bridge.adapter,protection_supervisor=supervisor)
    before=bridge.adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=before,epoch=0,observed_at=wall)
    result=await guarded.authorize_and_commit(intent,lease,physical,snapshot,before)
    assert result.status=="EXECUTED"
    assert result.receipt is not None and result.receipt.intent_id==intent.intent_id
    assert result.authorization_digest==guarded._authorization_digest(intent)
    assert result.transaction_id==intent.transaction_id
    assert result.capability_digest==lease.payload_digest
    assert bridge.adapter.device.state.volume==55.0


@pytest.mark.asyncio
async def test_interruption_during_commit_wait_blocks_adapter(env):
    import asyncio
    bridge,intent,lease,_=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    wall,mono=time.time(),time.monotonic()
    assert supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall,now=wall,observed_monotonic=mono,monotonic_now=mono) is ProtectionState.ACTIVE
    started,resume=asyncio.Event(),asyncio.Event()
    class WaitingGate:
        async def commit(self,authorized,physical_lease,snapshot,adapter):
            started.set()
            await resume.wait()
            return await adapter.execute_intent(intent=authorized,transaction_digest=authorized.transaction_id,capability_digest=authorized.capability_digest)
    class Spy:
        def __init__(self,device):
            self.device=device
            self.calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("adapter invoked after interruption")
    adapter=Spy(bridge.adapter.device)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,adapter,protection_supervisor=supervisor)
    before=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=before,epoch=0,observed_at=wall)
    task=asyncio.create_task(guarded.authorize_and_commit(intent,lease,physical,snapshot,before,commit_gate=WaitingGate()))
    await asyncio.wait_for(started.wait(),5)
    supervisor.interrupt("AUDIO_SESSION_INTERRUPTED",now=time.time(),monotonic_now=time.monotonic())
    resume.set()
    result=await task
    assert adapter.calls==0
    assert result.status=="REJECTED" and result.rejection=="PROTECTION_PAUSED"
    assert result.receipt is None and result.verification is None


@pytest.mark.asyncio
async def test_revalidation_does_not_revive_waiting_commit(env):
    import asyncio
    bridge,intent,lease,_=env
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    wall,mono=time.time(),time.monotonic()
    assert supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall,now=wall,observed_monotonic=mono,monotonic_now=mono) is ProtectionState.ACTIVE
    started,resume=asyncio.Event(),asyncio.Event()
    class WaitingGate:
        async def commit(self,authorized,physical_lease,snapshot,adapter):
            started.set()
            await resume.wait()
            return await adapter.execute_intent(intent=authorized,transaction_digest=authorized.transaction_id,capability_digest=authorized.capability_digest)
    class Spy:
        def __init__(self,device):
            self.device=device
            self.calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("old admission reached adapter after revalidation")
    adapter=Spy(bridge.adapter.device)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,adapter,protection_supervisor=supervisor)
    before=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=before,epoch=0,observed_at=wall)
    task=asyncio.create_task(guarded.authorize_and_commit(intent,lease,physical,snapshot,before,commit_gate=WaitingGate()))
    await asyncio.wait_for(started.wait(),5)
    supervisor.interrupt("AUDIO_SESSION_INTERRUPTED",now=time.time(),monotonic_now=time.monotonic())
    time.sleep(0.001)
    fresh_wall,fresh_mono=time.time(),time.monotonic()
    assert supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=fresh_wall,now=fresh_wall,observed_monotonic=fresh_mono,monotonic_now=fresh_mono) is ProtectionState.ACTIVE
    resume.set()
    result=await task
    assert adapter.calls==0
    assert result.status=="REJECTED"
    assert result.receipt is None and result.verification is None


@pytest.mark.asyncio
async def test_evidence_expiry_during_commit_wait_blocks_adapter(env,monkeypatch):
    import asyncio
    import importlib
    from types import SimpleNamespace
    bridge_module=importlib.import_module("src.control.device_fabric_bridge")
    bridge,intent,lease,_=env
    supervisor=ProtectionSupervisor(max_evidence_age=2.0)
    wall,mono=time.time(),time.monotonic()
    assert supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall,now=wall,observed_monotonic=mono,monotonic_now=mono) is ProtectionState.ACTIVE
    clock=[mono]
    monkeypatch.setattr(bridge_module,"time",SimpleNamespace(time=time.time,monotonic=lambda:clock[0]))
    started,resume=asyncio.Event(),asyncio.Event()
    class WaitingGate:
        async def commit(self,authorized,physical_lease,snapshot,adapter):
            started.set()
            await resume.wait()
            return await adapter.execute_intent(intent=authorized,transaction_digest=authorized.transaction_id,capability_digest=authorized.capability_digest)
    class Spy:
        def __init__(self,device):
            self.device=device
            self.calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("expired evidence reached adapter")
    adapter=Spy(bridge.adapter.device)
    guarded=Gen3DeviceFabricBridge(bridge.firewall,adapter,protection_supervisor=supervisor)
    before=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=before,epoch=0,observed_at=wall)
    task=asyncio.create_task(guarded.authorize_and_commit(intent,lease,physical,snapshot,before,commit_gate=WaitingGate()))
    await asyncio.wait_for(started.wait(),5)
    clock[0]=mono+3.0
    resume.set()
    result=await task
    assert adapter.calls==0
    assert result.status=="REJECTED" and result.rejection=="PROTECTION_DEGRADED"
    assert result.receipt is None and result.verification is None
    assert supervisor.reason=="STALE_EVIDENCE"
