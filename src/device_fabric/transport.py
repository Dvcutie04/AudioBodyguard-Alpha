import asyncio
import math
from typing import Optional, Protocol, runtime_checkable

from .contracts import ActuationReceipt, AuthorizedActionIntent


@runtime_checkable
class PhysicalTransport(Protocol):
    async def execute_intent(
        self,
        intent: AuthorizedActionIntent,
        transaction_digest: Optional[str] = None,
        capability_digest: Optional[str] = None,
    ) -> ActuationReceipt:
        ...


class PhysicalTransportTimeout(TimeoutError):
    def __init__(self, transaction_digest: Optional[str], capability_digest: Optional[str]):
        super().__init__("Physical transport execution timed out")
        self.transaction_digest = transaction_digest
        self.capability_digest = capability_digest


async def dispatch_physical_transport(
    transport: PhysicalTransport,
    intent: AuthorizedActionIntent,
    transaction_digest: Optional[str] = None,
    capability_digest: Optional[str] = None,
    timeout_seconds: float = 2.0,
) -> ActuationReceipt:
    if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a finite positive number")
    timeout_context = asyncio.timeout(timeout_seconds)
    try:
        async with timeout_context:
            return await transport.execute_intent(
                intent=intent,
                transaction_digest=transaction_digest,
                capability_digest=capability_digest,
            )
    except TimeoutError as exc:
        if not timeout_context.expired():
            raise
        raise PhysicalTransportTimeout(
            transaction_digest=transaction_digest,
            capability_digest=capability_digest,
        ) from exc
