from abc import ABC, abstractmethod
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
        pass

    @abstractmethod
    async def capabilities(self) -> DeviceCapabilities:
        pass

    @abstractmethod
    async def observe_state(self) -> DeviceState:
        pass

    @abstractmethod
    async def execute(
        self, action_id: str, intent_digest: str, command: str, payload: dict
    ) -> ActuationReceipt:
        pass

    @abstractmethod
    async def verify(self, expected: DeviceState) -> VerificationResult:
        pass

    @abstractmethod
    async def rollback(
        self, previous: DeviceState, lineage_digest: str
    ) -> ActuationReceipt:
        pass
