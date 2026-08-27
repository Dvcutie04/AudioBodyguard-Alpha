from typing import Dict, Tuple
from src.device_fabric.adapter import DeviceAdapter
from src.device_fabric.contracts import (
    ActuationReceipt,
    VerificationResult,
    DeviceState,
)


class DeviceFabricRouter:
    def __init__(self):
        self._registry: Dict[str, DeviceAdapter] = {}

    def register_device(self, device_id: str, adapter: DeviceAdapter) -> None:
        self._registry[device_id] = adapter

    async def dispatch_and_verify(
        self,
        device_id: str,
        action_id: str,
        intent_digest: str,
        command: str,
        payload: dict,
        expected_target_state: DeviceState,
    ) -> Tuple[ActuationReceipt, VerificationResult]:
        adapter = self._registry.get(device_id)
        if not adapter:
            raise ValueError(f"No adapter registered for device: {device_id}")

        receipt = await adapter.execute(action_id, intent_digest, command, payload)
        if receipt.status != "EXECUTED":
            observed = await adapter.observe_state()
            return receipt, VerificationResult(
                verified=False,
                expected_state=expected_target_state,
                observed_state=observed,
                error_message=f"Execution failed with status: {receipt.status}",
            )

        verification = await adapter.verify(expected_target_state)
        return receipt, verification
