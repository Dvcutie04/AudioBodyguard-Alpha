from abc import ABC, abstractmethod
from src.device_fabric.contracts import (
    DeviceIdentity,
    DeviceCapabilities,
    DeviceState,
    ActuationReceipt,
    VerificationResult,
)


class DeviceAdapter(ABC):
    """Abstract base class for device adapters."""

    @abstractmethod
    async def discover(self) -> DeviceIdentity:
        """Discover and return device identity."""
        pass

    @abstractmethod
    async def capabilities(self) -> DeviceCapabilities:
        """Return device capabilities."""
        pass

    @abstractmethod
    async def observe_state(self) -> DeviceState:
        """Observe and return current device state."""
        pass

    @abstractmethod
    async def execute(
        self,
        action_id: str,
        intent_digest: str,
        command: str,
        payload: dict,
    ) -> ActuationReceipt:
        """Execute a command on the device."""
        pass

    @abstractmethod
    async def verify(self, expected: DeviceState) -> VerificationResult:
        """Verify device state matches expected state."""
        pass

    @abstractmethod
    async def rollback(
        self,
        previous: DeviceState,
        lineage_digest: str,
    ) -> ActuationReceipt:
        """Rollback device to a previous state."""
        pass
