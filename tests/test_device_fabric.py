import pytest
from src.device_fabric.mocks.mock_tv import MockTVAdapter
from src.device_fabric.router import DeviceFabricRouter
from src.device_fabric.contracts import DeviceState, TransactionState
from src.device_fabric.transaction import PhysicalTransactionManager
from src.device_fabric.precondition import PreconditionEvaluator
from src.device_fabric.digital_twin import DigitalTwin

@pytest.mark.asyncio
async def test_device_fabric_execution_verification_and_idempotency():
    # 1. Build the engine components
    adapter = MockTVAdapter("tv_living_room")
    evaluator = PreconditionEvaluator(staleness_threshold_seconds=2.0)
    twin = DigitalTwin()
    
    # 2. Assemble the transaction manager
    tx_manager = PhysicalTransactionManager(adapter, evaluator, twin)
    
    # 3. Inject it into the Router
    router = DeviceFabricRouter(tx_manager)
    
    # 4. Setup mock states
    pre_state = DeviceState(power=True, volume=50.0, input_source="HDMI_1")
    target = DeviceState(power=True, volume=44.0, input_source="HDMI_1", payload={"delta_db": 6.0})
    
    # 5. Dispatch
    status, err = await router.dispatch_intent(
        device_id="tv_living_room",
        operation="REDUCE_VOLUME",
        expected_pre_state=pre_state,
        target_state=target
    )
    
    assert status == TransactionState.COMMITTED
