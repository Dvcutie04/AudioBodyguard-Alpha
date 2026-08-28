@pytest.mark.asyncio
async def test_hil_adversarial_catastrophic_recovery_required(hil_env, monkeypatch):
    manager, adapter, intent, lease = hil_env
    
    # Track state to distinguish pre- vs post-execution observation
    call_count = [0]
    
    async def observe_broken():
        call_count[0] += 1
        if call_count[0] == 1:
            # First call (precondition check): Return expected state so we pass the drift check
            return DeviceState(power=True, volume=50.0, input_source="HDMI_1")
        else:
            # Subsequent calls (verification check): Return wrong state to force a rollback
            return DeviceState(power=True, volume=99.0, input_source="UNKNOWN")
    
    # Network dies on rollback
    async def dead_rollback(*args, **kwargs):
        raise ConnectionError("Host Unreachable")
    
    monkeypatch.setattr(adapter, "observe_state", observe_broken)
    monkeypatch.setattr(adapter, "rollback", dead_rollback)
    
    status, err = await manager.execute_transaction(intent, lease)
    
    # The ultimate invariant check: If we don't know the physical state, we halt.
    assert status == TransactionState.RECOVERY_REQUIRED
    assert "CRITICAL" in err
