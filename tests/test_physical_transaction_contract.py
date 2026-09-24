from src.device_fabric.contracts import ActuationStatus

def test_transaction_has_stable_identity_and_terminal_states():
    assert ActuationStatus.PENDING.name == "PENDING"
    assert ActuationStatus.EXECUTING.name == "EXECUTING"
    assert ActuationStatus.EXECUTED.name == "EXECUTED"
    assert ActuationStatus.COMMITTED.name == "COMMITTED"
    assert ActuationStatus.REJECTED.name == "REJECTED"
    assert ActuationStatus.FAILED.name == "FAILED"

def test_transaction_lifecycle_is_prepare_then_commit():
    lifecycle=(ActuationStatus.PENDING, ActuationStatus.EXECUTING, ActuationStatus.EXECUTED, ActuationStatus.COMMITTED)
    assert lifecycle[0] == ActuationStatus.PENDING
    assert lifecycle[-1] == ActuationStatus.COMMITTED

def test_rejection_is_terminal_and_distinct_from_execution():
    assert ActuationStatus.REJECTED != ActuationStatus.EXECUTED
    assert ActuationStatus.REJECTED != ActuationStatus.COMMITTED

def test_failure_is_terminal_and_distinct_from_commit():
    assert ActuationStatus.FAILED != ActuationStatus.COMMITTED
