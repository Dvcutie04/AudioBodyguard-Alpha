import pytest
from src.extensions.contracts import (
    EXTENSION_CONTRACT_VERSION,
    ExtensionIdentity,
    CompatibilityRequirement,
    ExtensionManifest,
 )
from src.extensions.registry import ExtensionRegistry, ExtensionActivationError

def make_manifest():
    return ExtensionManifest(
        identity=ExtensionIdentity(
            extension_id="aqss.test.activation",
            name="Activation Test",
            vendor="AQSS",
            version="1.0.0",
        ),
        compatibility=CompatibilityRequirement(
            contract_version=EXTENSION_CONTRACT_VERSION,
        ),
        capabilities=(),
    )

def test_registered_extension_is_inactive_by_default():
    registry=ExtensionRegistry()
    manifest=make_manifest()
    registry.register(manifest)
    assert registry.get(manifest.identity.extension_id)==manifest
    assert registry.is_active(manifest.identity.extension_id) is False

def test_unknown_extension_cannot_be_activated():
    registry=ExtensionRegistry()
    with pytest.raises(ExtensionActivationError):
        registry.activate("aqss.unknown.extension")

def test_registered_extension_requires_explicit_activation():
    registry=ExtensionRegistry()
    manifest=make_manifest()
    registry.register(manifest)
    registry.activate(manifest.identity.extension_id)
    assert registry.is_active(manifest.identity.extension_id) is True
