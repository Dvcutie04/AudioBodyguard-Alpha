import time
from typing import Optional, Tuple
from src.device_fabric.contracts import (
    AuthorizedActionIntent,
    CapabilityLease,
    CommitCertificate,
    ContractViolation,
    DeviceState,
    PreconditionStatus,
    TransactionState,
    VerificationResult,
    VerificationStatus,
)


class PhysicalTransactionManager:
    def __init__(self, adapter, precondition_evaluator, digital_twin):
        self.adapter = adapter
        self.evaluator = precondition_evaluator
        self.twin = digital_twin
        self.state = TransactionState.PRECONDITION_CHECK

    async def execute_transaction(
        self, intent: AuthorizedActionIntent, lease: CapabilityLease
    ) -> Tuple[str, Optional[CommitCertificate]]:
        # 1. Capability Lease Check
        if intent.operation not in lease.capabilities:
            self.state = TransactionState.FAILED_CAPABILITY
            return "FAILED_CAPABILITY", None

        if lease.expires_at > 0 and time.time() > lease.expires_at:
            self.state = TransactionState.FAILED_CAPABILITY
            return "FAILED_CAPABILITY", None

        # 2. Precondition Evaluation
        self.state = TransactionState.PRECONDITION_CHECK
        observed_state = await self.adapter.observe_state()
        eval_result = self.evaluator.evaluate(observed_state, intent.expected_pre_state)

        if eval_result != PreconditionStatus.MATCH:
            self.state = TransactionState.FAILED_PRECONDITION
            return "FAILED_PRECONDITION", None

        # 3. Execution
        self.state = TransactionState.EXECUTING
        success, error = await self.adapter.apply_state(intent.target_state)
        if not success:
            self.state = TransactionState.FAILED_EXECUTION
            return "FAILED_EXECUTION", None

        self.state = TransactionState.EXECUTED

        # 4. Post-Execution Verification
        self.state = TransactionState.VERIFYING
        post_observed_state = await self.adapter.observe_state()
        post_eval_result = self.evaluator.evaluate(post_observed_state, intent.target_state)

        if post_eval_result != PreconditionStatus.MATCH:
            self.state = TransactionState.FAILED_VERIFICATION
            # Attempt Rollback
            rollback_success, _ = await self.adapter.rollback(intent.expected_pre_state)
            if rollback_success:
                self.state = TransactionState.ROLLED_BACK
            else:
                self.state = TransactionState.RECOVERY_REQUIRED

            cert = CommitCertificate(
                verification_result=VerificationResult(
                    status=VerificationStatus.FAILED_VERIFICATION,
                    details="Post-execution drift detected",
                    verified=False,
                ),
                observed_state_digest=None,
            )
            return "FAILED_VERIFICATION", cert

        # 5. Commit
        self.state = TransactionState.VERIFIED
        self.twin.update_state(intent.device_id, post_observed_state)
        self.state = TransactionState.COMMITTED

        cert = CommitCertificate(
            verification_result=VerificationResult(
                status=VerificationStatus.VERIFIED,
                details="Transaction committed successfully",
                verified=True,
            ),
            observed_state_digest=f"digest_{hash(str(post_observed_state))}",
        )
        return "COMMITTED", cert
