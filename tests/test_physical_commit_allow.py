import time
import pytest
from src.device_fabric.physical_commit_gate import PhysicalCommitGate
from src.device_fabric.contracts import AuthorizedActionIntent, CapabilityLease, DeviceState, PhysicalSnapshot, ActuationReceipt, ActuationStatus

@pytest.mark.asyncio
async def test_allow_reaches_adapter_exactly_once():
    class A:
        calls=0
        async def execute_intent(self,intent,*args,**kwargs):
            self.calls+=1
            return ActuationReceipt(receipt_id="allow_receipt",intent_id=intent.intent_id,device_id=intent.device_id,status=ActuationStatus.EXECUTED)
    a=A()
    pre=DeviceState()
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    authorized=AuthorizedActionIntent(intent_id="allow_test",lease_id="lease_test",action="set_volume",device_id="tv_integration_node_1",operation="set_volume",target_state=DeviceState(volume=55.0),expected_pre_state=pre,authorization_digest="test-auth-digest",deadline_at=time.time()+30.0)
    result=await PhysicalCommitGate().commit(authorized,physical,snapshot,a)
    assert a.calls==1
    assert result.status==ActuationStatus.EXECUTED
    assert result.intent_id=="allow_test"
    assert result.device_id=="tv_integration_node_1"
