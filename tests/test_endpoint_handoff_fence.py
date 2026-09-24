import pytest
from dataclasses import replace

from src.control.remote_controller_protocol import P256AuthorityKeyPair
from src.device_fabric.controller_fence_store import ControllerFenceStore
from src.device_fabric.endpoint_handoff_fence import SignedEndpointFenceDirective,VerifiedEndpointFenceInstaller


def test_signed_directive_advances_persisted_fence_only_if_valid(tmp_path):
    path=tmp_path/"endpoint-handoff-fence.json"
    store=ControllerFenceStore(path)
    assert store.accept("tv:living-room","phone-a",8) is True
    key=P256AuthorityKeyPair.generate("trusted-handoff-authority")
    unsigned=SignedEndpointFenceDirective(request_id="handoff-a-to-b",device_id="tv-fenced",resource_id="tv:living-room",previous_controller_id="phone-a",previous_fencing_token=8,controller_id="phone-b",fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id)
    directive=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    installer=VerifiedEndpointFenceInstaller(device_id="tv-fenced",fence_store=store,trusted_verifiers={key.key_id:key.public_verifier})
    assert installer.install(replace(directive,controller_id="phone-c"),now=101.0) is False
    assert installer.install(replace(directive,device_id="another-device"),now=101.0) is False
    assert store.snapshot()["tv:living-room"]==(8,"phone-a")
    assert installer.install(directive,now=101.0) is True
    assert ControllerFenceStore(path).snapshot()["tv:living-room"]==(9,"phone-b")
    assert installer.install(directive,now=101.0) is False


def test_remote_handoff_issues_only_persisted_fence_directive(tmp_path):
    from src.control.remote_atomic_controller_authority import IdempotentRemoteControllerAuthority
    key=P256AuthorityKeyPair.generate("handoff-directive-issuer")
    authority_path=tmp_path/"handoff-authority.json"
    authority=IdempotentRemoteControllerAuthority(state_path=authority_path,signing_key=key,endpoint_device_bindings={"tv:living-room":"tv-fenced"})
    first=authority.acquire(request_id="directive-acquire",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    successor=authority.handoff(request_id="directive-handoff",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    directive=authority.issue_fence_directive(request_id="directive-handoff",device_id="tv-fenced",now=102.0)
    assert directive.previous_controller_id==first.controller_id
    assert directive.previous_fencing_token==first.fencing_token
    assert directive.controller_id==successor.controller_id
    assert directive.fencing_token==successor.fencing_token
    assert directive.signature
    restarted=IdempotentRemoteControllerAuthority(state_path=authority_path,signing_key=key,endpoint_device_bindings={"tv:living-room":"tv-fenced"})
    assert restarted.issue_fence_directive(request_id="directive-handoff",device_id="tv-fenced",now=103.0)==directive
    store=ControllerFenceStore(tmp_path/"issued-directive-fence.json")
    assert store.accept(first.resource_id,first.controller_id,first.fencing_token) is True
    installer=VerifiedEndpointFenceInstaller(device_id="tv-fenced",fence_store=store,trusted_verifiers={key.key_id:key.public_verifier})
    assert installer.install(directive,now=103.0) is True
    assert store.snapshot()[first.resource_id]==(successor.fencing_token,successor.controller_id)
    import pytest
    with pytest.raises(RuntimeError,match="endpoint readiness"):
        authority.issue_grant(request_id="directive-handoff",controller_key_id="phone-b-key",now=103.0)
    with pytest.raises(RuntimeError,match="endpoint readiness"):
        restarted.issue_grant(request_id="directive-handoff",controller_key_id="phone-b-key",now=103.0)


def _failure_case_authority(tmp_path):
    from src.control.remote_atomic_controller_authority import IdempotentRemoteControllerAuthority
    key=P256AuthorityKeyPair.generate("failure-case-issuer")
    path=tmp_path/"handoff-authority.json"
    authority=IdempotentRemoteControllerAuthority(state_path=path,signing_key=key,endpoint_device_bindings={"tv:living-room":"tv-fenced"})
    first=authority.acquire(request_id="acquire",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    authority.handoff(request_id="handoff",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    return authority,key,path


def test_corrupted_persisted_directive_fails_closed(tmp_path):
    import json
    import pytest
    authority,key,path=_failure_case_authority(tmp_path)
    authority.issue_fence_directive(request_id="handoff",device_id="tv-fenced",now=102.0)
    raw=json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"]==4
    raw["handoff_directives"]["handoff"]["signature"]="invalid"
    path.write_text(json.dumps(raw),encoding="utf-8")
    corrupted=path.read_bytes()
    with pytest.raises(ValueError,match="invalid persisted handoff directive"):
        authority.__class__(state_path=path,signing_key=key,endpoint_device_bindings={"tv:living-room":"tv-fenced"})
    assert path.read_bytes()==corrupted


def test_directive_prewrite_failure_leaves_no_issued_record(tmp_path,monkeypatch):
    import json
    import pytest
    authority,key,path=_failure_case_authority(tmp_path)
    original=authority._save_state
    def fail_before_write(_committed):
        raise OSError("injected before write")
    monkeypatch.setattr(authority,"_save_state",fail_before_write)
    with pytest.raises(OSError,match="injected before write"):
        authority.issue_fence_directive(request_id="handoff",device_id="tv-fenced",now=102.0)
    assert authority._handoff_directives=={}
    assert json.loads(path.read_text(encoding="utf-8"))["version"]==2
    monkeypatch.setattr(authority,"_save_state",original)
    directive=authority.issue_fence_directive(request_id="handoff",device_id="tv-fenced",now=103.0)
    assert directive.signature
    restarted=authority.__class__(state_path=path,signing_key=key,endpoint_device_bindings={"tv:living-room":"tv-fenced"})
    assert restarted.issue_fence_directive(request_id="handoff",device_id="tv-fenced",now=103.0)==directive


def test_directive_postwrite_failure_recovers_exact_signed_record(tmp_path,monkeypatch):
    import json
    import pytest
    authority,key,path=_failure_case_authority(tmp_path)
    original=authority._save_state
    def write_then_fail(committed):
        original(committed)
        raise OSError("injected after write")
    monkeypatch.setattr(authority,"_save_state",write_then_fail)
    with pytest.raises(OSError,match="injected after write"):
        authority.issue_fence_directive(request_id="handoff",device_id="tv-fenced",now=102.0)
    assert authority._handoff_directives=={}
    persisted=SignedEndpointFenceDirective(**json.loads(path.read_text(encoding="utf-8"))["handoff_directives"]["handoff"])
    restarted=authority.__class__(state_path=path,signing_key=key,endpoint_device_bindings={"tv:living-room":"tv-fenced"})
    assert restarted.issue_fence_directive(request_id="handoff",device_id="tv-fenced",now=103.0)==persisted
    monkeypatch.setattr(authority,"_save_state",original)
    assert authority.issue_fence_directive(request_id="handoff",device_id="tv-fenced",now=103.0)==persisted


@pytest.mark.asyncio
async def test_installed_fence_keeps_grant_blocked_while_old_work_can_still_apply(tmp_path):
    import asyncio
    from types import SimpleNamespace
    from src.control.remote_atomic_controller_authority import IdempotentRemoteControllerAuthority
    from src.device_fabric.contracts import ActuationReceipt,ActuationStatus
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    from src.device_fabric.fenced_transport import FencedPhysicalTransport
    resource,device_id="tv:living-room","tv-fenced"
    key=P256AuthorityKeyPair.generate("queued-handoff-issuer")
    authority_path=tmp_path/"queued-authority.json"
    authority=IdempotentRemoteControllerAuthority(state_path=authority_path,signing_key=key,endpoint_device_bindings={resource:device_id})
    first=authority.acquire(request_id="queued-acquire",resource_id=resource,controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    fence_path=tmp_path/"queued-fence.json"
    fence=ControllerFenceStore(fence_path)
    assert fence.accept(resource,first.controller_id,first.fencing_token) is True
    finality_path=tmp_path/"queued-finality.sqlite3"
    finality=EndpointTransactionFinalityStore(finality_path)
    queued,release=asyncio.Event(),asyncio.Event()
    effects=[]
    class QueuedTransport:
        def __init__(self):
            self.device=SimpleNamespace(identity=SimpleNamespace(device_id=device_id))
            self.calls=0
        async def execute_intent(self,intent,transaction_digest=None,capability_digest=None):
            self.calls+=1
            queued.set()
            await release.wait()
            effects.append((intent.transaction_id,intent.controller_id,intent.controller_fencing_token))
            return ActuationReceipt(receipt_id="queued-effect",intent_id=intent.intent_id,status=ActuationStatus.EXECUTED,device_id=intent.device_id,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    delegate=QueuedTransport()
    transport=FencedPhysicalTransport(delegate,fence,transaction_finality_store=finality)
    old=SimpleNamespace(intent_id="queued-old",device_id=device_id,controller_resource_id=resource,controller_id=first.controller_id,controller_fencing_token=first.fencing_token,transaction_id="tx-queued-old",capability_digest="cap-queued-old")
    task=asyncio.create_task(transport.execute_intent(old))
    try:
        await asyncio.wait_for(queued.wait(),5.0)
        assert delegate.calls==1 and effects==[]
        assert finality.permits_execution(old.transaction_id,device_id=device_id) is False
        successor=authority.handoff(request_id="queued-handoff",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
        directive=authority.issue_fence_directive(request_id="queued-handoff",device_id=device_id,now=102.0)
        installer=VerifiedEndpointFenceInstaller(device_id=device_id,fence_store=fence,trusted_verifiers={key.key_id:key.public_verifier})
        assert installer.install(directive,now=103.0) is True
        assert ControllerFenceStore(fence_path).snapshot()[resource]==(successor.fencing_token,successor.controller_id)
        restarted=IdempotentRemoteControllerAuthority(state_path=authority_path,signing_key=key,endpoint_device_bindings={resource:device_id})
        for candidate in (authority,restarted):
            with pytest.raises(RuntimeError,match="endpoint readiness"):
                candidate.issue_grant(request_id="queued-handoff",controller_key_id="phone-b-key",now=103.0)
        late=SimpleNamespace(**{**vars(old),"intent_id":"late-old","transaction_id":"tx-late-old"})
        rejected=await asyncio.wait_for(transport.execute_intent(late),5.0)
        assert rejected.status is ActuationStatus.REJECTED
        assert delegate.calls==1 and effects==[]
        release.set()
        receipt=await asyncio.wait_for(task,5.0)
        assert receipt.status is ActuationStatus.EXECUTED
        assert receipt.transaction_id==old.transaction_id
        assert effects==[(old.transaction_id,first.controller_id,first.fencing_token)]
        assert delegate.calls==1
        reopened=EndpointTransactionFinalityStore(finality_path,require_existing=True)
        assert reopened.permits_execution(old.transaction_id,device_id=device_id) is False
        with pytest.raises(ValueError,match="already claimed"):
            reopened.record_not_applied(old.transaction_id,device_id=device_id)
        with pytest.raises(RuntimeError,match="endpoint readiness"):
            authority.issue_grant(request_id="queued-handoff",controller_key_id="phone-b-key",now=104.0)
    finally:
        release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task,return_exceptions=True)


def test_durable_handoff_barrier_retains_pending_old_admission_after_restart(tmp_path):
    from src.device_fabric.endpoint_handoff_barrier import EndpointHandoffBarrier
    resource,device_id="tv:living-room","tv-fenced"
    fence_path=tmp_path/"barrier-fence.json"
    store=ControllerFenceStore(fence_path)
    assert store.accept(resource,"phone-a",8) is True
    barrier_path=tmp_path/"handoff-barrier.sqlite3"
    key=P256AuthorityKeyPair.generate("barrier-directive-issuer")
    barrier=EndpointHandoffBarrier(barrier_path,device_id=device_id,fence_store=store,trusted_verifiers={key.key_id:key.public_verifier},enroll=True)
    assert barrier.admit(transaction_id="tx-old",resource_id=resource,controller_id="phone-a",fencing_token=8) is True
    unsigned=SignedEndpointFenceDirective(request_id="handoff-a-to-b",device_id=device_id,resource_id=resource,previous_controller_id="phone-a",previous_fencing_token=8,controller_id="phone-b",fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id)
    directive=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    assert barrier.install(directive,now=101.0) is True
    assert store.snapshot()[resource]==(9,"phone-b")
    assert barrier.is_ready("handoff-a-to-b") is False
    reopened=EndpointHandoffBarrier(barrier_path,device_id=device_id,fence_store=ControllerFenceStore(fence_path),trusted_verifiers={key.key_id:key.public_verifier})
    assert reopened.is_ready("handoff-a-to-b") is False
    assert reopened.admit(transaction_id="tx-late",resource_id=resource,controller_id="phone-a",fencing_token=8) is False
    assert reopened.admit(transaction_id="tx-old",resource_id=resource,controller_id="phone-a",fencing_token=8) is False
    assert ControllerFenceStore(fence_path).snapshot()[resource]==(9,"phone-b")


@pytest.mark.asyncio
async def test_barrier_records_work_before_delegate_and_blocks_late_old_dispatch(tmp_path):
    import asyncio
    from types import SimpleNamespace
    from src.device_fabric.contracts import ActuationReceipt,ActuationStatus
    from src.device_fabric.endpoint_handoff_barrier import EndpointHandoffBarrier
    from src.device_fabric.fenced_transport import FencedPhysicalTransport
    resource,device_id="tv:living-room","tv-fenced"
    fence_path=tmp_path/"queued-barrier-fence.json"
    fence=ControllerFenceStore(fence_path)
    assert fence.accept(resource,"phone-a",8) is True
    barrier_path=tmp_path/"queued-barrier.sqlite3"
    key=P256AuthorityKeyPair.generate("queued-barrier-issuer")
    barrier=EndpointHandoffBarrier(barrier_path,device_id=device_id,fence_store=fence,trusted_verifiers={key.key_id:key.public_verifier},enroll=True)
    entered,release=asyncio.Event(),asyncio.Event()
    effects=[]
    class Delegate:
        def __init__(self):
            self.device=SimpleNamespace(identity=SimpleNamespace(device_id=device_id))
            self.calls=0
        async def execute_intent(self,intent,transaction_digest=None,capability_digest=None):
            self.calls+=1
            entered.set()
            await release.wait()
            effects.append(intent.transaction_id)
            return ActuationReceipt(receipt_id="queued",intent_id=intent.intent_id,status=ActuationStatus.EXECUTED,device_id=device_id,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)
    delegate=Delegate()
    transport=FencedPhysicalTransport(delegate,fence,handoff_barrier=barrier)
    old=SimpleNamespace(intent_id="old",device_id=device_id,controller_resource_id=resource,controller_id="phone-a",controller_fencing_token=8,transaction_id="tx-old",capability_digest="cap-old")
    task=asyncio.create_task(transport.execute_intent(old))
    try:
        await asyncio.wait_for(entered.wait(),5.0)
        restarted=EndpointHandoffBarrier(barrier_path,device_id=device_id,fence_store=ControllerFenceStore(fence_path),trusted_verifiers={key.key_id:key.public_verifier})
        assert restarted.admit(transaction_id=old.transaction_id,resource_id=resource,controller_id="phone-a",fencing_token=8) is False
        assert delegate.calls==1 and effects==[]
        unsigned=SignedEndpointFenceDirective(request_id="queued-handoff",device_id=device_id,resource_id=resource,previous_controller_id="phone-a",previous_fencing_token=8,controller_id="phone-b",fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id)
        directive=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
        assert restarted.install(directive,now=101.0) is True
        assert restarted.is_ready("queued-handoff") is False
        late=SimpleNamespace(**{**vars(old),"intent_id":"late","transaction_id":"tx-late"})
        receipt=await asyncio.wait_for(transport.execute_intent(late),5.0)
        assert receipt.status is ActuationStatus.REJECTED
        assert delegate.calls==1 and effects==[]
        release.set()
        receipt=await asyncio.wait_for(task,5.0)
        assert receipt.status is ActuationStatus.EXECUTED
        assert effects==["tx-old"]
        assert restarted.is_ready("queued-handoff") is False
    finally:
        release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task,return_exceptions=True)


@pytest.mark.asyncio
async def test_missing_barrier_history_rejects_before_delegate(tmp_path):
    from types import SimpleNamespace
    from src.device_fabric.contracts import ActuationStatus
    from src.device_fabric.endpoint_handoff_barrier import EndpointHandoffBarrier
    from src.device_fabric.fenced_transport import FencedPhysicalTransport
    resource,device_id="tv:living-room","tv-fenced"
    fence=ControllerFenceStore(tmp_path/"missing-barrier-fence.json")
    assert fence.accept(resource,"phone-a",8) is True
    path=tmp_path/"missing-barrier.sqlite3"
    key=P256AuthorityKeyPair.generate("missing-barrier-issuer")
    barrier=EndpointHandoffBarrier(path,device_id=device_id,fence_store=fence,trusted_verifiers={key.key_id:key.public_verifier},enroll=True)
    class Delegate:
        def __init__(self):
            self.device=SimpleNamespace(identity=SimpleNamespace(device_id=device_id))
            self.calls=0
        async def execute_intent(self,**kwargs):
            self.calls+=1
            raise AssertionError("missing barrier history reached delegate")
    delegate=Delegate()
    transport=FencedPhysicalTransport(delegate,fence,handoff_barrier=barrier)
    path.unlink()
    intent=SimpleNamespace(intent_id="missing-history",device_id=device_id,controller_resource_id=resource,controller_id="phone-a",controller_fencing_token=8,transaction_id="tx-missing-history",capability_digest="cap-missing-history")
    receipt=await transport.execute_intent(intent)
    assert receipt.status is ActuationStatus.REJECTED
    assert delegate.calls==0
    assert fence.snapshot()[resource]==(8,"phone-a")



def test_handoff_barrier_pins_signing_key_across_restart_and_rejects_forgery(tmp_path):
    from src.device_fabric.endpoint_handoff_barrier import EndpointHandoffBarrier
    resource,device_id="tv:living-room","tv-fenced"
    trusted=P256AuthorityKeyPair.generate("pinned-handoff-key")
    attacker=P256AuthorityKeyPair.generate(trusted.key_id)
    fence_path=tmp_path/"pinned-key-fence.json"
    fence=ControllerFenceStore(fence_path)
    assert fence.accept(resource,"phone-a",8) is True
    path=tmp_path/"pinned-key-barrier.sqlite3"
    barrier=EndpointHandoffBarrier(path,device_id=device_id,fence_store=fence,trusted_verifiers={trusted.key_id:trusted.public_verifier},enroll=True)
    unsigned=SignedEndpointFenceDirective(request_id="pinned-handoff",device_id=device_id,resource_id=resource,previous_controller_id="phone-a",previous_fencing_token=8,controller_id="phone-b",fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=trusted.key_id)
    forged=replace(unsigned,signature=attacker.sign(unsigned.canonical_bytes))
    assert barrier.install(forged,now=101.0) is False
    assert fence.snapshot()[resource]==(8,"phone-a")
    with pytest.raises(ValueError,match="identity mismatch"):
        EndpointHandoffBarrier(path,device_id=device_id,fence_store=ControllerFenceStore(fence_path),trusted_verifiers={attacker.key_id:attacker.public_verifier})
    restarted=EndpointHandoffBarrier(path,device_id=device_id,fence_store=ControllerFenceStore(fence_path),trusted_verifiers={trusted.key_id:trusted.public_verifier})
    valid=replace(unsigned,signature=trusted.sign(unsigned.canonical_bytes))
    assert restarted.install(valid,now=101.0) is True
    assert fence.snapshot()[resource]==(9,"phone-b")
    assert restarted.is_ready("pinned-handoff") is False


@pytest.mark.parametrize("lose_confirmation", [False, True])
def test_handoff_barrier_blocks_unqualified_successor_after_restart(tmp_path, monkeypatch, lose_confirmation):
    from dataclasses import replace
    from src.control.remote_controller_protocol import P256AuthorityKeyPair
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    from src.device_fabric.endpoint_handoff_barrier import EndpointHandoffBarrier
    from src.device_fabric.endpoint_handoff_fence import SignedEndpointFenceDirective
    resource, device_id = "tv:living-room", "tv-fenced"
    fence_path = tmp_path / "held-fence.json"
    barrier_path = tmp_path / "held-barrier.sqlite3"
    fence = ControllerFenceStore(fence_path)
    assert fence.accept(resource, "phone-a", 8) is True
    key = P256AuthorityKeyPair.generate("held-handoff-key")
    trust = {key.key_id: key.public_verifier}
    barrier = EndpointHandoffBarrier(barrier_path, device_id=device_id, fence_store=fence, trusted_verifiers=trust, enroll=True)
    unsigned = SignedEndpointFenceDirective(request_id="held-handoff", device_id=device_id, resource_id=resource, previous_controller_id="phone-a", previous_fencing_token=8, controller_id="phone-b", fencing_token=9, issued_at=100.0, expires_at=130.0, issuer_id=key.key_id)
    directive = replace(unsigned, signature=key.sign(unsigned.canonical_bytes))
    original_snapshot = fence.snapshot
    observed_loss = False
    def confirmation_snapshot():
        nonlocal observed_loss
        snapshot = original_snapshot()
        if lose_confirmation and snapshot.get(resource) == (9, "phone-b"):
            observed_loss = True
            raise OSError("simulated lost fence confirmation")
        return snapshot
    monkeypatch.setattr(fence, "snapshot", confirmation_snapshot)
    result = barrier.install(directive, now=101.0)
    monkeypatch.setattr(fence, "snapshot", original_snapshot)
    assert observed_loss is lose_confirmation
    assert result is (not lose_confirmation)
    reopened_fence = ControllerFenceStore(fence_path)
    assert reopened_fence.snapshot()[resource] == (9, "phone-b")
    reopened = EndpointHandoffBarrier(barrier_path, device_id=device_id, fence_store=reopened_fence, trusted_verifiers=trust)
    assert reopened.is_ready("held-handoff") is False
    assert reopened.admit(transaction_id="tx-unqualified-successor", resource_id=resource, controller_id="phone-b", fencing_token=9) is False
    assert reopened_fence.accept("speaker:study", "phone-c", 3) is True
    assert reopened.admit(transaction_id="tx-independent-held-resource", resource_id="speaker:study", controller_id="phone-c", fencing_token=3) is True


@pytest.mark.parametrize("lose_confirmation", [False, True])
def test_held_handoff_rejects_successor_before_delegate_after_restart(tmp_path, monkeypatch, lose_confirmation):
    import asyncio
    async def scenario():
        from dataclasses import replace
        from types import SimpleNamespace
        from src.control.remote_controller_protocol import P256AuthorityKeyPair
        from src.device_fabric.contracts import ActuationReceipt, ActuationStatus
        from src.device_fabric.controller_fence_store import ControllerFenceStore
        from src.device_fabric.endpoint_handoff_barrier import EndpointHandoffBarrier
        from src.device_fabric.endpoint_handoff_fence import SignedEndpointFenceDirective
        from src.device_fabric.fenced_transport import FencedPhysicalTransport
        resource, other_resource, device_id = "tv:living-room", "speaker:study", "tv-fenced"
        fence_path = tmp_path / "transport-hold-fence.json"
        barrier_path = tmp_path / "transport-hold.sqlite3"
        fence = ControllerFenceStore(fence_path)
        assert fence.accept(resource, "phone-a", 8) is True
        assert fence.accept(other_resource, "phone-c", 3) is True
        key = P256AuthorityKeyPair.generate("transport-hold-key")
        trust = {key.key_id: key.public_verifier}
        barrier = EndpointHandoffBarrier(barrier_path, device_id=device_id, fence_store=fence, trusted_verifiers=trust, enroll=True)
        unsigned = SignedEndpointFenceDirective(request_id="transport-held-handoff", device_id=device_id, resource_id=resource, previous_controller_id="phone-a", previous_fencing_token=8, controller_id="phone-b", fencing_token=9, issued_at=100.0, expires_at=130.0, issuer_id=key.key_id)
        directive = replace(unsigned, signature=key.sign(unsigned.canonical_bytes))
        original_snapshot = fence.snapshot
        observed_loss = False
        def confirmation_snapshot():
            nonlocal observed_loss
            snapshot = original_snapshot()
            if lose_confirmation and snapshot.get(resource) == (9, "phone-b"):
                observed_loss = True
                raise OSError("simulated lost fence confirmation")
            return snapshot
        monkeypatch.setattr(fence, "snapshot", confirmation_snapshot)
        result = barrier.install(directive, now=101.0)
        monkeypatch.setattr(fence, "snapshot", original_snapshot)
        assert observed_loss is lose_confirmation
        assert result is (not lose_confirmation)
        reopened_fence = ControllerFenceStore(fence_path)
        reopened = EndpointHandoffBarrier(barrier_path, device_id=device_id, fence_store=reopened_fence, trusted_verifiers=trust)
        assert reopened_fence.snapshot()[resource] == (9, "phone-b")
        class Delegate:
            def __init__(self):
                self.device = SimpleNamespace(identity=SimpleNamespace(device_id=device_id))
                self.calls = 0
            async def execute_intent(self, intent, transaction_digest=None, capability_digest=None):
                self.calls += 1
                return ActuationReceipt(receipt_id="test-delegate", intent_id=intent.intent_id, status=ActuationStatus.EXECUTED, device_id=device_id, transaction_id=intent.transaction_id, capability_digest=intent.capability_digest)
        delegate = Delegate()
        transport = FencedPhysicalTransport(delegate, reopened_fence, handoff_barrier=reopened)
        intent = SimpleNamespace(intent_id="held-successor", device_id=device_id, controller_resource_id=resource, controller_id="phone-b", controller_fencing_token=9, transaction_id="tx-held-successor-transport", capability_digest="cap-held-successor")
        receipt = await transport.execute_intent(intent)
        assert receipt.status is ActuationStatus.REJECTED
        assert receipt.device_id == device_id
        assert receipt.transaction_id == intent.transaction_id
        assert receipt.capability_digest == intent.capability_digest
        assert delegate.calls == 0
        assert reopened.is_ready("transport-held-handoff") is False
        independent = SimpleNamespace(**{**vars(intent), "intent_id": "independent", "controller_resource_id": other_resource, "controller_id": "phone-c", "controller_fencing_token": 3, "transaction_id": "tx-independent-transport", "capability_digest": "cap-independent"})
        receipt = await transport.execute_intent(independent)
        assert receipt.status is ActuationStatus.EXECUTED
        assert receipt.transaction_id == independent.transaction_id
        assert delegate.calls == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("failure_point", ["before_hold_commit", "after_hold_commit", "before_result_commit"])
def test_handoff_hold_survives_journal_boundary_faults(tmp_path, monkeypatch, failure_point):
    import sqlite3
    from contextlib import contextmanager
    from dataclasses import replace
    from src.control.remote_controller_protocol import P256AuthorityKeyPair
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    from src.device_fabric.endpoint_handoff_barrier import EndpointHandoffBarrier
    from src.device_fabric.endpoint_handoff_fence import SignedEndpointFenceDirective
    resource, independent, device_id = "tv:living-room", "speaker:study", "tv-fenced"
    fence_path, barrier_path = tmp_path / "fault-fence.json", tmp_path / "fault-barrier.sqlite3"
    fence = ControllerFenceStore(fence_path)
    assert fence.accept(resource, "phone-a", 8) is True
    assert fence.accept(independent, "phone-c", 3) is True
    key = P256AuthorityKeyPair.generate("fault-handoff-key")
    trust = {key.key_id: key.public_verifier}
    barrier = EndpointHandoffBarrier(barrier_path, device_id=device_id, fence_store=fence, trusted_verifiers=trust, enroll=True)
    unsigned = SignedEndpointFenceDirective(request_id="fault-handoff", device_id=device_id, resource_id=resource, previous_controller_id="phone-a", previous_fencing_token=8, controller_id="phone-b", fencing_token=9, issued_at=100.0, expires_at=130.0, issuer_id=key.key_id)
    directive = replace(unsigned, signature=key.sign(unsigned.canonical_bytes))
    original_write, original_accept = barrier._write, fence.accept
    writes, accept_calls = 0, []
    @contextmanager
    def interrupted_write(*, create=False):
        nonlocal writes
        writes += 1
        stage = writes
        with original_write(create=create) as db:
            yield db
            if stage == 1 and failure_point == "before_hold_commit":
                raise OSError("simulated before hold commit")
            if stage == 2 and failure_point == "before_result_commit":
                raise OSError("simulated before result commit")
        if stage == 1 and failure_point == "after_hold_commit":
            raise OSError("simulated after hold commit")
    def recorded_accept(*args):
        accept_calls.append(args)
        return original_accept(*args)
    monkeypatch.setattr(barrier, "_write", interrupted_write)
    monkeypatch.setattr(fence, "accept", recorded_accept)
    with pytest.raises(OSError, match="simulated .* commit"):
        barrier.install(directive, now=101.0)
    assert writes == (2 if failure_point == "before_result_commit" else 1)
    assert accept_calls == ([(resource, "phone-b", 9)] if failure_point == "before_result_commit" else [])
    reopened_fence = ControllerFenceStore(fence_path)
    expected_fence = (9, "phone-b") if failure_point == "before_result_commit" else (8, "phone-a")
    assert reopened_fence.snapshot()[resource] == expected_fence
    with sqlite3.connect(barrier_path) as db:
        holds = db.execute("SELECT request_id FROM endpoint_barrier_holds WHERE resource_id=?", (resource,)).fetchall()
        handoffs = db.execute("SELECT request_id FROM endpoint_barrier_handoffs WHERE request_id=?", (directive.request_id,)).fetchall()
    assert holds == ([] if failure_point == "before_hold_commit" else [(directive.request_id,)])
    assert handoffs == []
    reopened = EndpointHandoffBarrier(barrier_path, device_id=device_id, fence_store=reopened_fence, trusted_verifiers=trust)
    assert reopened.admit(transaction_id="tx-old-after-fault", resource_id=resource, controller_id="phone-a", fencing_token=8) is (failure_point == "before_hold_commit")
    assert reopened.admit(transaction_id="tx-new-after-fault", resource_id=resource, controller_id="phone-b", fencing_token=9) is False
    assert reopened.admit(transaction_id="tx-independent-after-fault", resource_id=independent, controller_id="phone-c", fencing_token=3) is True
    assert reopened.is_ready(directive.request_id) is False


def test_concurrent_handoff_hold_orders_admission_across_store_instances(tmp_path, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import contextmanager
    from dataclasses import replace
    from src.control.remote_controller_protocol import P256AuthorityKeyPair
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    from src.device_fabric.endpoint_handoff_barrier import EndpointHandoffBarrier
    from src.device_fabric.endpoint_handoff_fence import SignedEndpointFenceDirective
    resource, device_id = "tv:living-room", "tv-fenced"
    fence_path, barrier_path = tmp_path / "concurrent-fence.json", tmp_path / "concurrent-barrier.sqlite3"
    installer_fence = ControllerFenceStore(fence_path)
    assert installer_fence.accept(resource, "phone-a", 8) is True
    key = P256AuthorityKeyPair.generate("concurrent-handoff-key")
    trust = {key.key_id: key.public_verifier}
    installing = EndpointHandoffBarrier(barrier_path, device_id=device_id, fence_store=installer_fence, trusted_verifiers=trust, enroll=True)
    admitting_fence = ControllerFenceStore(fence_path)
    admitting = EndpointHandoffBarrier(barrier_path, device_id=device_id, fence_store=admitting_fence, trusted_verifiers=trust)
    assert admitting.admit(transaction_id="tx-before-hold", resource_id=resource, controller_id="phone-a", fencing_token=8) is True
    unsigned = SignedEndpointFenceDirective(request_id="concurrent-handoff", device_id=device_id, resource_id=resource, previous_controller_id="phone-a", previous_fencing_token=8, controller_id="phone-b", fencing_token=9, issued_at=100.0, expires_at=130.0, issuer_id=key.key_id)
    directive = replace(unsigned, signature=key.sign(unsigned.canonical_bytes))
    hold_staged, admission_attempted, release_commit = threading.Event(), threading.Event(), threading.Event()
    original_install_write, original_admit_write = installing._write, admitting._write
    paused = False
    @contextmanager
    def pause_hold_commit(*, create=False):
        nonlocal paused
        with original_install_write(create=create) as db:
            yield db
            if not paused:
                paused = True
                assert db.execute("SELECT request_id FROM endpoint_barrier_holds WHERE resource_id=?", (resource,)).fetchone() == (directive.request_id,)
                hold_staged.set()
                if not release_commit.wait(5.0):
                    raise AssertionError("timed out before releasing hold commit")
    @contextmanager
    def note_admission_attempt(*, create=False):
        admission_attempted.set()
        with original_admit_write(create=create) as db:
            yield db
    monkeypatch.setattr(installing, "_write", pause_hold_commit)
    monkeypatch.setattr(admitting, "_write", note_admission_attempt)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_install = pool.submit(installing.install, directive, now=101.0)
        try:
            assert hold_staged.wait(5.0), "hold was not staged"
            future_admit = pool.submit(admitting.admit, transaction_id="tx-competing-old", resource_id=resource, controller_id="phone-a", fencing_token=8)
            assert admission_attempted.wait(5.0), "competing admission did not start"
        finally:
            release_commit.set()
        assert future_install.result(timeout=10.0) is True
        assert future_admit.result(timeout=10.0) is False
    assert paused is True
    assert admitting_fence.snapshot()[resource] == (9, "phone-b")
    assert admitting.admit(transaction_id="tx-later-successor", resource_id=resource, controller_id="phone-b", fencing_token=9) is False
    assert admitting.is_ready("concurrent-handoff") is False
