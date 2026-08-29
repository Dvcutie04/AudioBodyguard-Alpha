"""Mock implementation of TV device and TV adapter for testing."""

import uuid
from typing import Any, Dict, Optional, Union
from src.device_fabric.contracts import DeviceCapabilities, DeviceIdentity, DeviceState, ActuationReceipt


class MockTV:
    """Mock TV unit simulating device state and physical response."""

    def __init__(self, device_id: str = "tv_01", state: Optional[Union[Dict[str, Any], DeviceState]] = None):
        self.device_id = device_id
        self.identity = DeviceIdentity(
            device_id=device_id,
            device_type="TV",
            firmware_version="1.0.0",
        )
        self.capabilities = DeviceCapabilities(
            supported_operations=frozenset(["set_volume", "set_power", "set_muted", "REDUCE_VOLUME"]),
            max_volume=100.0,
            min_volume=0.0,
        )

        if isinstance(state, DeviceState):
            self.state = state
        elif isinstance(state, dict):
            self.state = DeviceState(
                power=state.get("power", True),
                volume=float(state.get("volume", 50.0)),
                muted=state.get("muted", False),
                input_source=state.get("input_source", "HDMI_1"),
                channel=str(state.get("channel", "")),
            )
        else:
            self.state = DeviceState(
                power=True,
                volume=50.0,
                muted=False,
                input_source="HDMI_1",
                channel="",
            )

    def set_power(self, power: bool) -> None:
        self.state.power = power

    def set_volume(self, volume: float) -> None:
        self.state.volume = volume

    def set_muted(self, muted: bool) -> None:
        self.state.muted = muted

    def set_input_source(self, source: str) -> None:
        self.state.input_source = source


class MockTVAdapter:
    """Adapter bridging MockTV to the Device Fabric execution pipeline."""

    def __init__(self, tv_or_id: Optional[Union[MockTV, str]] = None):
        if isinstance(tv_or_id, MockTV):
            self.device = tv_or_id
        elif isinstance(tv_or_id, str):
            self.device = MockTV(device_id=tv_or_id)
        else:
            self.device = MockTV()

        self.tv = self.device
        self._execution_history: Dict[str, ActuationReceipt] = {}

    def get_state(self) -> DeviceState:
        return self.device.state

    async def execute_intent(
        self,
        intent: Any,
        transaction_digest: str = "",
        capability_digest: str = "",
    ) -> ActuationReceipt:
        """Executes an authorized intent on the underlying MockTV instance and returns an ActuationReceipt."""
        intent_id = getattr(intent, "intent_id", "unknown_intent")

        if intent_id in self._execution_history:
            return self._execution_history[intent_id]

        target_state = getattr(intent, "target_state", None)
        if target_state and isinstance(target_state, DeviceState):
            self.device.state = target_state

        receipt = ActuationReceipt(
            receipt_id=f"rcpt_{uuid.uuid4().hex[:8]}",
            intent_id=intent_id,
            device_id=self.device.device_id,
            transaction_digest=transaction_digest,
            capability_digest=capability_digest,
            status="SUCCESS",
            resulting_state=self.device.state,
        )

        self._execution_history[intent_id] = receipt
        return receipt

    def apply_action(self, action: str, **kwargs: Any) -> bool:
        if action == "power_on":
            self.device.set_power(True)
        elif action == "power_off":
            self.device.set_power(False)
        elif action == "set_volume":
            self.device.set_volume(kwargs.get("volume", 0.0))
        elif action == "mute":
            self.device.set_muted(True)
        elif action == "unmute":
            self.device.set_muted(False)
        else:
            return False
        return True
