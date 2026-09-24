from inspect import signature

from src.device_fabric.transport import PhysicalTransport, PhysicalTransportTimeout, dispatch_physical_transport


class ConformingTransport:
    async def execute_intent(
        self,
        intent,
        transaction_digest=None,
        capability_digest=None,
    ):
        return None


class MissingExecutionTransport:
    pass


def test_physical_transport_is_runtime_checkable():
    assert isinstance(ConformingTransport(), PhysicalTransport)
    assert not isinstance(MissingExecutionTransport(), PhysicalTransport)


def test_physical_transport_preserves_commit_lineage_arguments():
    parameters = tuple(signature(PhysicalTransport.execute_intent).parameters)
    assert parameters == (
        "self",
        "intent",
        "transaction_digest",
        "capability_digest",
    )


import pytest

from src.control.device_fabric_bridge import Gen3DeviceFabricBridge


class SynchronousTransportImpostor:
    def execute_intent(
        self,
        intent,
        transaction_digest=None,
        capability_digest=None,
    ):
        return None


def test_bridge_rejects_synchronous_transport():
    with pytest.raises(ValueError, match="asynchronous PhysicalTransport"):
        Gen3DeviceFabricBridge(
            firewall=object(),
            adapter=SynchronousTransportImpostor(),
        )


import asyncio

from src.device_fabric.physical_commit_gate import PhysicalCommitGate
from src.device_fabric.precondition_gate import PreconditionResult


class AllowingPreconditionGate:
    def evaluate(self, intent, lease, snapshot):
        return PreconditionResult.ALLOW


class MinimalIntent:
    transaction_id = "transport-test-transaction"
    capability_digest = "transport-test-capability"


class CountingSynchronousTransport:
    def __init__(self):
        self.calls = 0

    def execute_intent(
        self,
        intent,
        transaction_digest=None,
        capability_digest=None,
    ):
        self.calls += 1
        return None


def test_physical_commit_gate_rejects_synchronous_transport_before_call():
    transport = CountingSynchronousTransport()
    gate = PhysicalCommitGate(precondition_gate=AllowingPreconditionGate())
    with pytest.raises(ValueError, match="asynchronous PhysicalTransport"):
        asyncio.run(
            gate.commit(
                intent=MinimalIntent(),
                lease=object(),
                snapshot=object(),
                adapter=transport,
            )
        )
    assert transport.calls == 0


from src.device_fabric.transport import (
    PhysicalTransportTimeout,
    dispatch_physical_transport,
)


class HangingTransport:
    def __init__(self):
        self.calls = 0

    async def execute_intent(
        self,
        intent,
        transaction_digest=None,
        capability_digest=None,
    ):
        self.calls += 1
        await asyncio.Event().wait()


def test_physical_transport_dispatch_times_out():
    transport = HangingTransport()

    async def scenario():
        with pytest.raises(PhysicalTransportTimeout):
            await dispatch_physical_transport(
                transport=transport,
                intent=MinimalIntent(),
                transaction_digest="transport-test-transaction",
                capability_digest="transport-test-capability",
                timeout_seconds=0.02,
            )

    asyncio.run(scenario())
    assert transport.calls == 1


class HangingPhysicalTransport:
    def __init__(self):
        self.calls = 0
        self.cancelled = False

    async def execute_intent(
        self,
        intent,
        transaction_digest=None,
        capability_digest=None,
    ):
        self.calls += 1
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


def test_dispatch_timeout_cancels_once_and_preserves_lineage():
    transport = HangingPhysicalTransport()

    async def scenario():
        with pytest.raises(PhysicalTransportTimeout) as captured:
            await dispatch_physical_transport(
                transport=transport,
                intent=MinimalIntent(),
                transaction_digest="transport-test-transaction",
                capability_digest="transport-test-capability",
                timeout_seconds=0.02,
            )
        return captured.value

    timeout = asyncio.run(scenario())
    assert transport.calls == 1
    assert transport.cancelled is True
    assert timeout.transaction_digest == "transport-test-transaction"
    assert timeout.capability_digest == "transport-test-capability"


def test_physical_commit_gate_applies_transport_timeout():
    transport = HangingPhysicalTransport()
    gate = PhysicalCommitGate(
        precondition_gate=AllowingPreconditionGate(),
        transport_timeout_seconds=0.02,
    )

    async def scenario():
        with pytest.raises(PhysicalTransportTimeout) as captured:
            await gate.commit(
                intent=MinimalIntent(),
                lease=object(),
                snapshot=object(),
                adapter=transport,
            )
        return captured.value

    timeout = asyncio.run(scenario())
    assert transport.calls == 1
    assert transport.cancelled is True
    assert timeout.transaction_digest == "transport-test-transaction"
    assert timeout.capability_digest == "transport-test-capability"


class InvalidTimeoutCountingTransport:
    def __init__(self):
        self.calls = 0

    async def execute_intent(
        self,
        intent,
        transaction_digest=None,
        capability_digest=None,
    ):
        self.calls += 1
        return object()


@pytest.mark.parametrize(
    "invalid_timeout",
    [True, False, 0, -1, float("nan"), float("inf"), "1"],
)
def test_dispatch_rejects_invalid_timeout_before_transport_call(invalid_timeout):
    transport = InvalidTimeoutCountingTransport()

    async def scenario():
        with pytest.raises(ValueError, match="timeout_seconds"):
            await dispatch_physical_transport(
                transport=transport,
                intent=MinimalIntent(),
                timeout_seconds=invalid_timeout,
            )

    asyncio.run(scenario())
    assert transport.calls == 0


class SelfTimingOutTransport:
    def __init__(self):
        self.calls = 0

    async def execute_intent(
        self,
        intent,
        transaction_digest=None,
        capability_digest=None,
    ):
        self.calls += 1
        raise TimeoutError("adapter timeout")


def test_dispatch_preserves_transport_generated_timeout():
    transport = SelfTimingOutTransport()

    async def scenario():
        with pytest.raises(TimeoutError, match="adapter timeout") as captured:
            await dispatch_physical_transport(
                transport=transport,
                intent=MinimalIntent(),
                timeout_seconds=1.0,
            )
        return captured.value

    timeout = asyncio.run(scenario())
    assert type(timeout) is TimeoutError
    assert transport.calls == 1
