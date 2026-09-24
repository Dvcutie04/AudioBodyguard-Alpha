from src.extensions.contracts import (
    EXTENSION_CONTRACT_VERSION,
    ExtensionIdentity,
    CompatibilityRequirement,
    ExtensionManifest,
 )
from src.extensions.registry import ExtensionRegistry

def make_manifest():
    return ExtensionManifest(
        identity=ExtensionIdentity(
            extension_id="aqss.test.active_no_authority",
            name="Active No Authority",
            vendor="AQSS",
            version="1.0.0",
        ),
        compatibility=CompatibilityRequirement(
            contract_version=EXTENSION_CONTRACT_VERSION,
        ),
        capabilities=(),
    )

def test_active_extension_still_has_no_physical_authority_surface():
    registry=ExtensionRegistry()
    manifest=make_manifest()
    registry.register(manifest)
    registry.activate(manifest.identity.extension_id)
    assert registry.is_active(manifest.identity.extension_id) is True
    forbidden={
        "authorize",
        "commit",
        "actuate",
        "execute_intent",
        "issue_capability_lease",
        "bypass_firewall",
    }
    exposed={name for name in dir(registry) if not name.startswith("_")}
    assert exposed.isdisjoint(forbidden)
