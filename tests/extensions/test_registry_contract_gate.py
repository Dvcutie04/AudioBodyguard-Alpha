import pytest
from src.extensions.contracts import (
    EXTENSION_CONTRACT_VERSION,
    ExtensionIdentity,
    CompatibilityRequirement,
    ExtensionManifest,
 )

def make_manifest(contract_version):
    return ExtensionManifest(
        identity=ExtensionIdentity(
            extension_id="aqss.test.registry",
            name="Registry Test",
            vendor="AQSS",
            version="1.0.0",
        ),
        compatibility=CompatibilityRequirement(
            contract_version=contract_version,
        ),
        capabilities=(),
    )

def test_registry_accepts_compatible_extension_contract():
    from src.extensions.registry import ExtensionRegistry
    registry=ExtensionRegistry()
    manifest=make_manifest(EXTENSION_CONTRACT_VERSION)
    registry.register(manifest)
    assert registry.get(manifest.identity.extension_id)==manifest

def test_registry_rejects_incompatible_extension_contract():
    from src.extensions.registry import ExtensionRegistry, ExtensionCompatibilityError
    registry=ExtensionRegistry()
    manifest=make_manifest("999.0")
    with pytest.raises(ExtensionCompatibilityError):
        registry.register(manifest)
    assert registry.get(manifest.identity.extension_id) is None
