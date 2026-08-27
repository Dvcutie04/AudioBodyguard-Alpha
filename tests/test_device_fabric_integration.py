import pytest
from src.device_fabric.contracts import DeviceState, ActuationStatus
from src.device_fabric.mocks.mock_tv import MockTVAdapter
from src.device_fabric.router import DeviceFabricRouter


@pytest.mark.asyncio
async def test_successful_volume_reduction_flow():
    router = DeviceFabricRouter()
    tv = MockTVAdapter("living_room_tv")
    router.register_device("living_room_tv", tv)

    # Initial state: volume=50.0
    expected_state = DeviceState(power=True, volume=40.0, muted=False, input_source="HDMI_1")

    receipt, verification = await router.dispatch_and_verify(
        device_id="living_room_tv",
        action_id="act_vol_down_01",
        intent_digest="intent_sha256_001",
        command="REDUCE_VOLUME",
        payload={"delta_db": 10.0},
        expected_target_state=expected_state,
    )

    assert receipt.status == ActuationStatus.EXECUTED.value
    assert verification.verified is True
    assert tv.state.volume == 40.0


@pytest.mark.asyncio
async def test_idempotent_duplicate_submission():
    router = DeviceFabricRouter()
    tv = MockTVAdapter("living_room_tv")
    router.register_device("living_room_tv", tv)

    expected_state = DeviceState(power=True, volume=40.0, muted=False, input_source="HDMI_1")

    # First execution
    await router.dispatch_and_verify(
        device_id="living_room_tv",
        action_id="act_vol_down_02",
        intent_digest="intent_sha256_002",
        command="REDUCE_VOLUME",
        payload={"delta_db": 10.0},
        expected_target_state=expected_state,
    )

    # Duplicate submission with identical action_id and intent_digest
    dup_receipt, dup_verification = await router.dispatch_and_verify(
        device_id="living_room_tv",
        action_id="act_vol_down_02",
        intent_digest="intent_sha256_002",
        command="REDUCE_VOLUME",
        payload={"delta_db": 10.0},
        expected_target_state=expected_state,
    )

    assert dup_receipt.status == ActuationStatus.DUPLICATE_ABSORBED.value
    assert dup_verification.verified is True
    # Ensure volume was not reduced a second time (should remain 40.0, not 30.0)
    assert tv.state.volume == 40.0


@pytest.mark.asyncio
async def test_fault_injection_and_automatic_rollback():
    router = DeviceFabricRouter()
    tv = MockTVAdapter("living_room_tv")
    router.register_device("living_room_tv", tv)

    # State before execution is volume=50.0
    pre_vol = tv.state.volume

    expected_state = DeviceState(power=True, volume=40.0, muted=False, input_source="HDMI_1")

    # Forcefully inject a hardware fault so observed state differs from expected state
    tv.inject_fault_state(power=True, volume=99.0, muted=False)

    receipt, verification = await router.dispatch_and_verify(
        device_id="living_room_tv",
        action_id="act_fault_01",
        intent_digest="intent_sha256_003",
        command="REDUCE_VOLUME",
        payload={"delta_db": 10.0},
        expected_target_state=expected_state,
    )

    # Verification fails due to injected hardware fault
    assert verification.verified is False
    # Router automatically executes rollback back to pre-state observation
    assert tv.state.volume == pre_vol
