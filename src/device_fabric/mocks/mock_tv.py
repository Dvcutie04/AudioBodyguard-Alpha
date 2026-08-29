from typing import Optional, Tuple
from src.device_fabric.contracts import DeviceState


class MockTV:
    """Base mock representation of a physical TV hardware device."""

    def __init__(self, device_id: str = "tv_living_room", initial_state: Optional[DeviceState] = None):
        self.device_id = device_id
        self.state = initial_state or DeviceState(power=True, volume=50.0, input_source="HDMI_1")

    def get_state(self) -> DeviceState:
        return self.state

    def set_state(self, new_state: DeviceState) -> None:
        self.state = new_state


class MockTVAdapter:
    """Adapter bridging PhysicalTransactionManager to MockTV hardware calls."""

    def __init__(self, device_id: str = "tv_living_room", initial_state: Optional[DeviceState] = None):
        self.device_id = device_id
        self.tv = MockTV(device_id=device_id, initial_state=initial_state)

    async def observe_state(self) -> DeviceState:
        """Observes and returns current device state."""
        return self.tv.get_state()

    async def apply_state(self, target_state: DeviceState) -> Tuple[bool, Optional[str]]:
        """Applies a target state to the mock TV."""
        self.tv.set_state(target_state)
        return True, None

    async def rollback(self, target_state: DeviceState) -> Tuple[bool, Optional[str]]:
        """Rolls back state to target state."""
        self.tv.set_state(target_state)
        return True, None
