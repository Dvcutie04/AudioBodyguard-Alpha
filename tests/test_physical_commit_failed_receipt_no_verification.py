import time
import pytest
from src.control.crypto_identity import KeyPair
from src.control.capability_lease import SignedCapabilityLease
from src.control.authorized_intent import SignedActionIntent
from src.control.intent_firewall import IntentFirewall
from src.control.device_fabric_bridge import Gen3DeviceFabricBridge
from src.device_fabric.contracts import CapabilityLease,DeviceState,PhysicalSnapshot,ActuationReceipt,ActuationStatus

@pytest.mark.asyncio
async def test_failed_receipt_never_creates_verification_record():
    class A:
        class Dev:
            class Id:
                device_id="tv_integration_node_1"
            identity=Id()
            state=DeviceState()
        device=Dev()
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="failed_receipt",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.FAILED)
    adapter=A()
    key=KeyPair.generate()
    firewall=IntentFirewall(trusted_verifiers={key.key_id:key.public_verifier})
    bridge=Gen3DeviceFabricBridge(firewall,adapter)
    now=time.time()
    ld=dict(device_id="tv_integration_node_1",capability_digest="cap_audio",firmware_identity="v1.0",protocol_version="1.0",issued_at=now,expires_at=now+60,nonce="lease_n",issuer_id=key.key_id)
    ls=key.sign(SignedCapabilityLease(**ld,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**ld,signature=ls)
    idata=dict(intent_id="failed_receipt_test",device_id="tv_integration_node_1",operation="SET_VOLUME",parameters={"volume":55.0},issuer_id=key.key_id,policy_digest="policy",capability_lease_digest=lease.payload_digest,created_at=now,expires_at=now+30,nonce="intent_n",transaction_id="tx_failed_receipt",protocol_version="1.0")
    sig=key.sign(SignedActionIntent(**idata,signature="").canonical_bytes)
    intent=SignedActionIntent(**idata,signature=sig)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre)
    assert adapter.calls==1
    assert result.status=="FAILED"
    assert result.receipt.status==ActuationStatus.FAILED
    assert result.verification is None
