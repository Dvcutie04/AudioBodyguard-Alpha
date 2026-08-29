from __future__ import annotations

from typing import Any, Dict, Optional
from src.device_fabric.contracts import DeviceIdentity, DeviceState


class MockTV:
    def __init__(
        self,
        device_id: str = "tv_mock_001",
        manufacturer: str = "Sony",
        model: str = "Bravia-XR",
        firmware_version: str = "v2.1.0",
    ):
        self.device_id = device_id
        self.identity = DeviceIdentity(
            device_id=device_id,
            manufacturer=manufacturer,
            model=model,
            firmware_version=firmware_version,
        )
        self.state = DeviceState()

    async def get_state(self) -> DeviceState:
        return self.state

    async def apply_state(self, new_state: DeviceState) -> tuple[bool, Optional[str]]:
        self.state = new_state
        return True, None

    async def execute_intent(self, intent: Any) -> bool:
        if hasattr(intent, "target_state") and isinstance(intent.target_state, dict):
            power = intent.target_state.get("power_state", self.state.power_state)
            vol = intent.target_state.get("volume", self.state.volume)
            muted = intent.target_state.get("muted", self.state.muted)
            chan = intent.target_state.get("channel", self.state.channel)
            inp = intent.target_state.get("input_source", self.state.input_source)
            self.state = DeviceState(
                power_state=power,
                volume=vol,
                muted=muted,
                channel=chan,
                input_source=inp,
            )
        return True
