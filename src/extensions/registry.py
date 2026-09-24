from __future__ import annotations

from .compatibility import is_contract_compatible
from .contracts import ExtensionManifest

class ExtensionCompatibilityError(ValueError):
    pass

class ExtensionIdentityCollisionError(ValueError):
    pass

class ExtensionActivationError(ValueError):
    pass

class ExtensionRegistry:
    def __init__(self):
        self._manifests = {}
        self._active = set()

    def register(self, manifest: ExtensionManifest) -> None:
        if not is_contract_compatible(manifest.compatibility):
            raise ExtensionCompatibilityError(
                "extension contract is incompatible with AQSS runtime"
            )
        extension_id = manifest.identity.extension_id
        if extension_id in self._manifests:
            raise ExtensionIdentityCollisionError(
                "extension identity is already registered"
            )
        self._manifests[extension_id] = manifest

    def get(self, extension_id: str):
        return self._manifests.get(extension_id)

    def is_active(self, extension_id: str) -> bool:
        return extension_id in self._active

    def activate(self, extension_id: str) -> None:
        if extension_id not in self._manifests:
            raise ExtensionActivationError(
                "cannot activate an unregistered extension"
            )
        self._active.add(extension_id)
