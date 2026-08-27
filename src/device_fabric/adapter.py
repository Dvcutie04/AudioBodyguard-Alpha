from abc import ABC, abstractmethod
from typing import Optional
from src.device_fabric.contracts import (
    DeviceIdentity,
    DeviceCapabilities,
    DeviceState,
    ActuationReceipt,
    VerificationResult,
)


class DeviceAdapter(ABC):

    @abstractmethod
    async def discover(self) -> DeviceIdentity:
        """Discover and return the physical device identity."""
        pass

    @abstractmethod
    async def capabilities(self) -> DeviceCapabilities:
        """Return the current capability snapshot of the physical device."""
        pass

    @abstractmethod
    async def observe_state(self) -> DeviceState:
        """Read and return the physical device's current state."""
        pass

    @abstractmethod
    async def execute(
        self,
        action_id: str,
        intent_digest: str,
        command: str,
        payload: dict,
    ) -> ActuationReceipt:
        """Execute the command on the device hardware and return an initial receipt."""
        pass

    @abstractmethod
    async def verify(
        self,
        expected: DeviceState,
        transaction_digest: Optional[str] = None,
    ) -> VerificationResult:
        """Observe physical state and verify if it matches the expected target state."""
        pass

    @abstractmethod
    async def rollback(
        self,
        target_pre_state: DeviceState,
        lineage_digest: str,
    ) -> ActuationReceipt:
        """Rollback device state to the exact pre-state observation captured prior to execution."""
        pass
