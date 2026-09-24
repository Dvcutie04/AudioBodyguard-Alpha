import json
import math
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ControllerBoundActionIntent:
    intent_id: str
    device_id: str
    operation: str
    parameters: Dict[str, Any]
    issuer_id: str
    policy_digest: str
    capability_lease_digest: str
    resource_id: str
    controller_id: str
    controller_lease_digest: str
    fencing_token: int
    created_at: float
    expires_at: float
    nonce: str
    transaction_id: str
    protocol_version: str
    expected_pre_state_digest: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        text_fields = (
            "intent_id", "device_id", "operation", "issuer_id",
            "policy_digest", "capability_lease_digest", "resource_id",
            "controller_id", "controller_lease_digest", "nonce",
            "transaction_id", "protocol_version",
        )
        for name in text_fields:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if isinstance(self.fencing_token, bool) or not isinstance(self.fencing_token, int) or self.fencing_token <= 0:
            raise ValueError("fencing_token must be a positive integer")
        for name in ("created_at", "expires_at"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.created_at >= self.expires_at:
            raise ValueError("intent validity window is invalid")
        if not isinstance(self.parameters, dict) or any(not isinstance(key, str) for key in self.parameters):
            raise ValueError("parameters must be a dictionary with string keys")
        try:
            json.dumps(self.parameters, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("parameters must be canonical JSON data") from exc
        if self.expected_pre_state_digest is not None and (type(self.expected_pre_state_digest) is not str or len(self.expected_pre_state_digest) != 64 or any(character not in "0123456789abcdef" for character in self.expected_pre_state_digest)):
            raise ValueError("expected_pre_state_digest must be lowercase SHA-256 hex")
        if not isinstance(self.signature, str):
            raise ValueError("signature must be a string")

    @property
    def canonical_bytes(self) -> bytes:
        payload = {
            "intent_id": self.intent_id,
            "device_id": self.device_id,
            "operation": self.operation,
            "parameters": self.parameters,
            "issuer_id": self.issuer_id,
            "policy_digest": self.policy_digest,
            "capability_lease_digest": self.capability_lease_digest,
            "resource_id": self.resource_id,
            "controller_id": self.controller_id,
            "controller_lease_digest": self.controller_lease_digest,
            "fencing_token": self.fencing_token,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "transaction_id": self.transaction_id,
            "protocol_version": self.protocol_version,
        }
        if self.expected_pre_state_digest is not None:
            payload["expected_pre_state_digest"] = self.expected_pre_state_digest
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
