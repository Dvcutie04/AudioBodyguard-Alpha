from src.control.active_controller_lease import ActiveControllerLeaseAuthority, ControllerLeaseDecision


def test_handoff_fences_previous_phone_immediately():
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    second=authority.handoff(current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    assert second.fencing_token==first.fencing_token+1
    assert authority.validate(first,now=102.0) is ControllerLeaseDecision.STALE_FENCE
    assert authority.validate(second,now=102.0) is ControllerLeaseDecision.ALLOW


def test_active_acquisition_is_exclusive_and_rejection_does_not_mutate_state():
    import pytest
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    with pytest.raises(RuntimeError,match="already has an active controller"):
        authority.acquire(resource_id="tv:living-room",controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    assert authority.validate(first,now=102.0) is ControllerLeaseDecision.ALLOW
    second=authority.acquire(resource_id="tv:living-room",controller_id="phone-b",now=130.0,ttl_seconds=30.0)
    assert second.fencing_token==first.fencing_token+1
    assert second.controller_id=="phone-b"
    assert authority.validate(first,now=131.0) is ControllerLeaseDecision.STALE_FENCE
    assert authority.validate(second,now=131.0) is ControllerLeaseDecision.ALLOW


def test_acquisition_is_allowed_strictly_after_expiry_with_higher_token():
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="speaker:kitchen",controller_id="phone-a",now=10.0,ttl_seconds=5.0)
    assert authority.validate(first,now=15.0) is ControllerLeaseDecision.EXPIRED
    second=authority.acquire(resource_id="speaker:kitchen",controller_id="phone-b",now=15.001,ttl_seconds=5.0)
    assert second.fencing_token>first.fencing_token
    assert authority.validate(second,now=16.0) is ControllerLeaseDecision.ALLOW


def test_invalid_acquisition_inputs_do_not_create_state_or_consume_token():
    import pytest
    authority=ActiveControllerLeaseAuthority()
    invalid_cases=[
        {"resource_id":"","controller_id":"phone-a","now":100.0,"ttl_seconds":30.0},
        {"resource_id":"tv:living-room","controller_id":"   ","now":100.0,"ttl_seconds":30.0},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":True,"ttl_seconds":30.0},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":float("nan"),"ttl_seconds":30.0},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":float("inf"),"ttl_seconds":30.0},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":float("-inf"),"ttl_seconds":30.0},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":100.0,"ttl_seconds":False},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":100.0,"ttl_seconds":float("nan")},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":100.0,"ttl_seconds":float("inf")},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":100.0,"ttl_seconds":float("-inf")},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":100.0,"ttl_seconds":0.0},
        {"resource_id":"tv:living-room","controller_id":"phone-a","now":100.0,"ttl_seconds":-1.0},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(ValueError):
            authority.acquire(**kwargs)
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    assert first.fencing_token==1


def test_invalid_validation_inputs_do_not_change_active_lease():
    import pytest
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    with pytest.raises(ValueError):
        authority.validate(object(),now=101.0)
    for invalid_now in (True,float("nan"),float("inf"),float("-inf")):
        with pytest.raises(ValueError):
            authority.validate(first,now=invalid_now)
    assert authority.validate(first,now=102.0) is ControllerLeaseDecision.ALLOW
    second=authority.handoff(current_lease=first,next_controller_id="phone-b",now=103.0,ttl_seconds=30.0)
    assert second.fencing_token==first.fencing_token+1


def test_invalid_handoff_inputs_do_not_change_state_or_consume_token():
    import pytest
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    invalid_cases=[
        {"current_lease":object(),"next_controller_id":"phone-b","now":101.0,"ttl_seconds":30.0},
        {"current_lease":first,"next_controller_id":"","now":101.0,"ttl_seconds":30.0},
        {"current_lease":first,"next_controller_id":"phone-b","now":True,"ttl_seconds":30.0},
        {"current_lease":first,"next_controller_id":"phone-b","now":float("nan"),"ttl_seconds":30.0},
        {"current_lease":first,"next_controller_id":"phone-b","now":float("inf"),"ttl_seconds":30.0},
        {"current_lease":first,"next_controller_id":"phone-b","now":float("-inf"),"ttl_seconds":30.0},
        {"current_lease":first,"next_controller_id":"phone-b","now":101.0,"ttl_seconds":False},
        {"current_lease":first,"next_controller_id":"phone-b","now":101.0,"ttl_seconds":0.0},
        {"current_lease":first,"next_controller_id":"phone-b","now":101.0,"ttl_seconds":-1.0},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(ValueError):
            authority.handoff(**kwargs)
    assert authority.validate(first,now=102.0) is ControllerLeaseDecision.ALLOW
    second=authority.handoff(current_lease=first,next_controller_id="phone-b",now=103.0,ttl_seconds=30.0)
    assert second.fencing_token==first.fencing_token+1


def test_handoff_at_expiry_fails_without_consuming_token():
    import pytest
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    with pytest.raises(RuntimeError,match="expired"):
        authority.handoff(current_lease=first,next_controller_id="phone-b",now=130.0,ttl_seconds=30.0)
    assert authority.validate(first,now=130.0) is ControllerLeaseDecision.EXPIRED
    second=authority.acquire(resource_id="tv:living-room",controller_id="phone-b",now=130.0,ttl_seconds=30.0)
    assert second.fencing_token==first.fencing_token+1


def test_forged_controller_with_current_token_is_stale():
    from dataclasses import replace
    authority=ActiveControllerLeaseAuthority()
    active=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    forged=replace(active,controller_id="observer-phone")
    assert forged.fencing_token==active.fencing_token
    assert authority.validate(forged,now=101.0) is ControllerLeaseDecision.STALE_FENCE
    assert authority.validate(active,now=101.0) is ControllerLeaseDecision.ALLOW


def test_modified_token_or_lease_times_are_stale():
    from dataclasses import replace
    authority=ActiveControllerLeaseAuthority()
    active=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    alterations=(
        replace(active,fencing_token=active.fencing_token-1),
        replace(active,fencing_token=active.fencing_token+1),
        replace(active,issued_at=active.issued_at-1.0),
        replace(active,expires_at=active.expires_at+1.0),
    )
    for forged in alterations:
        assert authority.validate(forged,now=101.0) is ControllerLeaseDecision.STALE_FENCE
    assert authority.validate(active,now=101.0) is ControllerLeaseDecision.ALLOW


def test_lease_for_unknown_resource_is_not_allowed():
    from dataclasses import replace
    authority=ActiveControllerLeaseAuthority()
    active=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    unknown=replace(active,resource_id="tv:unknown")
    assert authority.validate(unknown,now=101.0) is ControllerLeaseDecision.UNKNOWN_RESOURCE
    assert authority.validate(active,now=101.0) is ControllerLeaseDecision.ALLOW


def test_replayed_earlier_lease_never_regains_authority():
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    second=authority.handoff(current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    third=authority.handoff(current_lease=second,next_controller_id="phone-c",now=102.0,ttl_seconds=30.0)
    assert authority.validate(first,now=103.0) is ControllerLeaseDecision.STALE_FENCE
    assert authority.validate(second,now=103.0) is ControllerLeaseDecision.STALE_FENCE
    assert authority.validate(third,now=103.0) is ControllerLeaseDecision.ALLOW
    assert third.fencing_token==first.fencing_token+2
    assert authority.validate(first,now=104.0) is ControllerLeaseDecision.STALE_FENCE


def test_concurrent_acquisition_has_exactly_one_winner_and_one_token():
    import threading
    authority=ActiveControllerLeaseAuthority()
    start=threading.Barrier(3)
    result_lock=threading.Lock()
    successes=[]
    failures=[]

    def contend(controller_id):
        try:
            start.wait(timeout=5.0)
            lease=authority.acquire(resource_id="tv:living-room",controller_id=controller_id,now=100.0,ttl_seconds=30.0)
            with result_lock:
                successes.append(lease)
        except BaseException as exc:
            with result_lock:
                failures.append(exc)

    threads=[threading.Thread(target=contend,args=(controller_id,)) for controller_id in ("phone-a","phone-b")]
    for thread in threads:
        thread.start()
    start.wait(timeout=5.0)
    for thread in threads:
        thread.join(timeout=5.0)
    assert all(not thread.is_alive() for thread in threads)
    assert len(successes)==1
    assert len(failures)==1
    assert isinstance(failures[0],RuntimeError)
    winner=successes[0]
    assert winner.fencing_token==1
    assert authority.validate(winner,now=101.0) is ControllerLeaseDecision.ALLOW
    assert len(authority._active)==1
    assert authority._active=={"tv:living-room":winner}
    assert authority._highest_tokens=={"tv:living-room":1}
    next_controller="phone-b" if winner.controller_id=="phone-a" else "phone-a"
    successor=authority.acquire(resource_id="tv:living-room",controller_id=next_controller,now=130.0,ttl_seconds=30.0)
    assert successor.fencing_token==2


def test_authority_restart_restores_active_lease_and_monotonic_token(tmp_path):
    import pytest
    state_path=tmp_path / "active-controller-leases.json"
    first_authority=ActiveControllerLeaseAuthority(state_path=state_path)
    first=first_authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    restarted=ActiveControllerLeaseAuthority(state_path=state_path)
    assert restarted.validate(first,now=101.0) is ControllerLeaseDecision.ALLOW
    with pytest.raises(RuntimeError,match="already has an active controller"):
        restarted.acquire(resource_id="tv:living-room",controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    successor=restarted.acquire(resource_id="tv:living-room",controller_id="phone-b",now=130.0,ttl_seconds=30.0)
    assert successor.fencing_token==first.fencing_token+1
    restarted_again=ActiveControllerLeaseAuthority(state_path=state_path)
    assert restarted_again.validate(first,now=131.0) is ControllerLeaseDecision.STALE_FENCE
    assert restarted_again.validate(successor,now=131.0) is ControllerLeaseDecision.ALLOW


def test_authority_rejects_rolled_back_persistent_fence_state(tmp_path):
    import json
    import pytest
    state_path=tmp_path / "active-controller-leases.json"
    corrupted={"version":1,"resources":{"tv:living-room":{"controller_id":"phone-a","fencing_token":9,"issued_at":100.0,"expires_at":130.0,"highest_token":8}}}
    state_path.write_text(json.dumps(corrupted),encoding="utf-8")
    before=state_path.read_bytes()
    with pytest.raises(ValueError,match="invalid active controller lease record"):
        ActiveControllerLeaseAuthority(state_path=state_path)
    assert state_path.read_bytes()==before


def test_concurrent_persistent_authorities_issue_exactly_one_lease(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    state_path=tmp_path / "active-controller-leases.json"
    authorities=(ActiveControllerLeaseAuthority(state_path=state_path),ActiveControllerLeaseAuthority(state_path=state_path))
    barrier=Barrier(2)
    def contend(index):
        barrier.wait(timeout=5.0)
        try:
            return authorities[index].acquire(resource_id="tv:living-room",controller_id=f"phone-{index}",now=100.0,ttl_seconds=30.0)
        except RuntimeError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=tuple(pool.map(contend,(0,1)))
    leases=[result for result in results if not isinstance(result,BaseException)]
    failures=[result for result in results if isinstance(result,BaseException)]
    assert len(leases)==1
    assert len(failures)==1
    assert str(failures[0])=="resource already has an active controller"
    assert leases[0].fencing_token==1
    restarted=ActiveControllerLeaseAuthority(state_path=state_path)
    assert restarted.validate(leases[0],now=101.0) is ControllerLeaseDecision.ALLOW
    assert restarted._highest_tokens=={"tv:living-room":1}


def test_failed_persistent_handoff_does_not_publish_or_consume_token(tmp_path):
    import pytest
    state_path=tmp_path / "active-controller-leases.json"
    authority=ActiveControllerLeaseAuthority(state_path=state_path)
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    def fail_save(active,highest_tokens):
        raise OSError("controller authority storage unavailable")
    authority._save_state=fail_save
    with pytest.raises(OSError,match="storage unavailable"):
        authority.handoff(current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    assert authority.validate(first,now=102.0) is ControllerLeaseDecision.ALLOW
    restarted=ActiveControllerLeaseAuthority(state_path=state_path)
    assert restarted.validate(first,now=102.0) is ControllerLeaseDecision.ALLOW
    assert restarted._highest_tokens=={"tv:living-room":1}
    successor=restarted.handoff(current_lease=first,next_controller_id="phone-b",now=103.0,ttl_seconds=30.0)
    assert successor.fencing_token==2


def test_signed_controller_grant_binds_resource_controller_fence_and_key():
    from dataclasses import replace
    from src.control.controller_lease_grant import SignedControllerLeaseGrant
    from src.control.crypto_identity import KeyPair
    issuer=KeyPair.generate("controller-authority")
    unsigned=SignedControllerLeaseGrant(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,controller_key_id="secure-key-a",issued_at=100.0,expires_at=130.0,nonce="grant-1",issuer_id=issuer.key_id)
    grant=replace(unsigned,signature=issuer.sign(unsigned.canonical_bytes))
    assert issuer.public_verifier.verify(grant.canonical_bytes,grant.signature)
    mutations=(replace(grant,resource_id="tv:bedroom"),replace(grant,controller_id="phone-b"),replace(grant,fencing_token=8),replace(grant,controller_key_id="secure-key-b"),replace(grant,expires_at=131.0),replace(grant,nonce="grant-2"),replace(grant,issuer_id="other-authority"))
    assert all(not issuer.public_verifier.verify(candidate.canonical_bytes,candidate.signature) for candidate in mutations)


def test_controller_grant_verifier_fails_closed_for_invalid_authority_or_time():
    from dataclasses import replace
    from src.control.controller_lease_grant import ControllerLeaseGrantDecision,ControllerLeaseGrantVerifier,SignedControllerLeaseGrant
    from src.control.crypto_identity import KeyPair
    issuer=KeyPair.generate("controller-authority")
    attacker=KeyPair.generate("attacker")
    unsigned=SignedControllerLeaseGrant(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,controller_key_id="secure-key-a",issued_at=100.0,expires_at=130.0,nonce="grant-2",issuer_id=issuer.key_id)
    grant=replace(unsigned,signature=issuer.sign(unsigned.canonical_bytes))
    validator=ControllerLeaseGrantVerifier({issuer.key_id:issuer.public_verifier})
    assert validator.validate(grant,now=110.0) is ControllerLeaseGrantDecision.ALLOW
    assert validator.validate(replace(grant,controller_id="phone-b"),now=110.0) is ControllerLeaseGrantDecision.INVALID_SIGNATURE
    unknown_unsigned=replace(unsigned,issuer_id=attacker.key_id)
    unknown=replace(unknown_unsigned,signature=attacker.sign(unknown_unsigned.canonical_bytes))
    assert validator.validate(unknown,now=110.0) is ControllerLeaseGrantDecision.UNKNOWN_ISSUER
    assert validator.validate(grant,now=99.999) is ControllerLeaseGrantDecision.NOT_YET_VALID
    assert validator.validate(grant,now=130.0) is ControllerLeaseGrantDecision.EXPIRED


def test_controller_grant_verifier_rejects_malformed_values_without_exception():
    from dataclasses import replace
    from src.control.controller_lease_grant import ControllerLeaseGrantDecision,ControllerLeaseGrantVerifier,SignedControllerLeaseGrant
    from src.control.crypto_identity import KeyPair
    issuer=KeyPair.generate("controller-authority")
    unsigned=SignedControllerLeaseGrant(resource_id="tv:living-room",controller_id="phone-a",fencing_token=7,controller_key_id="secure-key-a",issued_at=100.0,expires_at=130.0,nonce="grant-3",issuer_id=issuer.key_id)
    sign=lambda candidate:replace(candidate,signature=issuer.sign(candidate.canonical_bytes))
    validator=ControllerLeaseGrantVerifier({issuer.key_id:issuer.public_verifier})
    valid=sign(unsigned)
    invalid_now=(True,"110",float("nan"),float("inf"),float("-inf"))
    assert all(validator.validate(valid,now=value) is ControllerLeaseGrantDecision.MALFORMED for value in invalid_now)
    malformed=(replace(unsigned,resource_id=""),replace(unsigned,controller_id=" "),replace(unsigned,fencing_token=True),replace(unsigned,fencing_token=0),replace(unsigned,controller_key_id=""),replace(unsigned,issued_at=float("nan")),replace(unsigned,expires_at=float("inf")),replace(unsigned,expires_at=100.0),replace(unsigned,nonce=""),replace(unsigned,issuer_id=""))
    assert all(validator.validate(sign(candidate),now=110.0) is ControllerLeaseGrantDecision.MALFORMED for candidate in malformed)
    assert validator.validate(replace(valid,signature=""),now=110.0) is ControllerLeaseGrantDecision.MALFORMED
    assert validator.validate(None,now=110.0) is ControllerLeaseGrantDecision.MALFORMED


def test_only_current_fencing_holder_can_receive_signed_controller_grant():
    import pytest
    from src.control.controller_lease_grant import ControllerLeaseGrantIssuer
    from src.control.crypto_identity import KeyPair
    authority=ActiveControllerLeaseAuthority()
    signing_key=KeyPair.generate("controller-authority")
    issuer=ControllerLeaseGrantIssuer(authority,signing_key)
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    grant=issuer.issue(lease=first,controller_key_id="secure-key-a",nonce="grant-4",now=101.0)
    assert grant.resource_id==first.resource_id
    assert grant.controller_id==first.controller_id
    assert grant.fencing_token==first.fencing_token
    assert grant.issued_at==first.issued_at
    assert grant.expires_at==first.expires_at
    assert grant.controller_key_id=="secure-key-a"
    assert signing_key.public_verifier.verify(grant.canonical_bytes,grant.signature)
    second=authority.handoff(current_lease=first,next_controller_id="phone-b",now=102.0,ttl_seconds=30.0)
    assert second.fencing_token>first.fencing_token
    with pytest.raises(RuntimeError,match="STALE_FENCE"):
        issuer.issue(lease=first,controller_key_id="secure-key-a",nonce="grant-5",now=103.0)
