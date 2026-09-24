import json
import math
from dataclasses import dataclass, replace
from enum import Enum

from src.control.active_controller_lease import ControllerLeaseDecision


@dataclass(frozen=True)
class SignedControllerLeaseGrant:
    resource_id: str
    controller_id: str
    fencing_token: int
    controller_key_id: str
    issued_at: float
    expires_at: float
    nonce: str
    issuer_id: str
    signature: str = ""

    @property
    def canonical_bytes(self) -> bytes:
        payload = {
            "resource_id": self.resource_id,
            "controller_id": self.controller_id,
            "fencing_token": self.fencing_token,
            "controller_key_id": self.controller_key_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "issuer_id": self.issuer_id,
        }
        return json.dumps(payload, sort_keys=True).encode("utf-8")


class ControllerLeaseGrantDecision(Enum):
    ALLOW = "ALLOW"
    MALFORMED = "MALFORMED"
    UNKNOWN_ISSUER = "UNKNOWN_ISSUER"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    NOT_YET_VALID = "NOT_YET_VALID"
    EXPIRED = "EXPIRED"


class ControllerLeaseGrantVerifier:
    def __init__(self, trusted_verifiers) -> None:
        self._trusted_verifiers = dict(trusted_verifiers)

    def validate(self, grant: SignedControllerLeaseGrant, now: float) -> ControllerLeaseGrantDecision:
        if not isinstance(grant, SignedControllerLeaseGrant):
            return ControllerLeaseGrantDecision.MALFORMED
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
            return ControllerLeaseGrantDecision.MALFORMED
        identifiers = (grant.resource_id, grant.controller_id, grant.controller_key_id, grant.nonce, grant.issuer_id)
        if any(not isinstance(value, str) or not value.strip() for value in identifiers):
            return ControllerLeaseGrantDecision.MALFORMED
        if type(grant.fencing_token) is not int or grant.fencing_token <= 0:
            return ControllerLeaseGrantDecision.MALFORMED
        times = (grant.issued_at, grant.expires_at)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in times):
            return ControllerLeaseGrantDecision.MALFORMED
        if grant.issued_at >= grant.expires_at:
            return ControllerLeaseGrantDecision.MALFORMED
        if not isinstance(grant.signature, str) or not grant.signature.strip():
            return ControllerLeaseGrantDecision.MALFORMED
        verifier = self._trusted_verifiers.get(grant.issuer_id)
        if verifier is None:
            return ControllerLeaseGrantDecision.UNKNOWN_ISSUER
        if not verifier.verify(grant.canonical_bytes, grant.signature):
            return ControllerLeaseGrantDecision.INVALID_SIGNATURE
        if now < grant.issued_at:
            return ControllerLeaseGrantDecision.NOT_YET_VALID
        if now >= grant.expires_at:
            return ControllerLeaseGrantDecision.EXPIRED
        return ControllerLeaseGrantDecision.ALLOW


class ControllerLeaseGrantIssuer:
    def __init__(self, authority, signing_key) -> None:
        self._authority = authority
        self._signing_key = signing_key

    def issue(self, *, lease, controller_key_id: str, nonce: str, now: float) -> SignedControllerLeaseGrant:
        decision = self._authority.validate(lease, now=now)
        if decision is not ControllerLeaseDecision.ALLOW:
            raise RuntimeError(f"controller lease is not active: {decision.value}")
        if not isinstance(controller_key_id, str) or not controller_key_id.strip():
            raise ValueError("controller_key_id must be a nonempty string")
        if not isinstance(nonce, str) or not nonce.strip():
            raise ValueError("nonce must be a nonempty string")
        unsigned = SignedControllerLeaseGrant(
            resource_id=lease.resource_id,
            controller_id=lease.controller_id,
            fencing_token=lease.fencing_token,
            controller_key_id=controller_key_id,
            issued_at=lease.issued_at,
            expires_at=lease.expires_at,
            nonce=nonce,
            issuer_id=self._signing_key.key_id,
        )
        return replace(unsigned, signature=self._signing_key.sign(unsigned.canonical_bytes))
