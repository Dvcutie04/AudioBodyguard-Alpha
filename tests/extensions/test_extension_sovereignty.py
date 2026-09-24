from dataclasses import fields
from src.extensions.contracts import (
    ExtensionAdapter,
    ExtensionIdentity,
    CapabilityDeclaration,
    CompatibilityRequirement,
    ExtensionManifest,
    EXTENSION_CONTRACT_VERSION,
 )

def test_extension_contract_does_not_expose_physical_authority_primitives():
    names={name for name in dir(ExtensionAdapter) if not name.startswith("_")}
    forbidden={
        "authorize",
        "commit",
        "actuate",
        "execute_intent",
        "issue_capability_lease",
        "bypass_firewall",
    }
    assert names.isdisjoint(forbidden)

def test_extension_manifest_has_no_physical_authority_field():
    names={f.name for f in fields(ExtensionManifest)}
    forbidden={
        "physical_authority",
        "commit_authority",
        "actuation_authority",
        "authorization_authority",
    }
    assert names.isdisjoint(forbidden)

def test_extension_manifest_is_declarative_only():
    manifest=ExtensionManifest(
        identity=ExtensionIdentity(
            extension_id="aqss.test.extension",
            name="Test Extension",
            vendor="AQSS",
            version="1.0.0",
        ),
        compatibility=CompatibilityRequirement(
            contract_version=EXTENSION_CONTRACT_VERSION,
        ),
        capabilities=(
            CapabilityDeclaration(
                name="audio.volume.observe",
                version="1.0",
            ),
        ),
    )
    assert manifest.compatibility.contract_version==EXTENSION_CONTRACT_VERSION
    assert manifest.capabilities[0].name=="audio.volume.observe"
