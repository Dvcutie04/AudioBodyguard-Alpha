from typing import Dict, Optional
from src.device_fabric.adapter import DeviceAdapter
from src.device_fabric.contracts import DeviceCapabilities, DeviceIdentity


class DeviceRegistry:
    def __init__(self):
        self._adapters: Dict[str, DeviceAdapter] = {}

    def register(self, device_id: str, adapter: DeviceAdapter) -> None:
        """Register a device adapter instance."""
        self._adapters[device_id] = adapter

    def unregister(self, device_id: str) -> None:
        """Unregister a device adapter instance."""
        self._adapters.pop(device_id, None)

    def get_adapter(self, device_id: str) -> Optional[DeviceAdapter]:
        """Retrieve a registered device adapter by ID."""
        return self._adapters.get(device_id)

    async def get_identity(self, device_id: str) -> Optional[DeviceIdentity]:
        """Fetch physical device identity."""
        adapter = self.get_adapter(device_id)
        if not adapter:
            return None
        return await adapter.discover()

    async def get_capabilities(self, device_id: str) -> Optional[DeviceCapabilities]:
        """Fetch current capability snapshot."""
        adapter = self.get_adapter(device_id)
        if not adapter:
            return None
        return await adapter.capabilities()
