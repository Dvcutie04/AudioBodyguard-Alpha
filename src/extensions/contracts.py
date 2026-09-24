from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

EXTENSION_CONTRACT_VERSION = "1.0"

@dataclass(frozen=True)
class ExtensionIdentity:
    extension_id: str
    name: str
    vendor: str
    version: str

@dataclass(frozen=True)
class CapabilityDeclaration:
    name: str
    version: str
    description: str = ""

@dataclass(frozen=True)
class CompatibilityRequirement:
    contract_version: str
    runtime_min: str | None = None
    runtime_max: str | None = None

@dataclass(frozen=True)
class ExtensionManifest:
    identity: ExtensionIdentity
    compatibility: CompatibilityRequirement
    capabilities: tuple[CapabilityDeclaration, ...]
    metadata: Mapping[str, Any] | None = None

class ExtensionAdapter(Protocol):
    def initialize(self) -> None: ...
    def capabilities(self) -> tuple[CapabilityDeclaration, ...]: ...
    def invoke(self, capability: str, request: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def shutdown(self) -> None: ...
