import time
from typing import Optional
from src.device_fabric.contracts import (
    DeviceIdentity,
    DeviceCapabilities,
    DeviceState,
    DeviceType,
    ActuationReceipt,
    VerificationResult,
    ActuationStatus,
)
from src.device_fabric.adapter import DeviceAdapter


class MockTVAdapter(DeviceAdapter):
    def __init__(self, device_id: str):
        self._device_id = device_id
        self._identity = DeviceIdentity(
            device_id=device_id,
            device_type=DeviceType.TV,
            manufacturer="MockCorp",
            model="MockTV-2000",
        )
        self._capabilities = DeviceCapabilities(
            volume_absolute=True,
            volume_delta=True,
            mute=True,
            power=True,
            input_select=True,
            max_volume_delta_db=15.0,
            min_volume_db=0.0,
            max_volume_db=100.0,
        )
        # Internal deterministic state
        self._state = DeviceState(
            power=True,
            volume=50.0,
            muted=False,
            input_source="HDMI_1",
        )

    async def discover(self) -> DeviceIdentity:
        return self._identity

    async def capabilities(self) -> DeviceCapabilities:
        return self._capabilities

    async def observe_state(self) -> DeviceState:
        return self._state

    async def execute(
        self,
        action_id: str,
        intent_digest: str,
        command: str,
        payload: dict,
    ) -> ActuationReceipt:
        # Simulate execution mutating internal hardware state
        if command == "REDUCE_VOLUME":
            delta = payload.get("delta_db", 0.0)
            new_vol = max(self._capabilities.min_volume_db, self._state.volume - delta)
            self._state = DeviceState(
                power=self._state.power,
                volume=new_vol,
                muted=self._state.muted,
                input_source=self._state.input_source,
            )
        elif command == "SET_VOLUME":
            target = payload.get("volume", self._state.volume)
            new_vol = max(
                self._capabilities.min_volume_db,
                min(self._capabilities.max_volume_db, target),
            )
            self._state = DeviceState(
                power=self._state.power,
                volume=new_vol,
                muted=self._state.muted,
                input_source=self._state.input_source,
            )
        elif command == "MUTE":
            self._state = DeviceState(
                power=self._state.power,
                volume=self._state.volume,
                muted=True,
                input_source=self._state.input_source,
            )

        return ActuationReceipt(
            receipt_id=f"receipt_{action_id}",
            action_id=action_id,
            device_id=self._device_id,
            intent_digest=intent_digest,
            status=ActuationStatus.EXECUTED.value,
            timestamp=time.time(),
        )

    async def verify(
        self,
        expected: DeviceState,
        transaction_digest: Optional[str] = None,
    ) -> VerificationResult:
        current = await self.observe_state()

        # Allow minor float precision differences for volume
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
        self,
        target_pre_state: DeviceState,
        lineage_digest: str,
    ) -> ActuationReceipt:
        # Overwrite current state with the exact target pre-state observation
        self._state = target_pre_state

        return ActuationReceipt(
            receipt_id=f"rollback_{lineage_digest[:8]}",
            action_id="ROLLBACK",
            device_id=self._device_id,
            intent_digest=lineage_digest,
            status=ActuationStatus.ROLLED_BACK.value,
            timestamp=time.time(),
        )

    def inject_fault_state(self, power: bool, volume: float, muted: bool):
        """Helper to forcefully mutate state for test fault-injection."""
        self._state = DeviceState(
            power=power,
            volume=volume,
            muted=muted,
            input_source=self._state.input_source,
        )
