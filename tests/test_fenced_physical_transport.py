from types import SimpleNamespace
import pytest
from src.device_fabric.contracts import ActuationReceipt,ActuationStatus
from src.device_fabric.fenced_transport import FencedPhysicalTransport


class RejectingFenceStore:
    def __init__(self):
        self.calls=0

    def accept(self,resource_id,controller_id,token):
        self.calls+=1
        return False


class CountingTransport:
    def __init__(self):
        self.calls=0
        self.device=SimpleNamespace(identity=SimpleNamespace(device_id="tv-fenced"))

    async def execute_intent(self,intent,transaction_digest=None,capability_digest=None):
        self.calls+=1
        return ActuationReceipt(receipt_id="underlying",intent_id=intent.intent_id,status=ActuationStatus.EXECUTED,device_id=intent.device_id,transaction_id=transaction_digest or intent.transaction_id,capability_digest=capability_digest or intent.capability_digest)


@pytest.mark.asyncio
async def test_stale_controller_fence_never_reaches_wrapped_transport():
    delegate=CountingTransport()
    fence_store=RejectingFenceStore()
    transport=FencedPhysicalTransport(delegate,fence_store)
    intent=SimpleNamespace(intent_id="intent-stale",device_id="tv-fenced",controller_resource_id="tv:living-room",controller_id="phone-a",controller_fencing_token=8,transaction_id="tx-stale",capability_digest="cap-stale")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-stale",capability_digest="cap-stale")
    assert receipt.status is ActuationStatus.REJECTED
    assert receipt.intent_id=="intent-stale"
    assert receipt.device_id=="tv-fenced"
    assert fence_store.calls==1
    assert delegate.calls==0
    assert transport.device is delegate.device


@pytest.mark.asyncio
async def test_missing_controller_fence_never_reaches_wrapped_transport():
    delegate=CountingTransport()
    fence_store=RejectingFenceStore()
    transport=FencedPhysicalTransport(delegate,fence_store)
    intent=SimpleNamespace(intent_id="intent-unbound",device_id="tv-fenced",controller_resource_id="",controller_id="",controller_fencing_token=0,transaction_id="tx-unbound",capability_digest="cap-unbound")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-unbound",capability_digest="cap-unbound")
    assert receipt.status is ActuationStatus.REJECTED
    assert fence_store.calls==0
    assert delegate.calls==0


@pytest.mark.asyncio
async def test_current_controller_fence_reaches_wrapped_transport_once():
    class AcceptingFenceStore:
        def __init__(self):
            self.calls=[]
        def accept(self,resource_id,controller_id,token):
            self.calls.append((resource_id,controller_id,token))
            return True
    delegate=CountingTransport()
    fence_store=AcceptingFenceStore()
    transport=FencedPhysicalTransport(delegate,fence_store)
    intent=SimpleNamespace(intent_id="intent-current",device_id="tv-fenced",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=9,transaction_id="tx-current",capability_digest="cap-current")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-current",capability_digest="cap-current")
    assert receipt.status is ActuationStatus.EXECUTED
    assert receipt.transaction_id=="tx-current"
    assert receipt.capability_digest=="cap-current"
    assert fence_store.calls==[("tv:living-room","phone-b",9)]
    assert delegate.calls==1


@pytest.mark.asyncio
async def test_device_mismatch_never_reaches_fence_store_or_transport():
    class AcceptingFenceStore:
        def __init__(self):
            self.calls=0
        def accept(self,resource_id,controller_id,token):
            self.calls+=1
            return True
    delegate=CountingTransport()
    fence_store=AcceptingFenceStore()
    transport=FencedPhysicalTransport(delegate,fence_store)
    intent=SimpleNamespace(intent_id="intent-wrong-device",device_id="tv-other",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=9,transaction_id="tx-wrong-device",capability_digest="cap-wrong-device")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-wrong-device",capability_digest="cap-wrong-device")
    assert receipt.status is ActuationStatus.REJECTED
    assert receipt.device_id=="tv-fenced"
    assert fence_store.calls==0
    assert delegate.calls==0


@pytest.mark.asyncio
async def test_fence_store_outage_never_reaches_wrapped_transport():
    class UnavailableFenceStore:
        def __init__(self):
            self.calls=0
        def accept(self,resource_id,controller_id,token):
            self.calls+=1
            raise OSError("simulated fence store outage")
    delegate=CountingTransport()
    fence_store=UnavailableFenceStore()
    transport=FencedPhysicalTransport(delegate,fence_store)
    intent=SimpleNamespace(intent_id="intent-outage",device_id="tv-fenced",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=9,transaction_id="tx-outage",capability_digest="cap-outage")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-outage",capability_digest="cap-outage")
    assert receipt.status is ActuationStatus.REJECTED
    assert receipt.device_id=="tv-fenced"
    assert fence_store.calls==1
    assert delegate.calls==0


@pytest.mark.asyncio
@pytest.mark.parametrize(("resource_id","controller_id","token"),[("","phone-b",9),("tv:living-room","",9),("tv:living-room","phone-b",0),("tv:living-room","phone-b",-1),("tv:living-room","phone-b",True),("tv:living-room","phone-b","9"),(None,"phone-b",9),("tv:living-room",None,9)])
async def test_malformed_controller_fence_never_reaches_store_or_transport(resource_id,controller_id,token):
    class RecordingFenceStore:
        def __init__(self):
            self.calls=0
        def accept(self,*args):
            self.calls+=1
            return True
    delegate=CountingTransport()
    fence_store=RecordingFenceStore()
    transport=FencedPhysicalTransport(delegate,fence_store)
    intent=SimpleNamespace(intent_id="intent-malformed",device_id="tv-fenced",controller_resource_id=resource_id,controller_id=controller_id,controller_fencing_token=token,transaction_id="tx-malformed",capability_digest="cap-malformed")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-malformed",capability_digest="cap-malformed")
    assert receipt.status is ActuationStatus.REJECTED
    assert fence_store.calls==0
    assert delegate.calls==0


def test_fenced_protected_bridge_factory_wraps_transport_boundary():
    from src.control.device_fabric_bridge import build_fenced_protected_device_fabric_bridge
    from src.control.protection_supervisor import ProtectionSupervisor
    delegate=CountingTransport()
    fence_store=RejectingFenceStore()
    supervisor=ProtectionSupervisor(max_evidence_age=5.0)
    bridge=build_fenced_protected_device_fabric_bridge(object(),delegate,supervisor,fence_store=fence_store)
    assert isinstance(bridge.adapter,FencedPhysicalTransport)
    assert bridge.adapter.device is delegate.device
    assert bridge.adapter._transport is delegate
    assert bridge.adapter._fence_store is fence_store
    assert bridge.protection_supervisor is supervisor
    assert delegate.calls==0


def test_fenced_physical_transport_is_public_device_fabric_contract():
    import src.device_fabric as device_fabric
    assert device_fabric.FencedPhysicalTransport is FencedPhysicalTransport
    assert "FencedPhysicalTransport" in device_fabric.__all__


def test_production_fenced_bridge_requires_qualified_store(tmp_path):
    from src.control.device_fabric_bridge import build_production_fenced_protected_device_fabric_bridge
    from src.control.protection_supervisor import ProtectionSupervisor
    from src.device_fabric import ExternalAtomicMonotonicFenceAnchor,MonotonicAnchorSecurityLevel,build_production_controller_fence_store
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    class RemoteBackend:
        provider_id="remote-controller-authority"
        def snapshot(self):
            return {}
        def advance(self,resource_id,controller_id,fencing_token):
            raise AssertionError("construction must not advance authority")
    anchor=ExternalAtomicMonotonicFenceAnchor(RemoteBackend(),security_level=MonotonicAnchorSecurityLevel.REMOTE_ATOMIC)
    fence_store=build_production_controller_fence_store(tmp_path/"controller-fences.json",monotonic_anchor=anchor)
    from cryptography.hazmat.primitives.asymmetric import ec
    from src.device_fabric.endpoint_transaction_finality_authority import EndpointFinalityTrustedKey,EndpointFinalityAuthoritySnapshot
    delegate=CountingTransport()
    supervisor=ProtectionSupervisor(max_evidence_age=5.0)
    legacy_store=EndpointTransactionFinalityStore(tmp_path/"legacy-finality.sqlite3")
    with pytest.raises(ValueError,match="trusted authority"):
        build_production_fenced_protected_device_fabric_bridge(object(),delegate,supervisor,fence_store=fence_store,transaction_finality_store=legacy_store)
    key=ec.derive_private_key(1,ec.SECP256R1()).public_key()
    trusted=EndpointFinalityTrustedKey(kid=b"k",namespace=b"n",issuer_id="i",audience="a",device_id=delegate.device.identity.device_id,authority_epoch=1,public_key=key)
    authority=EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=(trusted,))
    finality_store=EndpointTransactionFinalityStore(tmp_path/"endpoint-finality.sqlite3",trusted_authority=authority)
    with pytest.raises(ValueError,match="existing history"):
        build_production_fenced_protected_device_fabric_bridge(object(),delegate,supervisor,fence_store=fence_store,transaction_finality_store=finality_store)
    finality_store=EndpointTransactionFinalityStore(tmp_path/"endpoint-finality.sqlite3",trusted_authority=authority,require_existing=True)
    with pytest.raises(ValueError,match="profile v2"):
        build_production_fenced_protected_device_fabric_bridge(object(),delegate,supervisor,fence_store=fence_store,transaction_finality_store=finality_store)
    v2_path=tmp_path/"production-v2-finality.sqlite3"
    EndpointTransactionFinalityStore(v2_path,trusted_authority=authority,minimum_profile_version=2)
    finality_store=EndpointTransactionFinalityStore(v2_path,trusted_authority=authority,require_existing=True,minimum_profile_version=2)
    with pytest.raises(ValueError,match="endpoint execution boundary is required"):
        build_production_fenced_protected_device_fabric_bridge(object(),delegate,supervisor,fence_store=fence_store,transaction_finality_store=finality_store)
    assert delegate.calls==0


def test_production_fenced_bridge_rejects_test_only_store(tmp_path):
    from src.control.device_fabric_bridge import build_production_fenced_protected_device_fabric_bridge
    from src.control.protection_supervisor import ProtectionSupervisor
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor
    delegate=CountingTransport()
    fence_store=ControllerFenceStore(tmp_path/"controller-fences.json",monotonic_anchor=InMemoryMonotonicFenceAnchor())
    supervisor=ProtectionSupervisor(max_evidence_age=5.0)
    with pytest.raises(ValueError,match="production monotonic anchor"):
        build_production_fenced_protected_device_fabric_bridge(object(),delegate,supervisor,fence_store=fence_store)
    assert delegate.calls==0
    assert not (tmp_path/"controller-fences.json").exists()


@pytest.mark.asyncio
async def test_durable_not_applied_tombstone_rejects_late_delivery_after_restart(tmp_path):
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    class AcceptingFenceStore:
        def __init__(self):
            self.calls=0
        def accept(self,resource_id,controller_id,token):
            self.calls+=1
            return True
    path=tmp_path/"endpoint-finality.sqlite3"
    EndpointTransactionFinalityStore(path).record_not_applied("tx-late",device_id="tv-fenced")
    finality_store=EndpointTransactionFinalityStore(path)
    assert finality_store.permits_execution("tx-late",device_id="tv-fenced") is False
    delegate=CountingTransport()
    fence_store=AcceptingFenceStore()
    transport=FencedPhysicalTransport(delegate,fence_store,transaction_finality_store=finality_store)
    intent=SimpleNamespace(intent_id="intent-late",device_id="tv-fenced",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=9,transaction_id="tx-late",capability_digest="cap-late")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-late",capability_digest="cap-late")
    assert receipt.status is ActuationStatus.REJECTED
    assert fence_store.calls==0
    assert delegate.calls==0


def test_endpoint_transaction_finality_store_is_public_device_fabric_contract():
    import src.device_fabric as device_fabric
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    assert device_fabric.EndpointTransactionFinalityStore is EndpointTransactionFinalityStore
    assert "EndpointTransactionFinalityStore" in device_fabric.__all__


def test_production_fenced_bridge_requires_endpoint_transaction_finality_store(tmp_path):
    from src.control.device_fabric_bridge import build_production_fenced_protected_device_fabric_bridge
    from src.control.protection_supervisor import ProtectionSupervisor
    from src.device_fabric import ExternalAtomicMonotonicFenceAnchor,MonotonicAnchorSecurityLevel,build_production_controller_fence_store
    class RemoteBackend:
        provider_id="remote-controller-authority"
        def snapshot(self):
            return {}
        def advance(self,resource_id,controller_id,fencing_token):
            raise AssertionError("construction must not advance authority")
    anchor=ExternalAtomicMonotonicFenceAnchor(RemoteBackend(),security_level=MonotonicAnchorSecurityLevel.REMOTE_ATOMIC)
    fence_store=build_production_controller_fence_store(tmp_path/"controller-fences.json",monotonic_anchor=anchor)
    delegate=CountingTransport()
    supervisor=ProtectionSupervisor(max_evidence_age=5.0)
    with pytest.raises(ValueError,match="endpoint transaction finality store is required"):
        build_production_fenced_protected_device_fabric_bridge(object(),delegate,supervisor,fence_store=fence_store)
    assert delegate.calls==0


@pytest.mark.asyncio
async def test_endpoint_finality_store_outage_never_reaches_fence_store_or_transport():
    class UnavailableFinalityStore:
        def __init__(self):
            self.calls=0
        def permits_execution(self,transaction_id,*,device_id):
            self.calls+=1
            raise OSError("simulated endpoint finality store outage")
    class AcceptingFenceStore:
        def __init__(self):
            self.calls=0
        def accept(self,resource_id,controller_id,token):
            self.calls+=1
            return True
    delegate=CountingTransport()
    fence_store=AcceptingFenceStore()
    finality_store=UnavailableFinalityStore()
    transport=FencedPhysicalTransport(delegate,fence_store,transaction_finality_store=finality_store)
    intent=SimpleNamespace(intent_id="intent-finality-outage",device_id="tv-fenced",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=9,transaction_id="tx-finality-outage",capability_digest="cap-finality-outage")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-finality-outage",capability_digest="cap-finality-outage")
    assert receipt.status is ActuationStatus.REJECTED
    assert finality_store.calls==1
    assert fence_store.calls==0
    assert delegate.calls==0


@pytest.mark.asyncio
async def test_finality_recorded_during_fence_check_blocks_dispatch(tmp_path):
    from types import SimpleNamespace
    from src.device_fabric.contracts import ActuationStatus
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    from src.device_fabric.fenced_transport import FencedPhysicalTransport
    class ObservedTransport(CountingTransport):
        async def execute_intent(self,intent,transaction_digest=None,capability_digest=None):
            self.calls+=1
            return None
    delegate=ObservedTransport()
    device_id=delegate.device.identity.device_id
    path=tmp_path/"finality-race.sqlite3"
    finality_store=EndpointTransactionFinalityStore(path)
    writer=EndpointTransactionFinalityStore(path)
    class RecordingFenceStore:
        def __init__(self):
            self.calls=0
        def accept(self,resource_id,controller_id,token):
            self.calls+=1
            writer.record_not_applied("tx-race",device_id=device_id)
            return True
    fence_store=RecordingFenceStore()
    transport=FencedPhysicalTransport(delegate,fence_store,transaction_finality_store=finality_store)
    intent=SimpleNamespace(intent_id="intent-race",device_id=device_id,controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=9,transaction_id="tx-race",capability_digest="cap-race")
    receipt=await transport.execute_intent(intent,transaction_digest="tx-race",capability_digest="cap-race")
    assert fence_store.calls==1
    assert writer.permits_execution("tx-race",device_id=device_id) is False
    assert delegate.calls==0
    assert receipt.status is ActuationStatus.REJECTED


def test_production_bridge_requires_atomic_finality_claim(monkeypatch):
    from types import SimpleNamespace
    import pytest
    import src.control.device_fabric_bridge as bridge_module
    from src.control.protection_supervisor import ProtectionSupervisor
    monkeypatch.setattr(bridge_module,"require_production_monotonic_anchor",lambda anchor: None)
    fence_store=SimpleNamespace(monotonic_anchor=object(),accept=lambda *args: True)
    legacy_store=SimpleNamespace(permits_execution=lambda *args,**kwargs: True)
    with pytest.raises(ValueError,match="atomic execution claim"):
        bridge_module.build_production_fenced_protected_device_fabric_bridge(object(),CountingTransport(),ProtectionSupervisor(max_evidence_age=5.0),fence_store=fence_store,transaction_finality_store=legacy_store)


@pytest.mark.asyncio
async def test_queued_old_controller_rejected_after_durable_handoff(tmp_path):
    import asyncio
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    delegate=CountingTransport()
    store=ControllerFenceStore(tmp_path/"handoff-fence.json")
    resource="tv:living-room"
    assert store.accept(resource,"phone-a",8) is True
    transport=FencedPhysicalTransport(delegate,store)
    old=SimpleNamespace(intent_id="old-command",device_id="tv-fenced",controller_resource_id=resource,controller_id="phone-a",controller_fencing_token=8,transaction_id="tx-old",capability_digest="cap-old")
    started,resume=asyncio.Event(),asyncio.Event()
    async def queued_old_command():
        started.set()
        await resume.wait()
        return await transport.execute_intent(old,transaction_digest=old.transaction_id,capability_digest=old.capability_digest)
    pending=asyncio.create_task(queued_old_command())
    await asyncio.wait_for(started.wait(),5)
    assert store.accept(resource,"phone-b",9) is True
    assert store.snapshot()[resource]==(9,"phone-b")
    resume.set()
    rejected=await pending
    assert rejected.status is ActuationStatus.REJECTED
    assert rejected.transaction_id==old.transaction_id
    assert delegate.calls==0
    current=SimpleNamespace(intent_id="new-command",device_id="tv-fenced",controller_resource_id=resource,controller_id="phone-b",controller_fencing_token=9,transaction_id="tx-new",capability_digest="cap-new")
    executed=await transport.execute_intent(current,transaction_digest=current.transaction_id,capability_digest=current.capability_digest)
    assert executed.status is ActuationStatus.EXECUTED
    assert executed.transaction_id==current.transaction_id
    assert delegate.calls==1


@pytest.mark.asyncio
async def test_handoff_during_finality_claim_blocks_old_controller_dispatch(tmp_path):
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    resource="tv:living-room"
    fence_path=tmp_path/"handoff-during-claim.json"
    finality_path=tmp_path/"handoff-during-claim.sqlite3"
    fence=ControllerFenceStore(fence_path)
    successor=ControllerFenceStore(fence_path)
    finality=EndpointTransactionFinalityStore(finality_path)
    assert fence.accept(resource,"phone-a",8) is True
    class HandoffDuringClaim:
        def __init__(self):
            self.handoffs=0
        def permits_execution(self,transaction_id,*,device_id):
            return finality.permits_execution(transaction_id,device_id=device_id)
        def claim_execution(self,transaction_id,*,device_id):
            claimed=finality.claim_execution(transaction_id,device_id=device_id)
            if claimed and transaction_id=="tx-old-during-claim":
                assert successor.accept(resource,"phone-b",9) is True
                self.handoffs+=1
            return claimed
    hook=HandoffDuringClaim()
    delegate=CountingTransport()
    transport=FencedPhysicalTransport(delegate,fence,transaction_finality_store=hook)
    old=SimpleNamespace(intent_id="old-during-claim",device_id="tv-fenced",controller_resource_id=resource,controller_id="phone-a",controller_fencing_token=8,transaction_id="tx-old-during-claim",capability_digest="cap-old-during-claim")
    rejected=await transport.execute_intent(old,transaction_digest=old.transaction_id,capability_digest=old.capability_digest)
    assert hook.handoffs==1
    assert fence.snapshot()[resource]==(9,"phone-b")
    reopened=EndpointTransactionFinalityStore(finality_path,require_existing=True)
    assert reopened.permits_execution(old.transaction_id,device_id=old.device_id) is False
    assert delegate.calls==0
    assert rejected.status is ActuationStatus.REJECTED
    assert rejected.transaction_id==old.transaction_id
    assert rejected.capability_digest==old.capability_digest
    current=SimpleNamespace(intent_id="new-after-claim",device_id="tv-fenced",controller_resource_id=resource,controller_id="phone-b",controller_fencing_token=9,transaction_id="tx-new-after-claim",capability_digest="cap-new-after-claim")
    executed=await transport.execute_intent(current,transaction_digest=current.transaction_id,capability_digest=current.capability_digest)
    assert executed.status is ActuationStatus.EXECUTED
    assert executed.transaction_id==current.transaction_id
    assert executed.capability_digest==current.capability_digest
    assert delegate.calls==1


@pytest.mark.asyncio
@pytest.mark.parametrize("restore",[False,True])
async def test_protection_change_inside_finality_claim_blocks_dispatch(tmp_path,restore):
    import time
    from src.control.device_fabric_bridge import _ProtectionAdmissionInvalidated,_ProtectionBoundTransport
    from src.control.protection_supervisor import ProtectionState,ProtectionSupervisor,ProtectionUnavailableError
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    resource="tv:living-room"
    fence=ControllerFenceStore(tmp_path/"protection-claim-fence.json")
    assert fence.accept(resource,"phone-a",8) is True
    finality_path=tmp_path/"protection-claim.sqlite3"
    finality=EndpointTransactionFinalityStore(finality_path)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    wall,mono=time.time()-0.1,time.monotonic()-0.1
    assert supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall,now=wall,observed_monotonic=mono,monotonic_now=mono) is ProtectionState.ACTIVE
    generation=supervisor.require_automation(now=time.time(),monotonic_now=time.monotonic()).admission_generation
    class InterruptDuringClaim:
        def permits_execution(self,transaction_id,*,device_id):
            return finality.permits_execution(transaction_id,device_id=device_id)
        def claim_execution(self,transaction_id,*,device_id):
            claimed=finality.claim_execution(transaction_id,device_id=device_id)
            if claimed:
                supervisor.interrupt("AUDIO_SESSION_INTERRUPTED",now=wall+0.01,monotonic_now=mono+0.01)
                if restore:
                    assert supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall+0.02,now=wall+0.02,observed_monotonic=mono+0.02,monotonic_now=mono+0.02) is ProtectionState.ACTIVE
            return claimed
    delegate=CountingTransport()
    fenced=FencedPhysicalTransport(delegate,fence,transaction_finality_store=InterruptDuringClaim())
    transport=_ProtectionBoundTransport(fenced,supervisor,generation)
    intent=SimpleNamespace(intent_id="interrupted-claim",device_id="tv-fenced",controller_resource_id=resource,controller_id="phone-a",controller_fencing_token=8,transaction_id="tx-interrupted-claim",capability_digest="cap-interrupted-claim")
    expected=_ProtectionAdmissionInvalidated if restore else ProtectionUnavailableError
    with pytest.raises(expected):
        await transport.execute_intent(intent,transaction_digest=intent.transaction_id,capability_digest=intent.capability_digest)
    assert delegate.calls==0
    assert fence.snapshot()[resource]==(8,"phone-a")
    reopened=EndpointTransactionFinalityStore(finality_path,require_existing=True)
    assert reopened.permits_execution(intent.transaction_id,device_id=intent.device_id) is False


@pytest.mark.asyncio
async def test_protected_fenced_claim_reaches_delegate_for_current_admission(tmp_path):
    import time
    from src.control.device_fabric_bridge import _ProtectionBoundTransport
    from src.control.protection_supervisor import ProtectionState,ProtectionSupervisor
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    resource="tv:living-room"
    fence=ControllerFenceStore(tmp_path/"current-admission-fence.json")
    assert fence.accept(resource,"phone-a",8) is True
    finality_path=tmp_path/"current-admission.sqlite3"
    finality=EndpointTransactionFinalityStore(finality_path)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    wall,mono=time.time(),time.monotonic()
    assert supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=wall,now=wall,observed_monotonic=mono,monotonic_now=mono) is ProtectionState.ACTIVE
    generation=supervisor.require_automation(now=time.time(),monotonic_now=time.monotonic()).admission_generation
    delegate=CountingTransport()
    transport=_ProtectionBoundTransport(FencedPhysicalTransport(delegate,fence,transaction_finality_store=finality),supervisor,generation)
    intent=SimpleNamespace(intent_id="current-admission",device_id="tv-fenced",controller_resource_id=resource,controller_id="phone-a",controller_fencing_token=8,transaction_id="tx-current-admission",capability_digest="cap-current-admission")
    receipt=await transport.execute_intent(intent,transaction_digest=intent.transaction_id,capability_digest=intent.capability_digest)
    assert receipt.status is ActuationStatus.EXECUTED
    assert receipt.transaction_id==intent.transaction_id
    assert delegate.calls==1
    assert fence.snapshot()[resource]==(8,"phone-a")
    reopened=EndpointTransactionFinalityStore(finality_path,require_existing=True)
    assert reopened.permits_execution(intent.transaction_id,device_id=intent.device_id) is False
