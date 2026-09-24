import time
import pytest
from src.control.crypto_identity import KeyPair
from src.control.capability_lease import SignedCapabilityLease
from src.control.authorized_intent import SignedActionIntent
from src.control.intent_firewall import IntentFirewall
from src.control.device_fabric_bridge import Gen3DeviceFabricBridge
from src.device_fabric.mocks.mock_tv import MockTVAdapter
from src.device_fabric.contracts import CapabilityLease,PhysicalSnapshot,VerificationStatus

@pytest.mark.asyncio
async def test_verified_record_exactly_binds_intent_and_lease_lineage():
    adapter=MockTVAdapter("tv_integration_node_1")
    key=KeyPair.generate()
    firewall=IntentFirewall(trusted_verifiers={key.key_id:key.public_verifier})
    bridge=Gen3DeviceFabricBridge(firewall,adapter)
    now=time.time()
    ld=dict(device_id="tv_integration_node_1",capability_digest="cap_audio",firmware_identity="v1.0",protocol_version="1.0",issued_at=now,expires_at=now+60,nonce="lease_lineage",issuer_id=key.key_id)
    ls=key.sign(SignedCapabilityLease(**ld,signature="").canonical_bytes)
    lease=SignedCapabilityLease(**ld,signature=ls)
    idata=dict(intent_id="verification_lineage_exact",device_id="tv_integration_node_1",operation="SET_VOLUME",parameters={"volume":55.0},issuer_id=key.key_id,policy_digest="policy_lineage",capability_lease_digest=lease.payload_digest,created_at=now,expires_at=now+30,nonce="intent_lineage",transaction_id="tx_verification_lineage_exact",protocol_version="1.0")
    sig=key.sign(SignedActionIntent(**idata,signature="").canonical_bytes)
    intent=SignedActionIntent(**idata,signature=sig)
    pre=adapter.device.state
    physical=CapabilityLease(device_id=intent.device_id,capabilities={intent.operation.lower()},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id=intent.device_id,state=pre,epoch=0,observed_at=time.time())
    expected=bridge._translate_state(intent,pre)
    async def observer(device_id):
        return PhysicalSnapshot(device_id=device_id,state=expected,epoch=1,observed_at=time.time())
    result=await bridge.authorize_and_commit(intent,lease,physical,snapshot,pre,post_state_observer=observer)
    assert result.status=="EXECUTED"
    assert result.verification is not None
    assert result.verification.verification_status==VerificationStatus.VERIFIED
    assert result.verification.intent_id==intent.intent_id
    assert result.verification.transaction_id==intent.transaction_id
    assert result.verification.capability_digest==lease.payload_digest
    assert result.verification.authorization_digest==bridge._authorization_digest(intent)
    assert result.verification.authorization_digest==result.authorization_digest
