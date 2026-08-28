import pytest
from src.device_fabric.contracts import TransactionState

@pytest.mark.asyncio
async def test_adversarial_epistemic_guarantees(hil_env, monkeypatch):
    manager, adapter, intent, lease = hil_env
    call_count = [0]
    
    # 1. Simulate adversarial physical drift post-execution
    async def observe_drifting_truth():
        call_count[0] += 1
        if call_count[0] == 1:
            return intent.expected_pre_state # Passes precondition
        return intent.expected_pre_state # Fails post-execution verification
        
    # 2. Inject critical network failure during rollback attempt
    async def catastrophic_rollback(*args, **kwargs):
        raise ConnectionError("Link severed during rollback")
        
    monkeypatch.setattr(adapter, "observe_state", observe_drifting_truth)
    monkeypatch.setattr(adapter, "rollback", catastrophic_rollback)
    
    status, err = await manager.execute_transaction(intent, lease)
    
    # 3. Assert Non-Negotiable Invariants
    assert status == TransactionState.RECOVERY_REQUIRED
    assert "CRITICAL" in err
    
    # 4. Enforce Commit Monotonicity 
    assert status != TransactionState.COMMITTED
    assert status != TransactionState.ROLLED_BACK
