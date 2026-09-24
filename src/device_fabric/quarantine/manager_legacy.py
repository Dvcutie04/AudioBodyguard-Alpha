from __future__ import annotations
import time
from typing import Dict, Optional, Any
from .contracts import DeviceIdentity, DeviceState, CapabilityLease, LeaseExpiredError, ContractViolation
from .bus import EventBus
from .store import StateStore

class DeviceFabricManager:
    def __init__(self, bus: Optional[EventBus] = None, store: Optional[StateStore] = None):
        self._devices: Dict[str, DeviceIdentity] = {}
        self._states: Dict[str, DeviceState] = {}
        self._leases: Dict[str, CapabilityLease] = {}
        self.bus = bus
        self.store = store

    def register_device(self, identity: DeviceIdentity, initial_state: Optional[DeviceState] = None) -> None:
        self._devices[identity.device_id] = identity
        self._states[identity.device_id] = initial_state or DeviceState()
        if self.store:
            self.store.save_states(self._states)

    def grant_lease(self, lease: CapabilityLease) -> None:
        self._leases[lease.lease_id] = lease

    async def execute_action_async(self, lease_id: str, action: str, target_state: Optional[DeviceState] = None) -> DeviceState:
        lease = self._leases.get(lease_id)
        if not lease or not lease.is_valid():
            raise LeaseExpiredError(f"Lease {lease_id} is invalid or expired.")
        if lease.capability and lease.capability != action and action not in lease.capabilities:
            raise ContractViolation(f"Action {action} not authorized by lease {lease_id}.")
        if lease.device_id and lease.device_id in self._states and target_state:
            self._states[lease.device_id] = target_state
            if self.store:
                self.store.save_states(self._states)
            if self.bus:
                await self.bus.publish("state_changed", {"device_id": lease.device_id, "action": action, "state": target_state})
            return target_state
        return self._states.get(lease.device_id, DeviceState())
