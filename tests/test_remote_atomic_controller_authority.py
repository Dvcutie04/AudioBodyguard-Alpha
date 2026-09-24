from src.control.remote_atomic_controller_authority import IdempotentRemoteControllerAuthority


def test_retried_acquisition_returns_identical_committed_lease_without_incrementing_twice():
    authority=IdempotentRemoteControllerAuthority()
    first=authority.acquire(request_id="request-acquire-phone-a",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    retry=authority.acquire(request_id="request-acquire-phone-a",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    assert retry==first
    assert retry.fencing_token==1
    assert authority.highest_token("tv:living-room")==1
    successor=authority.acquire(request_id="request-acquire-phone-b",resource_id="tv:living-room",controller_id="phone-b",now=130.0,ttl_seconds=30.0)
    assert successor.fencing_token==2


def test_concurrent_identical_requests_commit_exactly_once():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    authority=IdempotentRemoteControllerAuthority()
    barrier=Barrier(2)
    def acquire(_):
        barrier.wait(timeout=5.0)
        return authority.acquire(request_id="request-concurrent-phone-a",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=tuple(pool.map(acquire,(0,1)))
    assert results[0]==results[1]
    assert results[0].fencing_token==1
    assert authority.highest_token("tv:living-room")==1


def test_committed_request_id_cannot_be_reused_for_different_payload():
    import pytest
    authority=IdempotentRemoteControllerAuthority()
    committed=authority.acquire(request_id="request-bound-payload",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    with pytest.raises(ValueError,match="different payload"):
        authority.acquire(request_id="request-bound-payload",resource_id="tv:living-room",controller_id="phone-b",now=100.0,ttl_seconds=30.0)
    assert authority.highest_token("tv:living-room")==1
    assert authority._authority.validate(committed,now=101.0).name=="ALLOW"


def test_committed_request_survives_authority_restart(tmp_path):
    state_path=tmp_path/"remote-controller-authority.json"
    first_authority=IdempotentRemoteControllerAuthority(state_path=state_path)
    first=first_authority.acquire(request_id="request-restart-phone-a",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path)
    retry=restarted.acquire(request_id="request-restart-phone-a",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    assert retry==first
    assert restarted.highest_token("tv:living-room")==1
    successor=restarted.acquire(request_id="request-after-restart-phone-b",resource_id="tv:living-room",controller_id="phone-b",now=130.0,ttl_seconds=30.0)
    assert successor.fencing_token==2


def test_failed_remote_persistence_does_not_publish_or_consume_token(tmp_path):
    import pytest
    state_path=tmp_path/"remote-controller-authority.json"
    authority=IdempotentRemoteControllerAuthority(state_path=state_path)
    real_save=authority._save_state
    def fail_save(committed_requests):
        raise OSError("remote authority storage unavailable")
    authority._save_state=fail_save
    with pytest.raises(OSError,match="storage unavailable"):
        authority.acquire(request_id="request-failed-storage",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    assert authority.highest_token("tv:living-room")==0
    assert not state_path.exists()
    authority._save_state=real_save
    committed=authority.acquire(request_id="request-after-storage-recovery",resource_id="tv:living-room",controller_id="phone-a",now=101.0,ttl_seconds=30.0)
    assert committed.fencing_token==1
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path)
    assert restarted.highest_token("tv:living-room")==1


def test_concurrent_service_instances_commit_shared_request_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    state_path=tmp_path/"remote-controller-authority.json"
    authorities=(IdempotentRemoteControllerAuthority(state_path=state_path),IdempotentRemoteControllerAuthority(state_path=state_path))
    barrier=Barrier(2)
    def acquire(index):
        barrier.wait(timeout=5.0)
        return authorities[index].acquire(request_id="request-shared-across-instances",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=tuple(pool.map(acquire,(0,1)))
    assert results[0]==results[1]
    assert results[0].fencing_token==1
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path)
    assert restarted.highest_token("tv:living-room")==1
    assert restarted.acquire(request_id="request-shared-across-instances",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)==results[0]


def test_retried_handoff_returns_identical_successor_and_fences_previous_controller():
    authority=IdempotentRemoteControllerAuthority()
    first=authority.acquire(request_id="request-acquire-phone-a-for-handoff",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    second=authority.handoff(request_id="request-handoff-phone-b",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    retry=authority.handoff(request_id="request-handoff-phone-b",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    assert retry==second
    assert second.fencing_token==first.fencing_token+1
    assert authority.highest_token("tv:living-room")==2
    assert authority._authority.validate(first,now=102.0).name=="STALE_FENCE"
    assert authority._authority.validate(second,now=102.0).name=="ALLOW"


def test_committed_handoff_survives_restart_without_advancing_again(tmp_path):
    state_path=tmp_path/"remote-controller-authority.json"
    authority=IdempotentRemoteControllerAuthority(state_path=state_path)
    first=authority.acquire(request_id="request-persistent-phone-a",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    second=authority.handoff(request_id="request-persistent-handoff-phone-b",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path)
    retry=restarted.handoff(request_id="request-persistent-handoff-phone-b",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    assert retry==second
    assert retry.fencing_token==2
    assert restarted.highest_token("tv:living-room")==2
    assert restarted._authority.validate(first,now=102.0).name=="STALE_FENCE"
    assert restarted._authority.validate(second,now=102.0).name=="ALLOW"


def test_failed_handoff_persistence_keeps_previous_controller_and_token(tmp_path):
    import pytest
    state_path=tmp_path/"remote-controller-authority.json"
    authority=IdempotentRemoteControllerAuthority(state_path=state_path)
    first=authority.acquire(request_id="request-phone-a-before-failed-handoff",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    real_save=authority._save_state
    def fail_save(committed_requests):
        raise OSError("remote authority storage unavailable")
    authority._save_state=fail_save
    with pytest.raises(OSError,match="storage unavailable"):
        authority.handoff(request_id="request-failed-handoff-phone-b",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    assert authority.highest_token("tv:living-room")==1
    assert authority._authority.validate(first,now=102.0).name=="ALLOW"
    authority._save_state=real_save
    second=authority.handoff(request_id="request-recovered-handoff-phone-b",current_lease=first,next_controller_id="phone-b",now=103.0,ttl_seconds=30.0)
    assert second.fencing_token==2
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path)
    assert restarted._authority.validate(first,now=104.0).name=="STALE_FENCE"
    assert restarted._authority.validate(second,now=104.0).name=="ALLOW"


def test_corrupted_remote_fence_state_fails_closed_without_rewriting_file(tmp_path):
    import json
    import pytest
    state_path=tmp_path/"remote-controller-authority.json"
    authority=IdempotentRemoteControllerAuthority(state_path=state_path)
    authority.acquire(request_id="request-before-corruption",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    corrupted=json.loads(state_path.read_text(encoding="utf-8"))
    corrupted["resources"]["tv:living-room"]["highest_token"]=0
    state_path.write_text(json.dumps(corrupted,sort_keys=True,separators=(",",":")),encoding="utf-8")
    before=state_path.read_bytes()
    with pytest.raises(ValueError,match="invalid remote controller authority resource"):
        IdempotentRemoteControllerAuthority(state_path=state_path)
    assert state_path.read_bytes()==before


def test_committed_remote_lease_can_be_issued_as_request_bound_signed_grant():
    from dataclasses import replace
    from src.control.controller_lease_grant import ControllerLeaseGrantDecision,ControllerLeaseGrantVerifier
    from src.control.crypto_identity import KeyPair
    signing_key=KeyPair.generate("remote-controller-authority")
    authority=IdempotentRemoteControllerAuthority(signing_key=signing_key)
    request_id="request-signed-phone-a"
    lease=authority.acquire(request_id=request_id,resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    grant=authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=101.0)
    retry=authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=101.0)
    assert retry==grant
    assert grant.resource_id==lease.resource_id
    assert grant.controller_id==lease.controller_id
    assert grant.fencing_token==lease.fencing_token
    assert grant.controller_key_id=="secure-phone-a-key"
    assert grant.nonce==request_id
    verifier=ControllerLeaseGrantVerifier({signing_key.key_id:signing_key.public_verifier})
    assert verifier.validate(grant,now=101.0) is ControllerLeaseGrantDecision.ALLOW
    mutations=(replace(grant,controller_id="phone-b"),replace(grant,fencing_token=2),replace(grant,controller_key_id="attacker-key"),replace(grant,nonce="different-request"))
    assert all(verifier.validate(candidate,now=101.0) is ControllerLeaseGrantDecision.INVALID_SIGNATURE for candidate in mutations)


def test_superseded_committed_request_cannot_mint_signed_grant():
    import pytest
    from src.control.controller_lease_grant import ControllerLeaseGrantDecision,ControllerLeaseGrantVerifier
    from src.control.crypto_identity import KeyPair
    real_key=KeyPair.generate("remote-controller-authority")
    class CountingSigningKey:
        key_id=real_key.key_id
        public_verifier=real_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return real_key.sign(data)
    signing_key=CountingSigningKey()
    authority=IdempotentRemoteControllerAuthority(signing_key=signing_key)
    first_request="request-phone-a-before-handoff"
    second_request="request-handoff-phone-b-for-grant"
    first=authority.acquire(request_id=first_request,resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    second=authority.handoff(request_id=second_request,current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    with pytest.raises(RuntimeError,match="STALE_FENCE"):
        authority.issue_grant(request_id=first_request,controller_key_id="secure-phone-a-key",now=102.0)
    assert signing_key.calls==0
    with pytest.raises(RuntimeError,match="endpoint readiness"):
        authority.issue_grant(request_id=second_request,controller_key_id="secure-phone-b-key",now=102.0)
    assert signing_key.calls==0
    assert second.fencing_token==first.fencing_token+1


def test_remote_authority_uses_only_its_configured_signing_key():
    import pytest
    from src.control.controller_lease_grant import ControllerLeaseGrantDecision,ControllerLeaseGrantVerifier
    from src.control.crypto_identity import KeyPair
    authority_key=KeyPair.generate("trusted-remote-controller-authority")
    attacker_key=KeyPair.generate("attacker")
    authority=IdempotentRemoteControllerAuthority(signing_key=authority_key)
    request_id="request-pinned-authority-signer"
    authority.acquire(request_id=request_id,resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    grant=authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=101.0)
    assert grant.issuer_id==authority_key.key_id
    verifier=ControllerLeaseGrantVerifier({authority_key.key_id:authority_key.public_verifier})
    assert verifier.validate(grant,now=101.0) is ControllerLeaseGrantDecision.ALLOW
    with pytest.raises(TypeError):
        authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",signing_key=attacker_key,now=101.0)


def test_request_bound_signed_grant_is_identical_after_restart(tmp_path):
    from src.control.controller_lease_grant import ControllerLeaseGrantDecision,ControllerLeaseGrantVerifier
    from src.control.crypto_identity import KeyPair
    state_path=tmp_path/"remote-controller-authority.json"
    signing_key=KeyPair.generate("durable-remote-controller-authority")
    request_id="request-signed-before-restart"
    authority=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    authority.acquire(request_id=request_id,resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    first_grant=authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=101.0)
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    retry_grant=restarted.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=102.0)
    assert retry_grant==first_grant
    assert retry_grant.nonce==request_id
    assert retry_grant.fencing_token==1
    verifier=ControllerLeaseGrantVerifier({signing_key.key_id:signing_key.public_verifier})
    assert verifier.validate(retry_grant,now=102.0) is ControllerLeaseGrantDecision.ALLOW


def test_committed_request_cannot_be_resigned_for_different_controller_key():
    import pytest
    from src.control.crypto_identity import KeyPair
    real_key=KeyPair.generate("remote-controller-authority")
    class CountingSigningKey:
        key_id=real_key.key_id
        public_verifier=real_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return real_key.sign(data)
    signing_key=CountingSigningKey()
    authority=IdempotentRemoteControllerAuthority(signing_key=signing_key)
    request_id="request-controller-key-bound-once"
    authority.acquire(request_id=request_id,resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    first=authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=101.0)
    retry=authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=102.0)
    assert retry==first
    assert signing_key.calls==2
    with pytest.raises(ValueError,match="different controller key"):
        authority.issue_grant(request_id=request_id,controller_key_id="attacker-key",now=103.0)
    assert signing_key.calls==2


def test_controller_key_binding_survives_authority_restart(tmp_path):
    import pytest
    from src.control.crypto_identity import KeyPair
    state_path=tmp_path/"remote-controller-authority.json"
    real_key=KeyPair.generate("durable-remote-controller-authority")
    class CountingSigningKey:
        key_id=real_key.key_id
        public_verifier=real_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return real_key.sign(data)
    signing_key=CountingSigningKey()
    request_id="request-durable-controller-key-binding"
    authority=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    authority.acquire(request_id=request_id,resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    original=authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=101.0)
    assert signing_key.calls==1
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    with pytest.raises(ValueError,match="different controller key"):
        restarted.issue_grant(request_id=request_id,controller_key_id="attacker-key",now=102.0)
    assert signing_key.calls==1
    retry=restarted.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=103.0)
    assert retry==original
    assert signing_key.calls==2


def test_failed_controller_key_binding_persistence_is_not_published(tmp_path):
    import pytest
    from src.control.crypto_identity import KeyPair
    state_path=tmp_path/"remote-controller-authority.json"
    real_key=KeyPair.generate("durable-remote-controller-authority")
    class CountingSigningKey:
        key_id=real_key.key_id
        public_verifier=real_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return real_key.sign(data)
    signing_key=CountingSigningKey()
    request_id="request-binding-storage-failure"
    authority=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    authority.acquire(request_id=request_id,resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    before=state_path.read_bytes()
    real_save=authority._save_state
    def fail_save(committed_requests):
        raise OSError("controller key binding storage unavailable")
    authority._save_state=fail_save
    with pytest.raises(OSError,match="storage unavailable"):
        authority.issue_grant(request_id=request_id,controller_key_id="uncommitted-phone-key",now=101.0)
    assert signing_key.calls==1
    assert authority._grant_key_bindings=={}
    assert state_path.read_bytes()==before
    authority._save_state=real_save
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    committed=restarted.issue_grant(request_id=request_id,controller_key_id="recovered-phone-key",now=102.0)
    assert committed.controller_key_id=="recovered-phone-key"
    assert signing_key.calls==2
    restarted_again=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    with pytest.raises(ValueError,match="different controller key"):
        restarted_again.issue_grant(request_id=request_id,controller_key_id="uncommitted-phone-key",now=103.0)
    assert signing_key.calls==2


def test_corrupted_controller_key_binding_fails_closed_without_rewriting_file(tmp_path):
    import json
    import pytest
    from src.control.crypto_identity import KeyPair
    state_path=tmp_path/"remote-controller-authority.json"
    signing_key=KeyPair.generate("durable-remote-controller-authority")
    authority=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    request_id="request-valid-binding-before-corruption"
    authority.acquire(request_id=request_id,resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    authority.issue_grant(request_id=request_id,controller_key_id="secure-phone-a-key",now=101.0)
    corrupted=json.loads(state_path.read_text(encoding="utf-8"))
    assert corrupted["version"]==2
    corrupted["grant_key_bindings"]["request-never-committed"]="attacker-key"
    state_path.write_text(json.dumps(corrupted,sort_keys=True,separators=(",",":")),encoding="utf-8")
    before=state_path.read_bytes()
    with pytest.raises(ValueError,match="invalid remote authority controller key binding"):
        IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    assert state_path.read_bytes()==before


def test_p256_protocol_result_is_persisted_and_not_resigned_after_restart(tmp_path):
    import pytest
    from dataclasses import replace
    from src.control.remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair,RemoteControllerResultDecision,RemoteControllerResultVerifier
    state_path=tmp_path/"remote-controller-authority.json"
    real_key=P256AuthorityKeyPair.generate("durable-p256-controller-authority")
    class CountingSigningKey:
        key_id=real_key.key_id
        algorithm=real_key.algorithm
        public_verifier=real_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return real_key.sign(data)
    signing_key=CountingSigningKey()
    request=AtomicControllerRequest(operation="acquire",request_id="request-p256-idempotent",resource_id="tv:living-room",controller_id="phone-a",controller_key_id="secure-phone-a-key",current_fencing_token=0,requested_ttl_seconds=30.0,challenge="server-challenge-p256")
    authority=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    authority.acquire(request_id=request.request_id,resource_id=request.resource_id,controller_id=request.controller_id,now=100.0,ttl_seconds=request.requested_ttl_seconds)
    original=authority.issue_protocol_result(request=request)
    assert signing_key.calls==1
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    with pytest.raises(ValueError,match="different protocol request"):
        restarted.issue_protocol_result(request=replace(request,challenge="attacker-challenge"))
    assert signing_key.calls==1
    retry=restarted.issue_protocol_result(request=request)
    assert retry==original
    assert retry.signature==original.signature
    assert signing_key.calls==1
    verifier=RemoteControllerResultVerifier({signing_key.key_id:signing_key.public_verifier})
    assert verifier.validate(retry,request=request,now=101.0) is RemoteControllerResultDecision.ALLOW


def test_failed_p256_protocol_result_persistence_publishes_nothing(tmp_path):
    import pytest
    from dataclasses import replace
    from src.control.remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair
    state_path=tmp_path/"remote-controller-authority.json"
    real_key=P256AuthorityKeyPair.generate("durable-p256-controller-authority")
    class CountingSigningKey:
        key_id=real_key.key_id
        algorithm=real_key.algorithm
        public_verifier=real_key.public_verifier
        calls=0
        def sign(self,data):
            self.calls+=1
            return real_key.sign(data)
    signing_key=CountingSigningKey()
    request=AtomicControllerRequest(operation="acquire",request_id="request-p256-storage-failure",resource_id="tv:living-room",controller_id="phone-a",controller_key_id="uncommitted-phone-key",current_fencing_token=0,requested_ttl_seconds=30.0,challenge="uncommitted-challenge")
    authority=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    authority.acquire(request_id=request.request_id,resource_id=request.resource_id,controller_id=request.controller_id,now=100.0,ttl_seconds=request.requested_ttl_seconds)
    before=state_path.read_bytes()
    real_save=authority._save_state
    def fail_save(committed_requests):
        raise OSError("protocol result storage unavailable")
    authority._save_state=fail_save
    with pytest.raises(OSError,match="storage unavailable"):
        authority.issue_protocol_result(request=request)
    assert signing_key.calls==1
    assert authority._protocol_results=={}
    assert authority._grant_key_bindings=={}
    assert state_path.read_bytes()==before
    authority._save_state=real_save
    recovered=replace(request,controller_key_id="recovered-phone-key",challenge="recovered-challenge")
    committed=authority.issue_protocol_result(request=recovered)
    assert committed.controller_key_id=="recovered-phone-key"
    assert signing_key.calls==2
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    assert restarted.issue_protocol_result(request=recovered)==committed
    assert signing_key.calls==2
    with pytest.raises(ValueError,match="different protocol request"):
        restarted.issue_protocol_result(request=request)
    assert signing_key.calls==2


def test_corrupted_p256_protocol_result_fails_closed_without_rewriting_state(tmp_path):
    import json
    import pytest
    from src.control.remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair
    state_path=tmp_path/"remote-controller-authority.json"
    signing_key=P256AuthorityKeyPair.generate("durable-p256-controller-authority")
    request=AtomicControllerRequest(operation="acquire",request_id="request-p256-corruption",resource_id="tv:living-room",controller_id="phone-a",controller_key_id="secure-phone-a-key",current_fencing_token=0,requested_ttl_seconds=30.0,challenge="server-challenge-corruption")
    authority=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    authority.acquire(request_id=request.request_id,resource_id=request.resource_id,controller_id=request.controller_id,now=100.0,ttl_seconds=request.requested_ttl_seconds)
    authority.issue_protocol_result(request=request)
    corrupted=json.loads(state_path.read_text(encoding="utf-8"))
    assert corrupted["version"]==3
    corrupted["protocol_results"][request.request_id]["signature"]="AAAA"
    state_path.write_text(json.dumps(corrupted,sort_keys=True,separators=(",",":")),encoding="utf-8")
    before=state_path.read_bytes()
    with pytest.raises(ValueError,match="invalid persisted remote protocol result"):
        IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    assert state_path.read_bytes()==before


def test_p256_handoff_result_advances_fence_and_is_idempotent_after_restart(tmp_path):
    from src.control.remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair,RemoteControllerResultDecision,RemoteControllerResultVerifier
    state_path=tmp_path/"remote-controller-authority.json"
    signing_key=P256AuthorityKeyPair.generate("durable-p256-controller-authority")
    authority=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    first=authority.acquire(request_id="request-acquire-phone-a",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    handoff=authority.handoff(request_id="request-handoff-phone-b",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    request=AtomicControllerRequest(operation="handoff",request_id="request-handoff-phone-b",resource_id="tv:living-room",controller_id="phone-b",controller_key_id="secure-phone-b-key",current_fencing_token=first.fencing_token,requested_ttl_seconds=30.0,challenge="server-challenge-handoff-phone-b")
    import pytest
    assert handoff.fencing_token>request.current_fencing_token
    with pytest.raises(RuntimeError,match="endpoint readiness"):
        authority.issue_protocol_result(request=request)
    restarted=IdempotentRemoteControllerAuthority(state_path=state_path,signing_key=signing_key)
    assert restarted.highest_token("tv:living-room")==handoff.fencing_token
    with pytest.raises(RuntimeError,match="endpoint readiness"):
        restarted.issue_protocol_result(request=request)


def test_handoff_result_waits_for_endpoint_readiness():
    import pytest
    from src.control.remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair
    key=P256AuthorityKeyPair.generate("readiness-test-authority")
    authority=IdempotentRemoteControllerAuthority(signing_key=key)
    first=authority.acquire(request_id="readiness-acquire",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    successor=authority.handoff(request_id="readiness-handoff",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    request=AtomicControllerRequest(operation="handoff",request_id="readiness-handoff",resource_id=first.resource_id,controller_id="phone-b",controller_key_id="phone-b-key",current_fencing_token=first.fencing_token,requested_ttl_seconds=30.0,challenge="readiness-challenge")
    assert successor.fencing_token>first.fencing_token
    with pytest.raises(RuntimeError,match="endpoint readiness"):
        authority.issue_protocol_result(request=request)


def test_handoff_grant_waits_for_endpoint_readiness():
    import pytest
    from src.control.crypto_identity import KeyPair
    authority=IdempotentRemoteControllerAuthority(signing_key=KeyPair.generate("readiness-grant-authority"))
    first=authority.acquire(request_id="grant-readiness-acquire",resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    authority.handoff(request_id="grant-readiness-handoff",current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
    with pytest.raises(RuntimeError,match="endpoint readiness"):
        authority.issue_grant(request_id="grant-readiness-handoff",controller_key_id="phone-b-key",now=102.0)
