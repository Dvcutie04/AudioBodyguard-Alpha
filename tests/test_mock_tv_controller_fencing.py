import pytest

from src.device_fabric.contracts import ActuationStatus,AuthorizedActionIntent,DeviceState
from src.device_fabric.mocks.mock_tv import MockTVAdapter


@pytest.mark.asyncio
async def test_mock_tv_enforces_monotonic_controller_fencing_at_endpoint():
    adapter=MockTVAdapter("tv-fenced")
    token8=AuthorizedActionIntent(intent_id="intent-token-8",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=20.0),transaction_id="tx-8",capability_digest="cap-8",controller_resource_id="tv:living-room",controller_id="phone-a",controller_fencing_token=8)
    first=await adapter.execute_intent(token8)
    assert first.status is ActuationStatus.EXECUTED
    assert adapter.device.state.volume==20.0
    stale=AuthorizedActionIntent(intent_id="intent-token-7",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=99.0),transaction_id="tx-7",capability_digest="cap-7",controller_resource_id="tv:living-room",controller_id="phone-a",controller_fencing_token=7)
    stale_receipt=await adapter.execute_intent(stale)
    assert stale_receipt.status is ActuationStatus.REJECTED
    assert adapter.device.state.volume==20.0
    forged=AuthorizedActionIntent(intent_id="intent-forged-token-8",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=98.0),transaction_id="tx-forged",capability_digest="cap-forged",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=8)
    forged_receipt=await adapter.execute_intent(forged)
    assert forged_receipt.status is ActuationStatus.REJECTED
    assert adapter.device.state.volume==20.0
    token9=AuthorizedActionIntent(intent_id="intent-token-9",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=30.0),transaction_id="tx-9",capability_digest="cap-9",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=9)
    successor=await adapter.execute_intent(token9)
    assert successor.status is ActuationStatus.EXECUTED
    assert adapter.device.state.volume==30.0
    assert adapter._highest_controller_fences=={"tv:living-room":(9,"phone-b")}


@pytest.mark.asyncio
async def test_mock_tv_persists_controller_fence_across_restart(tmp_path):
    from src.device_fabric.controller_fence_store import ControllerFenceStore
    store_path=tmp_path/"controller-fences.json"
    first_adapter=MockTVAdapter("tv-fenced",fence_store=ControllerFenceStore(store_path))
    token9=AuthorizedActionIntent(intent_id="intent-before-restart-token-9",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=30.0),transaction_id="tx-before-restart",capability_digest="cap-before-restart",controller_resource_id="tv:living-room",controller_id="phone-b",controller_fencing_token=9)
    first=await first_adapter.execute_intent(token9)
    assert first.status is ActuationStatus.EXECUTED
    restarted_adapter=MockTVAdapter("tv-fenced",fence_store=ControllerFenceStore(store_path))
    stale=AuthorizedActionIntent(intent_id="intent-after-restart-token-8",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=99.0),transaction_id="tx-after-restart",capability_digest="cap-after-restart",controller_resource_id="tv:living-room",controller_id="phone-a",controller_fencing_token=8)
    rejected=await restarted_adapter.execute_intent(stale)
    assert rejected.status is ActuationStatus.REJECTED
    assert restarted_adapter.device.state.volume==10.0
    assert restarted_adapter._executed_intents==set()


@pytest.mark.asyncio
async def test_mock_tv_rejects_before_mutation_when_fence_store_fails():
    class BrokenFenceStore:
        def snapshot(self):
            return {}
        def accept(self,resource_id,controller_id,token):
            raise OSError("simulated durable-store failure")

    adapter=MockTVAdapter("tv-fenced",fence_store=BrokenFenceStore())
    intent=AuthorizedActionIntent(intent_id="intent-store-failure",device_id="tv-fenced",operation="set_volume",target_state=DeviceState(volume=99.0),transaction_id="tx-store-failure",capability_digest="cap-store-failure",controller_resource_id="tv:living-room",controller_id="phone-a",controller_fencing_token=11)
    receipt=await adapter.execute_intent(intent)
    assert receipt.status is ActuationStatus.REJECTED
    assert adapter.device.state.volume==10.0
    assert adapter._executed_intents==set()
    assert adapter._highest_controller_fences=={}
