import pytest
from src.extensions.contracts import (
    EXTENSION_CONTRACT_VERSION,
    ExtensionIdentity,
    CompatibilityRequirement,
    ExtensionManifest,
 )
from src.extensions.registry import ExtensionRegistry, ExtensionIdentityCollisionError

def make_manifest(version):
    return ExtensionManifest(
        identity=ExtensionIdentity(
            extension_id="aqss.test.same_identity",
            name="Identity Collision Test",
            vendor="AQSS",
            version=version,
        ),
        compatibility=CompatibilityRequirement(
            contract_version=EXTENSION_CONTRACT_VERSION,
        ),
        capabilities=(),
    )

def test_registry_does_not_silently_replace_existing_extension_identity():
    registry=ExtensionRegistry()
    first=make_manifest("1.0.0")
    second=make_manifest("2.0.0")
    registry.register(first)
    with pytest.raises(ExtensionIdentityCollisionError):
        registry.register(second)
    assert registry.get(first.identity.extension_id)==first
