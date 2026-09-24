def test_execution_claim_and_finality_are_mutually_exclusive_after_restart(tmp_path):
    import pytest
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    path=tmp_path/"finality-claims.sqlite3"
    first=EndpointTransactionFinalityStore(path)
    second=EndpointTransactionFinalityStore(path)
    first.record_not_applied("tx-closed",device_id="device-a")
    assert second.claim_execution("tx-closed",device_id="device-a") is False
    assert first.claim_execution("tx-claimed",device_id="device-a") is True
    reopened=EndpointTransactionFinalityStore(path)
    assert reopened.claim_execution("tx-claimed",device_id="device-a") is False
    assert reopened.permits_execution("tx-claimed",device_id="device-a") is False
    with pytest.raises(ValueError,match="execution already claimed"):
        second.record_not_applied("tx-claimed",device_id="device-a")
    assert reopened.permits_execution("tx-claimed",device_id="device-a") is False
    assert reopened.claim_execution("tx-claimed",device_id="device-b") is True


def test_verified_finality_is_committed_atomically_and_survives_restart(tmp_path):
    from dataclasses import replace
    import pytest
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec,utils
    from src.device_fabric.endpoint_transaction_finality_authority import EndpointFinalityTrustedKey,EndpointFinalityAuthoritySnapshot
    from src.device_fabric.endpoint_transaction_finality_commitment import encode_endpoint_finality_cose_sign1,encode_endpoint_finality_signing_input
    from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    key=ec.derive_private_key(1,ec.SECP256R1())
    trusted=EndpointFinalityTrustedKey(kid=b"k",namespace=b"n",issuer_id="i",audience="a",device_id="d",authority_epoch=1,public_key=key.public_key())
    authority=EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=(trusted,))
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    def signed(current):
        payload=encode_endpoint_finality_signing_input(claims=current,kid=b"k",namespace=b"n")
        r,s=utils.decode_dss_signature(key.sign(payload,ec.ECDSA(hashes.SHA256())))
        return encode_endpoint_finality_cose_sign1(claims=current,kid=b"k",signature=r.to_bytes(32,"big")+s.to_bytes(32,"big"))
    context=dict(device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,audience="a",issuer_id="i",authority_epoch=1)
    path=tmp_path/"verified-finality.sqlite3"
    store=EndpointTransactionFinalityStore(path,trusted_authority=authority,clock=lambda:1)
    with pytest.raises(ValueError,match="verified proof required"):
        store.record_not_applied("forged",device_id="d")
    with pytest.raises(ValueError,match="trusted authority"):
        EndpointTransactionFinalityStore(path)
    changed_key=replace(trusted,public_key=ec.derive_private_key(2,ec.SECP256R1()).public_key())
    with pytest.raises(ValueError,match="authority binding"):
        EndpointTransactionFinalityStore(path,trusted_authority=EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=(changed_key,)),clock=lambda:1)
    changed_epoch=replace(trusted,authority_epoch=2)
    with pytest.raises(ValueError,match="authority binding"):
        EndpointTransactionFinalityStore(path,trusted_authority=EndpointFinalityAuthoritySnapshot(active_authority_epoch=2,keys=(changed_epoch,)),clock=lambda:1)
    legacy_path=tmp_path/"legacy-upgrade.sqlite3"
    legacy_store=EndpointTransactionFinalityStore(legacy_path)
    legacy_store.record_not_applied("legacy",device_id="d")
    with pytest.raises(ValueError,match="legacy"):
        EndpointTransactionFinalityStore(legacy_path,trusted_authority=authority,clock=lambda:1)
    wire=signed(claims)
    accepted=store.record_verified_not_applied(wire,**context)
    assert accepted.accepted_result.claims==claims
    assert store.permits_execution("t",device_id="d") is False
    restarted=EndpointTransactionFinalityStore(path,trusted_authority=authority,clock=lambda:1)
    assert restarted.record_verified_not_applied(wire,**context).proof_digest==accepted.proof_digest
    assert restarted.claim_execution("t",device_id="d") is False
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute("DELETE FROM not_applied_transactions WHERE device_id=? AND transaction_id=?",("d","t"))
    assert restarted.permits_execution("t",device_id="d") is False
    assert restarted.claim_execution("t",device_id="d") is False
    with pytest.raises(ValueError,match="history"):
        restarted.record_verified_not_applied(wire,**context)
    fresh=EndpointTransactionFinalityStore(tmp_path/"invalid-finality.sqlite3",trusted_authority=authority,clock=lambda:1)
    with pytest.raises(ValueError):
        fresh.record_verified_not_applied(wire[:-1]+bytes([wire[-1]^1]),**context)
    assert fresh.permits_execution("t",device_id="d") is True
    assert fresh.claim_execution("claimed",device_id="d") is True
    with pytest.raises(ValueError):
        fresh.record_verified_not_applied(signed(replace(claims,transaction_id="claimed",proof_id="other")),**{**context,"transaction_id":"claimed"})
    assert fresh.permits_execution("claimed",device_id="d") is False
    # FINALITY_V2_PRODUCTION_PROOF_TEST
    v2=replace(claims,profile_version=2,proof_id="p-v2",transaction_id="t-v2",request_digest="request-one")
    v2_context={**context,"transaction_id":"t-v2"}
    v2_path=tmp_path/"v2-finality.sqlite3"
    enrolled_v2=EndpointTransactionFinalityStore(v2_path,trusted_authority=authority,clock=lambda:1,minimum_profile_version=2)
    with pytest.raises(ValueError,match="profile policy"):
        EndpointTransactionFinalityStore(v2_path,trusted_authority=authority,clock=lambda:1)
    with pytest.raises(ValueError,match="request_digest"):
        enrolled_v2.record_verified_not_applied(wire,**context)
    production=EndpointTransactionFinalityStore(v2_path,trusted_authority=authority,clock=lambda:1,require_existing=True,minimum_profile_version=2)
    with pytest.raises(ValueError,match="request_digest"):
        production.record_verified_not_applied(signed(v2),**v2_context)
    with pytest.raises(ValueError,match="request_digest mismatch"):
        production.record_verified_not_applied(signed(v2),request_digest="wrong",**v2_context)
    with pytest.raises(ValueError,match="request_digest"):
        production.record_verified_not_applied(wire,request_digest="request-one",**context)
    accepted_v2=production.record_verified_not_applied(signed(v2),request_digest="request-one",**v2_context)
    assert accepted_v2.accepted_result.claims==v2
    assert production.permits_execution("t-v2",device_id="d") is False
    restarted_v2=EndpointTransactionFinalityStore(v2_path,trusted_authority=authority,clock=lambda:1,require_existing=True,minimum_profile_version=2)
    assert restarted_v2.claim_execution("t-v2",device_id="d") is False


def test_existing_finality_history_cannot_be_silently_recreated(tmp_path):
    import pytest
    from cryptography.hazmat.primitives.asymmetric import ec
    from src.device_fabric.endpoint_transaction_finality_authority import EndpointFinalityTrustedKey,EndpointFinalityAuthoritySnapshot
    from src.device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    key=EndpointFinalityTrustedKey(kid=b"k",namespace=b"n",issuer_id="i",audience="a",device_id="d",authority_epoch=1,public_key=ec.derive_private_key(1,ec.SECP256R1()).public_key())
    authority=EndpointFinalityAuthoritySnapshot(active_authority_epoch=1,keys=(key,))
    path=tmp_path/"history.sqlite3"
    enrolled=EndpointTransactionFinalityStore(path,trusted_authority=authority)
    assert enrolled.claim_execution("t",device_id="d") is True
    opened=EndpointTransactionFinalityStore(path,trusted_authority=authority,require_existing=True)
    assert opened.claim_execution("t",device_id="d") is False
    path.unlink()
    with pytest.raises(ValueError,match="history is missing"):
        EndpointTransactionFinalityStore(path,trusted_authority=authority,require_existing=True)
    assert not path.exists()
