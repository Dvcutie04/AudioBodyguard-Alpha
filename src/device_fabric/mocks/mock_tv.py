import time
from typing import Optional

from src.device_fabric.adapter import DeviceAdapter
from src.device_fabric.contracts import (
    ActuationReceipt,
    ActuationStatus,
    DeviceCapabilities,
    DeviceIdentity,
    DeviceState,
    DeviceType,
    VerificationResult,
)


class MockTVAdapter(DeviceAdapter):
    def __init__(self, device_id: str):
        self._identity = DeviceIdentity(
            device_id=device_id,
            device_type=DeviceType.TV,
            manufacturer="MockCorp",
            model="MockTV-2000",
            firmware_version="1.0.0-mock",  # Added to satisfy the updated contract
        )
        self._state = DeviceState(
            power=True, volume=50.0, muted=False, input_source="HDMI_1"
        )
        self._execution_history = set()

    @property
    def identity(self) -> DeviceIdentity:
        return self._identity

    @property
    def state(self) -> DeviceState:
        return self._state

    def inject_fault_state(self, power: bool, volume: float, muted: bool) -> None:
        """Test hook to simulate hardware state drifting outside of fabric control."""
        self._state = DeviceState(
            power=power,
            volume=volume,
            muted=muted,
            input_source=self._state.input_source,
        )

    async def discover(self) -> DeviceIdentity:
        return self.identity

    async def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            capability_digest="mock_cap_sha256_001",
            supported_commands=["SET_POWER", "SET_VOLUME", "REDUCE_VOLUME", "MUTE"],
        )

    async def observe_state(self) -> DeviceState:
        return self.state

    async def execute(
        self,
        action_id: str,
        intent_digest: str,
        command: str,
        payload: dict,
    ) -> ActuationReceipt:
        
        tx_digest = f"{action_id}|{self.identity.device_id}|{intent_digest}"
        
        if tx_digest in self._execution_history:
            return ActuationReceipt(
                receipt_id=f"rcpt_{time.time()}",
                action_id=action_id,
                device_id=self.identity.device_id,
                intent_digest=intent_digest,
                status=ActuationStatus.DUPLICATE_ABSORBED.value,
                timestamp=time.time(),
                transaction_digest=tx_digest,
                capability_digest="mock_cap_sha256_001",
                pre_state_digest=self.state.state_digest,
                post_state_digest=self.state.state_digest,
                fabric_sequence=0,
            )

        pre_state = self.state
        
        # Simulate execution
        if command == "REDUCE_VOLUME":
            delta = payload.get("delta_db", 0.0)
            new_vol = max(0.0, self.state.volume - delta)
            self._state = DeviceState(
                power=self.state.power,
                volume=new_vol,
                muted=self.state.muted,
                input_source=self.state.input_source
            )

        self._execution_history.add(tx_digest)
        
        return ActuationReceipt(
            receipt_id=f"rcpt_{time.time()}",
            action_id=action_id,
            device_id=self.identity.device_id,
            intent_digest=intent_digest,
            status=ActuationStatus.EXECUTED.value,
            timestamp=time.time(),
            transaction_digest=tx_digest,
            capability_digest="mock_cap_sha256_001",
            pre_state_digest=pre_state.state_digest,
            post_state_digest=self.state.state_digest,
            fabric_sequence=0,
        )

    async def verify(
        self,
        expected: DeviceState,
        transaction_digest: Optional[str] = None,
    ) -> VerificationResult:
        current = await self.observe_state()

        vol_match = abs(current.volume - expected.volume) < 0.1
        match = (
            current.power == expected.power
            and vol_match
            and current.muted == expected.muted
            and current.input_source == expected.input_source
        )

        return VerificationResult(
            verified=match,
            expected_state=expected,
            observed_state=current,
            error_message=None if match else "State mismatch",
            transaction_digest=transaction_digest,
        )

    async def rollback(
        self, target_pre_state: DeviceState, lineage_digest: str
    ) -> ActuationReceipt:
        pre_rollback_state = self.state
        self._state = target_pre_state
        
        return ActuationReceipt(
            receipt_id=f"rb_{time.time()}",
            action_id="ROLLBACK",
            device_id=self.identity.device_id,
            intent_digest=lineage_digest,
            status=ActuationStatus.ROLLED_BACK.value,
            timestamp=time.time(),
            transaction_digest=f"rb_{lineage_digest}",
            capability_digest="mock_cap_sha256_001",
            pre_state_digest=pre_rollback_state.state_digest,
            post_state_digest=self.state.state_digest,
            fabric_sequence=0,
        )
