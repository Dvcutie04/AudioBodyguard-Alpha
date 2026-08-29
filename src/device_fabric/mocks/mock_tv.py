from typing import Optional, Tuple
from src.device_fabric.contracts import DeviceState


class MockTVAdapter:
    def __init__(
        self,
        device_id: str = "tv_living_room",
        initial_state: Optional[DeviceState] = None,
    ):
        self.device_id = device_id
        self._current_state = initial_state or DeviceState(
            power=True, volume=50.0, input_source="HDMI_1"
        )

    async def observe_state(self) -> DeviceState:
        """Observes and returns current device state."""
        return self._current_state

    async def apply_state(self, target_state: DeviceState) -> Tuple[bool, Optional[str]]:
        """Applies a target state to the mock TV."""
        self._current_state = target_state
        return True, None

    async def rollback(self, target_state: DeviceState) -> Tuple[bool, Optional[str]]:
        """Rolls back state to target state."""
        self._current_state = target_state
        return True, None
