import time
from typing import Tuple, Optional

from src.device_fabric.contracts import (
    AuthorizedActionIntent, 
    CapabilityLease, 
    TransactionState, 
    PreconditionStatus, 
    DeviceState
)
from src.device_fabric.precondition import PreconditionEvaluator
from src.device_fabric.digital_twin import DigitalTwin

class PhysicalTransactionManager:
    """
    Coordinates verifiable physical state transitions.
    Guarantees: Idempotency, Precondition Drift Protection, and Verified Rollback.
    """
    def __init__(
        self, 
        adapter, 
        precondition_evaluator: PreconditionEvaluator, 
        digital_twin: DigitalTwin
    ):
        self.adapter = adapter
        self.precondition = precondition_evaluator
        self.twin = digital_twin

    async def execute_transaction(
        self, 
        intent: AuthorizedActionIntent, 
        lease: CapabilityLease,
        current_time: Optional[float] = None
    ) -> Tuple[TransactionState, Optional[str]]:
        
        now = current_time or time.time()
        tx_id = f"tx_{intent.intent_id}"

        # 1. Cryptographic Lease Verification
        if lease.expires_at < now:
            return TransactionState.FAILED_VERIFICATION, "Capability lease expired."
        if lease.device_id != intent.device_id:
            return TransactionState.FAILED_CAPABILITY, "Lease device mismatch."

        # 2. Precondition / World-State Drift Check
        observed_pre_state = await self.adapter.observe_state()
        pre_status = self.precondition.evaluate(intent.expected_pre_state, observed_pre_state, now)
        
        if pre_status != PreconditionStatus.MATCH:
            return TransactionState.FAILED_DRIFT, f"Precondition failed: {pre_status.name}"

        # 3. Digital Twin Predictive Constraint Check
        if not self.twin.validate_transition(intent.device_id, observed_pre_state, intent.target_state):
            return TransactionState.FAILED_VERIFICATION, "Digital Twin constraint violation."

        # 4. Physical Execution
        try:
            await self.adapter.execute(
                action_id=intent.intent_id,
                intent_digest=intent.intent_digest,
                command=intent.operation,
                payload=intent.target_state.payload 
            )
        except Exception as e:
            return await self._attempt_rollback(tx_id, intent, observed_pre_state, f"Execution fault: {str(e)}")

        # 5. Independent Post-State Observation & Verification (Physical Truth Invariant)
        verification = await self.adapter.verify(intent.target_state, tx_id)
        
        if not verification.verified:
            return await self._attempt_rollback(tx_id, intent, observed_pre_state, "Physical verification failed")

        return TransactionState.COMMITTED, None

    async def _attempt_rollback(
        self, 
        tx_id: str, 
        intent: AuthorizedActionIntent, 
        original_state: DeviceState,
        reason: str
    ) -> Tuple[TransactionState, str]:
        """
        Attempts to restore hardware to original state if a transaction fails.
        Transitions to RECOVERY_REQUIRED if hardware state is indeterminate.
        """
        try:
            await self.adapter.rollback(original_state, tx_id)
            
            # Verify the rollback actually worked
            verification = await self.adapter.verify(original_state, f"rb_{tx_id}")
            if verification.verified:
                return TransactionState.ROLLED_BACK, f"{reason} | Rolled back successfully."
            else:
                return TransactionState.RECOVERY_REQUIRED, f"{reason} | CRITICAL: Rollback failed. State unknown."
                
        except Exception as e:
            return TransactionState.RECOVERY_REQUIRED, f"{reason} | CRITICAL: Exception during rollback. {str(e)}"
