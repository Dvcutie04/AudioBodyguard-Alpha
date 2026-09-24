from __future__ import annotations

from .contracts import (
    EXTENSION_CONTRACT_VERSION,
    CompatibilityRequirement,
 )

def is_contract_compatible(requirement: CompatibilityRequirement) -> bool:
    return requirement.contract_version == EXTENSION_CONTRACT_VERSION
