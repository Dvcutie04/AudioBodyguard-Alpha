from __future__ import annotations

from .proposal import ExtensionProposal
from .registry import ExtensionRegistry

class ExtensionGatewayError(ValueError):
    pass

class ExtensionGateway:
    def __init__(self, registry: ExtensionRegistry):
        self._registry = registry

    def accept(self, proposal: ExtensionProposal) -> ExtensionProposal:
        manifest=self._registry.get(proposal.extension_id)
        if manifest is None:
            raise ExtensionGatewayError(
                "proposal references an unregistered extension"
            )
        if not self._registry.is_active(proposal.extension_id):
            raise ExtensionGatewayError(
                "proposal references an inactive extension"
            )
        declared={capability.name for capability in manifest.capabilities}
        if proposal.capability not in declared:
            raise ExtensionGatewayError(
                "proposal capability was not declared by extension"
            )
        return proposal
