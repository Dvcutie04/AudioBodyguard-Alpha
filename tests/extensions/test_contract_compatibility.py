from src.extensions.contracts import (
    EXTENSION_CONTRACT_VERSION,
    CompatibilityRequirement,
 )

from src.extensions.compatibility import is_contract_compatible

def test_matching_extension_contract_version_is_compatible():
    requirement=CompatibilityRequirement(
        contract_version=EXTENSION_CONTRACT_VERSION,
    )
    assert is_contract_compatible(requirement) is True

def test_mismatched_extension_contract_version_fails_closed():
    requirement=CompatibilityRequirement(
        contract_version="999.0",
    )
    assert is_contract_compatible(requirement) is False
