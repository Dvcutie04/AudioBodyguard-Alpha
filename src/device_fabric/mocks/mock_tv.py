"""Mock implementation of TV device and TV adapter for testing."""

from typing import Any, Dict, Optional


class MockTV:
    """Mock TV unit simulating device state and physical response."""

    def __init__(self, device_id: str = "tv_01", state: Optional[Dict[str, Any]] = None):
        self.device_id = device_id
        self.state = state if state is not None else {
            "power": False,
            "volume": 10,
            "muted": False,
            "input_source": "HDMI1",
            "channel": 1,
        }

    def set_power(self, power: bool) -> None:
        self.state["power"] = power

    def set_volume(self, volume: float) -> None:
        self.state["volume"] = volume

    def set_muted(self, muted: bool) -> None:
        self.state["muted"] = muted

    def set_input_source(self, source: str) -> None:
        self.state["input_source"] = source


class MockTVAdapter:
    """Adapter bridging MockTV to the Device Fabric execution pipeline."""

    def __init__(self, tv: Optional[MockTV] = None):
        self.tv = tv or MockTV()

    def get_state(self) -> Dict[str, Any]:
        return self.tv.state

    def apply_action(self, action: str, **kwargs: Any) -> bool:
        if action == "power_on":
            self.tv.set_power(True)
        elif action == "power_off":
            self.tv.set_power(False)
        elif action == "set_volume":
            self.tv.set_volume(kwargs.get("volume", 0))
        elif action == "mute":
            self.tv.set_muted(True)
        elif action == "unmute":
            self.tv.set_muted(False)
        else:
            return False
        return True
