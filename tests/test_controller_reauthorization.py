import json
from dataclasses import replace

import pytest

from src.control.active_controller_lease import ActiveControllerLeaseAuthority, ControllerLeaseDecision
from src.control.controller_reauthorization import SignedControllerReauthorizationGrant
from src.control.crypto_identity import KeyPair


def test_signed_reinstall_grant_recovers_above_device_fence_once_across_restart(tmp_path):
    key=KeyPair.generate(key_id="controller-recovery-authority")
    unsigned=SignedControllerReauthorizationGrant(resource_id="tv:living-room",controller_id="phone-b",previous_fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id,nonce="reinstall-recovery-nonce-9",reason="CONTROL_PLANE_REINSTALL")
    expected=json.dumps({"controller_id":"phone-b","expires_at":130.0,"issued_at":100.0,"issuer_id":"controller-recovery-authority","nonce":"reinstall-recovery-nonce-9","previous_fencing_token":9,"reason":"CONTROL_PLANE_REINSTALL","resource_id":"tv:living-room"},sort_keys=True,separators=(",",":")).encode("utf-8")
    assert unsigned.canonical_bytes==expected
    grant=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    state_path=tmp_path / "active-controller-leases.json"
    authority=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
    recovered=authority.reauthorize(grant,now=101.0,ttl_seconds=30.0)
    assert recovered.resource_id=="tv:living-room"
    assert recovered.controller_id=="phone-b"
    assert recovered.fencing_token==10
    restarted=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
    assert restarted.validate(recovered,now=102.0) is ControllerLeaseDecision.ALLOW
    with pytest.raises(RuntimeError,match="replayed"):
        restarted.reauthorize(grant,now=102.0,ttl_seconds=30.0)
    assert restarted.validate(recovered,now=102.0) is ControllerLeaseDecision.ALLOW


def test_tampered_reauthorization_fields_never_mutate_authority(tmp_path):
    key=KeyPair.generate(key_id="controller-recovery-authority")
    unsigned=SignedControllerReauthorizationGrant(resource_id="tv:living-room",controller_id="phone-b",previous_fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id,nonce="reinstall-recovery-nonce-9",reason="CONTROL_PLANE_REINSTALL")
    valid=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    state_path=tmp_path / "active-controller-leases.json"
    authority=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
    tampered=(
        replace(valid,resource_id="tv:bedroom"),
        replace(valid,controller_id="phone-c"),
        replace(valid,previous_fencing_token=10),
        replace(valid,issued_at=99.0),
        replace(valid,expires_at=131.0),
        replace(valid,issuer_id="rogue-recovery-authority"),
        replace(valid,nonce="forged-recovery-nonce"),
    )
    for grant in tampered:
        with pytest.raises(RuntimeError):
            authority.reauthorize(grant,now=101.0,ttl_seconds=30.0)
        assert not state_path.exists()
        assert authority._active=={}
        assert authority._highest_tokens=={}
        assert authority._used_reauthorization_nonces==set()
    recovered=authority.reauthorize(valid,now=101.0,ttl_seconds=30.0)
    assert recovered.fencing_token==10
    assert authority.validate(recovered,now=102.0) is ControllerLeaseDecision.ALLOW


def test_reauthorization_time_window_rejections_do_not_consume_nonce(tmp_path):
    key=KeyPair.generate(key_id="controller-recovery-authority")
    unsigned=SignedControllerReauthorizationGrant(resource_id="tv:living-room",controller_id="phone-b",previous_fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id,nonce="reinstall-recovery-nonce-9",reason="CONTROL_PLANE_REINSTALL")
    grant=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    for name,now,message in (("future",99.999,"not yet valid"),("expired",130.0,"expired")):
        state_path=tmp_path / f"{name}-active-controller-leases.json"
        authority=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
        with pytest.raises(RuntimeError,match=message):
            authority.reauthorize(grant,now=now,ttl_seconds=30.0)
        assert not state_path.exists()
        assert authority._active=={}
        assert authority._highest_tokens=={}
        assert authority._used_reauthorization_nonces==set()


def test_malformed_reauthorization_grants_are_rejected_at_construction():
    base={
        "resource_id":"tv:living-room",
        "controller_id":"phone-b",
        "previous_fencing_token":9,
        "issued_at":100.0,
        "expires_at":130.0,
        "issuer_id":"controller-recovery-authority",
        "nonce":"reinstall-recovery-nonce-9",
        "reason":"CONTROL_PLANE_REINSTALL",
    }
    invalid_changes=(
        {"resource_id":""},
        {"controller_id":"   "},
        {"previous_fencing_token":True},
        {"previous_fencing_token":0},
        {"previous_fencing_token":-1},
        {"issued_at":True},
        {"issued_at":float("nan")},
        {"issued_at":float("inf")},
        {"expires_at":float("nan")},
        {"expires_at":float("inf")},
        {"expires_at":100.0},
        {"expires_at":99.0},
        {"issuer_id":""},
        {"nonce":"   "},
        {"reason":"MANUAL_RESET"},
        {"reason":None},
        {"signature":None},
    )
    for changes in invalid_changes:
        with pytest.raises(ValueError):
            SignedControllerReauthorizationGrant(**{**base,**changes})


def test_reauthorization_cannot_roll_persistent_fence_backward(tmp_path):
    key=KeyPair.generate(key_id="controller-recovery-authority")
    def signed(previous_fencing_token,controller_id,nonce):
        unsigned=SignedControllerReauthorizationGrant(resource_id="tv:living-room",controller_id=controller_id,previous_fencing_token=previous_fencing_token,issued_at=100.0,expires_at=140.0,issuer_id=key.key_id,nonce=nonce,reason="CONTROL_PLANE_REINSTALL")
        return replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    state_path=tmp_path / "active-controller-leases.json"
    authority=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
    first=authority.reauthorize(signed(9,"phone-b","recovery-9"),now=101.0,ttl_seconds=30.0)
    assert first.fencing_token==10
    stale=signed(9,"phone-c","stale-recovery-9")
    with pytest.raises(RuntimeError,match="fence is stale"):
        authority.reauthorize(stale,now=102.0,ttl_seconds=30.0)
    assert authority.validate(first,now=103.0) is ControllerLeaseDecision.ALLOW
    assert (key.key_id,stale.nonce) not in authority._used_reauthorization_nonces
    restarted=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
    assert restarted.validate(first,now=103.0) is ControllerLeaseDecision.ALLOW
    successor=restarted.reauthorize(signed(10,"phone-c","recovery-10"),now=104.0,ttl_seconds=30.0)
    assert successor.fencing_token==11
    assert restarted.validate(first,now=105.0) is ControllerLeaseDecision.STALE_FENCE
    assert restarted.validate(successor,now=105.0) is ControllerLeaseDecision.ALLOW


def test_failed_reauthorization_persistence_does_not_publish_or_consume_nonce(tmp_path):
    key=KeyPair.generate(key_id="controller-recovery-authority")
    unsigned=SignedControllerReauthorizationGrant(resource_id="tv:living-room",controller_id="phone-b",previous_fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id,nonce="reinstall-recovery-nonce-9",reason="CONTROL_PLANE_REINSTALL")
    grant=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    state_path=tmp_path / "active-controller-leases.json"
    authority=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
    real_save=authority._save_state
    def fail_save(active,highest_tokens,used_reauthorization_nonces=None):
        raise OSError("controller recovery storage unavailable")
    authority._save_state=fail_save
    with pytest.raises(OSError,match="storage unavailable"):
        authority.reauthorize(grant,now=101.0,ttl_seconds=30.0)
    assert not state_path.exists()
    assert authority._active=={}
    assert authority._highest_tokens=={}
    assert authority._used_reauthorization_nonces==set()
    authority._save_state=real_save
    recovered=authority.reauthorize(grant,now=102.0,ttl_seconds=30.0)
    assert recovered.fencing_token==10
    restarted=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
    assert restarted.validate(recovered,now=103.0) is ControllerLeaseDecision.ALLOW
    assert restarted._used_reauthorization_nonces=={(key.key_id,grant.nonce)}


def test_concurrent_persistent_reauthorization_allows_exactly_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    key=KeyPair.generate(key_id="controller-recovery-authority")
    unsigned=SignedControllerReauthorizationGrant(resource_id="tv:living-room",controller_id="phone-b",previous_fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id,nonce="reinstall-recovery-nonce-9",reason="CONTROL_PLANE_REINSTALL")
    grant=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    state_path=tmp_path / "active-controller-leases.json"
    authorities=(
        ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier}),
        ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier}),
    )
    barrier=Barrier(2)
    def contend(index):
        barrier.wait(timeout=5.0)
        try:
            return authorities[index].reauthorize(grant,now=101.0,ttl_seconds=30.0)
        except RuntimeError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=tuple(pool.map(contend,(0,1)))
    leases=[result for result in results if not isinstance(result,BaseException)]
    failures=[result for result in results if isinstance(result,BaseException)]
    assert len(leases)==1
    assert len(failures)==1
    assert "replayed" in str(failures[0])
    assert leases[0].fencing_token==10
    restarted=ActiveControllerLeaseAuthority(state_path=state_path,recovery_verifiers={key.key_id:key.public_verifier})
    assert restarted.validate(leases[0],now=102.0) is ControllerLeaseDecision.ALLOW
    assert restarted._highest_tokens=={"tv:living-room":10}
    assert restarted._used_reauthorization_nonces=={(key.key_id,grant.nonce)}


@pytest.mark.asyncio
async def test_reauthorization_recovers_above_persistent_device_fence(tmp_path):
    from src.device_fabric.contracts import ActuationStatus,AuthorizedActionIntent,DeviceState
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    from src.device_fabric.mocks.mock_tv import MockTVAdapter
    fence_path=tmp_path / "controller-fences.json"
    fence_store=ControllerFenceStore(fence_path)
    assert fence_store.accept("tv:living-room","phone-a",9) is True
    adapter=MockTVAdapter("tv-fenced",fence_store=fence_store)
    stale=AuthorizedActionIntent(intent_id="intent-reinstalled-token-1",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=99.0),transaction_id="tx-stale",capability_digest="cap-stale",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=1)
    rejected=await adapter.execute_intent(stale)
    assert rejected.status is ActuationStatus.REJECTED
    assert adapter.device.state.volume==10.0
    assert adapter._executed_intents==set()
    assert fence_store.snapshot()=={"tv:living-room":(9,"phone-a")}
    key=KeyPair.generate(key_id="controller-recovery-authority")
    unsigned=SignedControllerReauthorizationGrant(resource_id="tv:living-room",controller_id="phone-b",previous_fencing_token=9,issued_at=100.0,expires_at=130.0,issuer_id=key.key_id,nonce="device-fence-recovery-9",reason="CONTROL_PLANE_REINSTALL")
    grant=replace(unsigned,signature=key.sign(unsigned.canonical_bytes))
    authority=ActiveControllerLeaseAuthority(state_path=tmp_path / "active-controller-leases.json",recovery_verifiers={key.key_id:key.public_verifier})
    recovered=authority.reauthorize(grant,now=101.0,ttl_seconds=30.0)
    assert recovered.fencing_token==10
    intent=AuthorizedActionIntent(intent_id="intent-recovered-token-10",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=30.0),transaction_id="tx-recovered",capability_digest="cap-recovered",controller_resource_id=recovered.resource_id,controller_id=recovered.controller_id,controller_fencing_token=recovered.fencing_token)
    receipt=await adapter.execute_intent(intent)
    assert receipt.status is ActuationStatus.EXECUTED
    assert adapter.device.state.volume==30.0
    assert fence_store.snapshot()=={"tv:living-room":(10,"phone-b")}


def test_authority_rejects_corrupt_persistent_reauthorization_nonce_ledger(tmp_path):
    invalid_ledgers=(
        [["controller-recovery-authority","nonce-1"],["controller-recovery-authority","nonce-1"]],
        [["controller-recovery-authority"]],
        [["","nonce-1"]],
        ["controller-recovery-authority:nonce-1"],
    )
    for index,ledger in enumerate(invalid_ledgers):
        state_path=tmp_path / f"corrupt-{index}.json"
        state_path.write_text(json.dumps({"version":2,"resources":{},"used_reauthorization_nonces":ledger}),encoding="utf-8")
        before=state_path.read_bytes()
        with pytest.raises(ValueError,match="invalid controller reauthorization nonce record"):
            ActiveControllerLeaseAuthority(state_path=state_path)
        assert state_path.read_bytes()==before
