from dataclasses import fields
from src.extensions.contracts import (
    CapabilityDeclaration,
    ExtensionIdentity,
    CompatibilityRequirement,
    ExtensionManifest,
    EXTENSION_CONTRACT_VERSION,
 )

def test_declared_capability_does_not_encode_authorization():
    capability=CapabilityDeclaration(
        name="audio.volume.set",
        version="1.0",
        description="Translate an external volume-setting request",
    )
    names={f.name for f in fields(capability)}
    forbidden={
        "authorized",
        "authorization",
        "lease",
        "lease_id",
        "can_commit",
        "can_actuate",
        "physical_authority",
    }
    assert names.isdisjoint(forbidden)

def test_manifest_with_actuation_named_capability_still_has_no_authority():
    manifest=ExtensionManifest(
        identity=ExtensionIdentity(
            extension_id="aqss.test.tv.adapter",
            name="TV Adapter",
            vendor="AQSS",
            version="1.0.0",
        ),
        compatibility=CompatibilityRequirement(
            contract_version=EXTENSION_CONTRACT_VERSION,
        ),
        capabilities=(
            CapabilityDeclaration(
                name="audio.volume.set",
                version="1.0",
            ),
        ),
    )
    manifest_fields={f.name for f in fields(manifest)}
    assert "capabilities" in manifest_fields
    assert "physical_authority" not in manifest_fields
    assert "authorization" not in manifest_fields
    assert manifest.capabilities[0].name=="audio.volume.set"
