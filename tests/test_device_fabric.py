import pytest
from src.device_fabric.mocks.mock_tv import MockTVAdapter
from src.device_fabric.router import DeviceFabricRouter
from src.device_fabric.contracts import DeviceState


@pytest.mark.asyncio
async def test_device_fabric_execution_verification_and_idempotency():
    adapter = MockTVAdapter("tv_living_room")
    router = DeviceFabricRouter()
    router.register_device("tv_living_room", adapter)

    expected_state = DeviceState(power=True, volume=44.0, muted=False)

    # 1. Execute & Verify
    receipt, verification = await router.dispatch_and_verify(
        device_id="tv_living_room",
        action_id="act_001",
        intent_digest="sha256_digest_abc",
        command="REDUCE_VOLUME",
        payload={"delta_db": 6.0},
        expected_target_state=expected_state,
    )

    assert receipt.status == "EXECUTED"
    assert verification.verified is True
    assert verification.observed_state.volume == 44.0

    # 2. Idempotency absorb check
    dup_receipt = await adapter.execute("act_001", "sha256_digest_abc", "REDUCE_VOLUME", {"delta_db": 6.0})
    assert dup_receipt.status == "DUPLICATE_ABSORBED"
    assert adapter.state.volume == 44.0  # State remains unchanged
