import math
from inspect import iscoroutinefunction
from src.control.active_controller_lease import ControllerLeaseDecision
from src.device_fabric.precondition_gate import PreconditionGate, PreconditionResult
from src.device_fabric.transport import PhysicalTransport, dispatch_physical_transport

class PhysicalCommitGate:
    def __init__(self, precondition_gate=None, *, adaptive_memory=None, directive_proposal=None, controller_authority=None, controller_lease=None, controller_now=None, transport_timeout_seconds=2.0):
        self.precondition_gate = precondition_gate or PreconditionGate()
        self.adaptive_memory = adaptive_memory
        self.directive_proposal = directive_proposal
        self.controller_authority = controller_authority
        self.controller_lease = controller_lease
        self.controller_now = controller_now
        self.transport_timeout_seconds = transport_timeout_seconds

    async def commit(self, intent, lease, snapshot, adapter: PhysicalTransport):
        result = self.precondition_gate.evaluate(intent, lease, snapshot)
        if result != PreconditionResult.ALLOW:
            return result
        if self.controller_authority is not None or self.controller_lease is not None or self.controller_now is not None:
            try:
                current = self.controller_authority is not None and self.controller_lease is not None and self.controller_now is not None and self.controller_authority.validate(self.controller_lease, now=self.controller_now) is ControllerLeaseDecision.ALLOW
            except Exception:
                return PreconditionResult.CONTROLLER_FENCE_STALE
            if current is not True:
                return PreconditionResult.CONTROLLER_FENCE_STALE
        if self.adaptive_memory is not None or self.directive_proposal is not None:
            try:
                current = self.adaptive_memory is not None and self.directive_proposal is not None and self.adaptive_memory.proposal_is_current(self.directive_proposal)
            except Exception:
                return PreconditionResult.ADAPTIVE_PROPOSAL_INVALID
            if current is not True:
                return PreconditionResult.ADAPTIVE_PROPOSAL_INVALID
            try:
                proposal_key = self.directive_proposal.key
                if type(proposal_key) is not tuple or len(proposal_key) != 4 or any(type(part) is not str or not part.strip() for part in proposal_key):
                    return PreconditionResult.ADAPTIVE_PROPOSAL_INVALID
                if proposal_key[1] != intent.device_id:
                    return PreconditionResult.DEVICE_MISMATCH
                if self.directive_proposal.action != "lower_volume" or intent.operation != "set_volume":
                    return PreconditionResult.ADAPTIVE_ACTION_MISMATCH
                before = intent.expected_pre_state.volume
                after = intent.target_state.volume
                if type(before) not in (int, float) or type(after) not in (int, float):
                    return PreconditionResult.ADAPTIVE_ACTION_MISMATCH
                if not math.isfinite(before) or not math.isfinite(after) or not after < before:
                    return PreconditionResult.ADAPTIVE_ACTION_MISMATCH
            except Exception:
                return PreconditionResult.ADAPTIVE_PROPOSAL_INVALID
        if adapter is None or not isinstance(adapter,PhysicalTransport):
            raise ValueError("Device Fabric adapter with execute_intent() is required")
        if not iscoroutinefunction(adapter.execute_intent):
            raise ValueError("Device Fabric adapter must implement asynchronous PhysicalTransport")
        return await dispatch_physical_transport(
            transport=adapter,
            intent=intent,
            transaction_digest=intent.transaction_id,
            capability_digest=intent.capability_digest,
            timeout_seconds=self.transport_timeout_seconds,
        )
