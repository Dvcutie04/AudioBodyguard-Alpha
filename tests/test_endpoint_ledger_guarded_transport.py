from dataclasses import replace
from types import SimpleNamespace

import pytest

from src.device_fabric.contracts import ActuationReceipt,ActuationStatus,AuthorizedActionIntent,DeviceState
from src.device_fabric.endpoint_execution_ledger import EndpointExecutionLedger
from src.device_fabric.endpoint_ledger_guarded_transport import EndpointLedgerGuardedTransport


class Adapter:
    def __init__(self):
        self.device=SimpleNamespace(identity=SimpleNamespace(device_id="device"))
        self.calls=0

    async def execute_intent(self,intent,transaction_digest=None,capability_digest=None):
        self.calls+=1
        return ActuationReceipt(receipt_id="physical",intent_id=intent.intent_id,status=ActuationStatus.EXECUTED,device_id=intent.device_id,transaction_id=intent.transaction_id,capability_digest=intent.capability_digest)


def _intent():
    return AuthorizedActionIntent(intent_id="intent",action="set_power",operation="set_power",device_id="device",target_state=DeviceState(power=True),expected_pre_state=DeviceState(power=False),authorization_digest="auth",deadline_at=4102444800.0,transaction_id="transaction",capability_digest="capability",controller_resource_id="device",controller_id="controller",controller_fencing_token=1)


@pytest.mark.asyncio
async def test_closed_transaction_never_reaches_adapter_after_restart(tmp_path):
    path=tmp_path/"endpoint.sqlite3"
    adapter=Adapter()
    guard=EndpointLedgerGuardedTransport(adapter,EndpointExecutionLedger(path,device_id="device",enroll=True),authority_epoch=1)
    assert guard.close_if_unstarted(_intent()) is True
    restarted=EndpointLedgerGuardedTransport(adapter,EndpointExecutionLedger(path,device_id="device"),authority_epoch=1)
    with pytest.raises(ValueError,match="closed"):
        await restarted.execute_intent(_intent(),transaction_digest="transaction",capability_digest="capability")
    assert adapter.calls==0


@pytest.mark.asyncio
async def test_claim_prevents_false_closure_and_replay(tmp_path):
    path=tmp_path/"claimed.sqlite3"
    adapter=Adapter()
    guard=EndpointLedgerGuardedTransport(adapter,EndpointExecutionLedger(path,device_id="device",enroll=True),authority_epoch=1)
    assert (await guard.execute_intent(_intent(),transaction_digest="transaction",capability_digest="capability")).status is ActuationStatus.EXECUTED
    assert guard.close_if_unstarted(_intent()) is False
    with pytest.raises(ValueError,match="closed"):
        await guard.execute_intent(_intent(),transaction_digest="transaction",capability_digest="capability")
    with pytest.raises(ValueError,match="binding"):
        guard.close_if_unstarted(replace(_intent(),operation="other-operation"))
    assert adapter.calls==1


@pytest.mark.asyncio
async def test_missing_history_fails_before_adapter(tmp_path):
    path=tmp_path/"missing.sqlite3"
    adapter=Adapter()
    guard=EndpointLedgerGuardedTransport(adapter,EndpointExecutionLedger(path,device_id="device",enroll=True),authority_epoch=1)
    path.unlink()
    with pytest.raises(ValueError,match="history is missing"):
        await guard.execute_intent(_intent())
    assert adapter.calls==0
    assert not path.exists()


@pytest.mark.asyncio
async def test_configured_endpoint_verifier_rejects_missing_evidence_before_adapter(tmp_path):
    from src.device_fabric.endpoint_action_admission import EndpointActionVerifier
    adapter=Adapter()
    ledger=EndpointExecutionLedger(tmp_path/"signed-endpoint.sqlite3",device_id="device",enroll=True)
    verifier=EndpointActionVerifier(policy_verifiers={},controller_verifiers={})
    guard=EndpointLedgerGuardedTransport(adapter,ledger,authority_epoch=1,endpoint_action_verifier=verifier)
    with pytest.raises(ValueError,match="endpoint action"):
        await guard.execute_intent(_intent())
    with pytest.raises(ValueError,match="endpoint action"):
        await guard.execute_intent(_intent(),signed_intent=object(),capability_lease=object(),controller_evidence=object())
    assert adapter.calls==0
    assert guard.close_if_unstarted(_intent()) is True


@pytest.mark.asyncio
@pytest.mark.parametrize("controller_id", ("iphone-controller", "android-controller"))
async def test_verified_volume_executes_once_after_ledger_restart(tmp_path, controller_id):
    import hashlib
    import time
    from dataclasses import replace
    from src.control.capability_lease import SignedCapabilityLease
    from src.control.controller_bound_intent import ControllerBoundActionIntent
    from src.control.controller_lease_evidence import SignedControllerLeaseEvidence
    from src.control.crypto_identity import KeyPair
    from src.device_fabric.endpoint_action_admission import EndpointActionVerifier
    now=time.time()
    policy_key=KeyPair.generate("policy-"+controller_id)
    controller_key=KeyPair.generate("controller-"+controller_id)
    cap=SignedCapabilityLease(device_id="device",capability_digest="cap",firmware_identity="fw",protocol_version="AQSS-1",issued_at=now-10,expires_at=now+120,nonce="cap-nonce",issuer_id=policy_key.key_id,signature="")
    cap=replace(cap,signature=policy_key.sign(cap.canonical_bytes))
    evidence=SignedControllerLeaseEvidence(resource_id="device",controller_id=controller_id,fencing_token=1,issued_at=now-10,expires_at=now+120,issuer_id=controller_key.key_id,nonce="lease-nonce",scope=("SET_VOLUME",))
    evidence=replace(evidence,signature=controller_key.sign(evidence.canonical_bytes))
    before=DeviceState()
    signed=ControllerBoundActionIntent(intent_id="intent",device_id="device",operation="SET_VOLUME",parameters={"volume":25},issuer_id=policy_key.key_id,policy_digest="policy",capability_lease_digest=cap.payload_digest,resource_id=evidence.resource_id,controller_id=controller_id,controller_lease_digest=evidence.evidence_digest,fencing_token=1,created_at=now-1,expires_at=now+60,nonce="intent-nonce",transaction_id="transaction",protocol_version="AQSS-1",expected_pre_state_digest=before.state_digest)
    signed=replace(signed,signature=policy_key.sign(signed.canonical_bytes))
    action=AuthorizedActionIntent(intent_id=signed.intent_id,lease_id=cap.payload_digest,action="set_volume",device_id="device",operation="set_volume",target_state=DeviceState(volume=25),expected_pre_state=before,authorization_digest=hashlib.sha256(signed.canonical_bytes).hexdigest(),deadline_at=signed.expires_at,transaction_id="transaction",capability_digest=cap.payload_digest,controller_resource_id="device",controller_id=controller_id,controller_fencing_token=1)
    def verifier():
        return EndpointActionVerifier(policy_verifiers={policy_key.key_id:policy_key.public_verifier},controller_verifiers={controller_key.key_id:controller_key.public_verifier})
    path=tmp_path/"signed-volume.sqlite3"
    adapter=Adapter()
    guard=EndpointLedgerGuardedTransport(adapter,EndpointExecutionLedger(path,device_id="device",enroll=True),authority_epoch=1,endpoint_action_verifier=verifier())
    proof=dict(signed_intent=signed,capability_lease=cap,controller_evidence=evidence)
    with pytest.raises(ValueError,match="endpoint action"):
        await guard.execute_intent(replace(action,target_state=DeviceState(volume=99)),**proof)
    assert adapter.calls==0
    assert (await guard.execute_intent(action,**proof)).status is ActuationStatus.EXECUTED
    assert adapter.calls==1
    restarted=EndpointLedgerGuardedTransport(adapter,EndpointExecutionLedger(path,device_id="device"),authority_epoch=1,endpoint_action_verifier=verifier())
    with pytest.raises(ValueError,match="closed"):
        await restarted.execute_intent(action,**proof)
    assert adapter.calls==1
