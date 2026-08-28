from typing import Dict, List, Callable
from src.device_fabric.contracts import DeviceState


class DigitalTwin:
    """
    Predictive Simulation Engine.
    Provides predictive evidence that a proposed transition is valid under the safety model.
    Does NOT establish physical truth (that is reserved for adapter observation).
    """
    def __init__(self):
        # Maps device_id to a list of constraint evaluation functions
        self._constraints: Dict[str, List[Callable[[DeviceState, DeviceState], bool]]] = {}

    def register_constraint(self, device_id: str, constraint_fn: Callable[[DeviceState, DeviceState], bool]) -> None:
        """Registers a mathematical or logical safety boundary for a specific device."""
        if device_id not in self._constraints:
            self._constraints[device_id] = []
        self._constraints[device_id].append(constraint_fn)

    def validate_transition(
        self, device_id: str, current_state: DeviceState, target_state: DeviceState
    ) -> bool:
        """
        Evaluates the proposed transition against all registered constraints.
        Returns True ONLY if all bounds checks pass.
        """
        constraints = self._constraints.get(device_id, [])
        for check in constraints:
            if not check(current_state, target_state):
                return False
        return True
