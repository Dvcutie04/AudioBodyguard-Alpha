import pytest

from src.extensions.contracts import (
    EXTENSION_CONTRACT_VERSION,
    ExtensionIdentity,
    CapabilityDeclaration,
    CompatibilityRequirement,
    ExtensionManifest,
 )
from src.extensions.proposal import ExtensionProposal
from src.extensions.registry import ExtensionRegistry

def make_manifest(extension_id="aqss.test.gateway"):
    return ExtensionManifest(
        identity=ExtensionIdentity(
            extension_id=extension_id,
            name="Gateway Test",
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

def make_proposal(extension_id="aqss.test.gateway", capability="audio.volume.set"):
    return ExtensionProposal(
        extension_id=extension_id,
        capability=capability,
        target_id="living_room_tv",
        operation="SET_VOLUME",
        parameters={"volume":25},
    )

def test_gateway_rejects_unknown_extension():
    from src.extensions.gateway import ExtensionGateway, ExtensionGatewayError
    gateway=ExtensionGateway(ExtensionRegistry())
    with pytest.raises(ExtensionGatewayError):
        gateway.accept(make_proposal())

def test_gateway_rejects_inactive_extension():
    from src.extensions.gateway import ExtensionGateway, ExtensionGatewayError
    registry=ExtensionRegistry()
    registry.register(make_manifest())
    gateway=ExtensionGateway(registry)
    with pytest.raises(ExtensionGatewayError):
        gateway.accept(make_proposal())

def test_gateway_rejects_undeclared_capability():
    from src.extensions.gateway import ExtensionGateway, ExtensionGatewayError
    registry=ExtensionRegistry()
    manifest=make_manifest()
    registry.register(manifest)
    registry.activate(manifest.identity.extension_id)
    gateway=ExtensionGateway(registry)
    with pytest.raises(ExtensionGatewayError):
        gateway.accept(make_proposal(capability="device.power.set"))

def test_gateway_accepts_active_declared_capability_without_granting_authority():
    from src.extensions.gateway import ExtensionGateway
    registry=ExtensionRegistry()
    manifest=make_manifest()
    registry.register(manifest)
    registry.activate(manifest.identity.extension_id)
    gateway=ExtensionGateway(registry)
    proposal=make_proposal()
    accepted=gateway.accept(proposal)
    assert accepted is proposal
    forbidden={"authorize","commit","actuate","execute_intent","issue_capability_lease","bypass_firewall"}
    exposed={name for name in dir(gateway) if not name.startswith("_")}
    assert exposed.isdisjoint(forbidden)
