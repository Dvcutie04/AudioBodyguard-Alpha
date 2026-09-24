import pytest

from src.device_fabric.endpoint_execution_ledger import EndpointExecutionLedger


def _context():
    return dict(intent_id="intent",request_digest="request-digest",capability_digest="capability-digest",authorization_digest="authorization-digest",controller_id="controller",controller_fencing_token=1,authority_epoch=1)


def test_durable_closure_blocks_late_dispatch_after_restart(tmp_path):
    path=tmp_path/"endpoint-ledger.sqlite3"
    ledger=EndpointExecutionLedger(path,device_id="device",enroll=True)
    context=_context()
    assert ledger.close_if_unstarted("transaction",**context) is True
    assert ledger.close_if_unstarted("transaction",**context) is True
    restarted=EndpointExecutionLedger(path,device_id="device")
    class Adapter:
        calls=0
        def invoke(self):
            self.calls+=1
    adapter=Adapter()
    if restarted.claim_execution("transaction",**context):
        adapter.invoke()
    assert adapter.calls==0
    with pytest.raises(ValueError,match="binding"):
        restarted.close_if_unstarted("transaction",**{**context,"request_digest":"different-request"})


def test_execution_claim_prevents_false_closure_and_redispatch(tmp_path):
    path=tmp_path/"claimed-ledger.sqlite3"
    ledger=EndpointExecutionLedger(path,device_id="device",enroll=True)
    context=_context()
    assert ledger.claim_execution("transaction",**context) is True
    restarted=EndpointExecutionLedger(path,device_id="device")
    assert restarted.close_if_unstarted("transaction",**context) is False
    assert restarted.claim_execution("transaction",**context) is False


def test_concurrent_claim_and_closure_have_one_winner(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    context=_context()
    for attempt in range(8):
        path=tmp_path/("race-"+str(attempt)+".sqlite3")
        claimant=EndpointExecutionLedger(path,device_id="device",enroll=True)
        closer=EndpointExecutionLedger(path,device_id="device")
        gate=Barrier(2)
        def claim():
            gate.wait()
            return claimant.claim_execution("transaction",**context)
        def close():
            gate.wait()
            return closer.close_if_unstarted("transaction",**context)
        with ThreadPoolExecutor(max_workers=2) as workers:
            claim_future=workers.submit(claim)
            close_future=workers.submit(close)
            claim_won=claim_future.result()
            close_won=close_future.result()
        assert (claim_won,close_won) in ((True,False),(False,True))
        restarted=EndpointExecutionLedger(path,device_id="device")
        assert restarted.claim_execution("transaction",**context) is False
        assert restarted.close_if_unstarted("transaction",**context) is close_won


def test_missing_history_stops_endpoint_decisions(tmp_path):
    path=tmp_path/"missing-history.sqlite3"
    ledger=EndpointExecutionLedger(path,device_id="device",enroll=True)
    assert ledger.claim_execution("transaction",**_context()) is True
    path.unlink()
    with pytest.raises(ValueError,match="history is missing"):
        ledger.close_if_unstarted("other-transaction",**_context())
    with pytest.raises(ValueError,match="history is missing"):
        EndpointExecutionLedger(path,device_id="device")
    assert not path.exists()
