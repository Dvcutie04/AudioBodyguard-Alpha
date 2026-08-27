import time
from typing import Dict, Tuple
from src.device_fabric.adapter import DeviceAdapter
from src.device_fabric.contracts import (
    ActuationReceipt,
    ActuationStatus,
    DeviceCapabilities,
    DeviceState,
    TransactionIdentity,
    VerificationResult,
)


class DeviceFabricRouter:
    def __init__(self):
        self._registry: Dict[str, DeviceAdapter] = {}
        self._fabric_sequence = 0
        self._transaction_history: Dict[str, ActuationReceipt] = {}

    def register_device(self, device_id: str, adapter: DeviceAdapter) -> None:
        """Register a device adapter instance."""
        self._registry[device_id] = adapter

    def _next_sequence(self) -> int:
        self._fabric_sequence += 1
        return self._fabric_sequence

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

        tx_identity = TransactionIdentity(
            action_id=action_id,
            device_id=device_id,
            intent_digest=intent_digest,
        )
        tx_digest = tx_identity.transaction_digest

        # Handle Idempotency Absorption
        if tx_digest in self._transaction_history:
            cached_receipt = self._transaction_history[tx_digest]
            dup_receipt = ActuationReceipt(
                receipt_id=f"dup_{cached_receipt.receipt_id}",
                action_id=action_id,
                device_id=device_id,
                intent_digest=intent_digest,
                status=ActuationStatus.DUPLICATE_ABSORBED.value,
                timestamp=time.time(),
                transaction_digest=tx_digest,
                capability_digest=cached_receipt.capability_digest,
                pre_state_digest=cached_receipt.pre_state_digest,
                post_state_digest=cached_receipt.post_state_digest,
                fabric_sequence=self._next_sequence(),
            )
            current_obs = await adapter.observe_state()
            v_res = VerificationResult(
                verified=True,
                expected_state=expected_target_state,
                observed_state=current_obs,
                transaction_digest=tx_digest,
            )
            return dup_receipt, v_res

        # 1. Capability Snapshot
        caps: DeviceCapabilities = await adapter.capabilities()
        cap_digest = caps.capability_digest

        # 2. Pre-State Snapshot
        pre_state: DeviceState = await adapter.observe_state()
        pre_digest = pre_state.state_digest

        # 3. Execution
        receipt = await adapter.execute(action_id, intent_digest, command, payload)

        if receipt.status == ActuationStatus.DUPLICATE_ABSORBED.value:
            v_res = VerificationResult(
                verified=True,
                expected_state=expected_target_state,
                observed_state=pre_state,
                transaction_digest=tx_digest,
            )
            return receipt, v_res

        if receipt.status != ActuationStatus.EXECUTED.value:
            observed = await adapter.observe_state()
            return receipt, VerificationResult(
                verified=False,
                expected_state=expected_target_state,
                observed_state=observed,
                error_message=f"Execution failed with status: {receipt.status}",
                transaction_digest=tx_digest,
            )

        # 4. Hardware Verification
        verification: VerificationResult = await adapter.verify(
            expected_target_state, transaction_digest=tx_digest
        )

        # 5. Rollback on Mismatch
        if not verification.verified:
            await adapter.rollback(
                target_pre_state=pre_state,
                lineage_digest=tx_digest,
            )
            # Update verification to reflect post-rollback state
            verification.observed_state = await adapter.observe_state()

        self._transaction_history[tx_digest] = receipt
        return receipt, verification
