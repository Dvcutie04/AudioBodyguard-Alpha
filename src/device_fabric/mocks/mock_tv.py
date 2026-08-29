from datetime import datetime, timezone
from typing import Any, Optional

from src.device_fabric.contracts import (
    ActuationReceipt,
    ActuationStatus,
    AuthorizedActionIntent,
    DeviceCapabilities,
    DeviceIdentity,
    DeviceState,
    DeviceType,
)


class MockTV:
    def __init__(self, device_id: str = "tv_mock_001", manufacturer: str = "Generic", model: str = "SmartTV"):
        self.identity = DeviceIdentity(
            device_id=device_id,
            device_type=DeviceType.TV,
            name=model,
            vendor=manufacturer,
        )
        self.state = DeviceState()
        self.capabilities = DeviceCapabilities(
            device_id=device_id,
            capabilities={"power", "volume", "channel", "input_source"},
            supported_actions=["set_power", "set_volume", "set_channel", "set_input_source"],
        )

    async def apply_state(self, target_state: DeviceState) -> None:
        self.state = target_state

    async def execute_intent(self, intent: Any) -> bool:
        if hasattr(intent, "target_state") and isinstance(intent.target_state, DeviceState):
            self.state = intent.target_state
        elif hasattr(intent, "target_state") and isinstance(intent.target_state, dict):
            power = intent.target_state.get("power", self.state.power)
            vol = intent.target_state.get("volume", self.state.volume)
            muted = intent.target_state.get("muted", self.state.muted)
            chan = intent.target_state.get("channel", self.state.channel)
            inp = intent.target_state.get("input_source", self.state.input_source)
            self.state = DeviceState(
                power=power,
                volume=vol,
                muted=muted,
                channel=chan,
                input_source=inp,
            )
        return True


class MockTVAdapter:
    def __init__(self, device_id: str = "tv_mock_001"):
        self.device = MockTV(device_id=device_id)
        self._executed_intents = set()

    async def execute_intent(
        self,
        intent: AuthorizedActionIntent,
        transaction_digest: Optional[str] = None,
        capability_digest: Optional[str] = None,
    ) -> ActuationReceipt:
        if intent.intent_id in self._executed_intents:
            return ActuationReceipt(
                receipt_id=f"rcpt_{intent.intent_id}",
                intent_id=intent.intent_id,
                device_id=self.device.identity.device_id,
                status=ActuationStatus.DUPLICATE_ABSORBED,
                timestamp=datetime.now(timezone.utc).timestamp(),
            )

        self._executed_intents.add(intent.intent_id)

        if intent.target_state:
            await self.device.apply_state(intent.target_state)

        return ActuationReceipt(
            receipt_id=f"rcpt_{intent.intent_id}",
            intent_id=intent.intent_id,
            device_id=self.device.identity.device_id,
            status=ActuationStatus.EXECUTED,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )
