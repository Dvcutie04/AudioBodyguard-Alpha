import time
import pytest
from src.device_fabric.physical_commit_gate import PhysicalCommitGate
from src.device_fabric.precondition_gate import PreconditionResult
from src.device_fabric.contracts import AuthorizedActionIntent, CapabilityLease, DeviceState, PhysicalSnapshot

@pytest.mark.asyncio
async def test_intent_expired_never_reaches_adapter():
    class A:
        calls=0
        async def execute_intent(self,*args,**kwargs):
            self.calls+=1
            raise AssertionError("adapter must not be called")
    a=A()
    pre=DeviceState()
    physical=CapabilityLease(device_id="tv_integration_node_1",capabilities={"set_volume"},authorized_epoch=0)
    snapshot=PhysicalSnapshot(device_id="tv_integration_node_1",state=pre,epoch=0,observed_at=time.time())
    authorized=AuthorizedActionIntent(intent_id="expiry_test",lease_id="lease_test",action="set_volume",device_id="tv_integration_node_1",operation="set_volume",target_state=DeviceState(volume=55.0),expected_pre_state=pre,authorization_digest="test-auth-digest",deadline_at=time.time()-1.0)
    result=await PhysicalCommitGate().commit(authorized,physical,snapshot,a)
    assert result==PreconditionResult.INTENT_EXPIRED
    assert a.calls==0
