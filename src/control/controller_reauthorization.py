import hashlib
import json
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SignedControllerReauthorizationGrant:
    resource_id: str
    controller_id: str
    previous_fencing_token: int
    issued_at: float
    expires_at: float
    issuer_id: str
    nonce: str
    reason: str
    signature: str = ""

    def __post_init__(self) -> None:
        for name in ("resource_id", "controller_id", "issuer_id", "nonce"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if isinstance(self.previous_fencing_token, bool) or not isinstance(self.previous_fencing_token, int) or self.previous_fencing_token <= 0:
            raise ValueError("previous_fencing_token must be a positive integer")
        for name in ("issued_at", "expires_at"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.issued_at >= self.expires_at:
            raise ValueError("reauthorization validity window is invalid")
        if self.reason != "CONTROL_PLANE_REINSTALL":
            raise ValueError("reason must be CONTROL_PLANE_REINSTALL")
        if not isinstance(self.signature, str):
            raise ValueError("signature must be a string")

    @property
    def canonical_bytes(self) -> bytes:
        payload = {
            "resource_id": self.resource_id,
            "controller_id": self.controller_id,
            "previous_fencing_token": self.previous_fencing_token,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "issuer_id": self.issuer_id,
            "nonce": self.nonce,
            "reason": self.reason,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def grant_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()
