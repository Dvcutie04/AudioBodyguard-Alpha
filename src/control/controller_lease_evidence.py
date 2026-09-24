import hashlib
import json
import math
import threading
from dataclasses import dataclass
from enum import Enum

from src.control.crypto_identity import KeyVerifier


@dataclass(frozen=True)
class SignedControllerLeaseEvidence:
    resource_id: str
    controller_id: str
    fencing_token: int
    issued_at: float
    expires_at: float
    issuer_id: str
    nonce: str
    scope: tuple[str, ...]
    signature: str = ""

    def __post_init__(self) -> None:
        for name in ("resource_id", "controller_id", "issuer_id", "nonce"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if isinstance(self.fencing_token, bool) or not isinstance(self.fencing_token, int) or self.fencing_token <= 0:
            raise ValueError("fencing_token must be a positive integer")
        for name in ("issued_at", "expires_at"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.issued_at >= self.expires_at:
            raise ValueError("evidence validity window is invalid")
        if not isinstance(self.scope, tuple) or not self.scope:
            raise ValueError("scope must be a nonempty tuple")
        if any(not isinstance(item, str) or not item.strip() for item in self.scope):
            raise ValueError("scope entries must be nonempty strings")
        if len(set(self.scope)) != len(self.scope):
            raise ValueError("scope entries must be unique")
        if not isinstance(self.signature, str):
            raise ValueError("signature must be a string")

    @property
    def canonical_bytes(self) -> bytes:
        payload = {
            "resource_id": self.resource_id,
            "controller_id": self.controller_id,
            "fencing_token": self.fencing_token,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "issuer_id": self.issuer_id,
            "nonce": self.nonce,
            "scope": list(self.scope),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def evidence_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


class ControllerEvidenceDecision(Enum):
    ALLOW = "ALLOW"
    ISSUER_UNKNOWN = "ISSUER_UNKNOWN"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    NOT_YET_VALID = "NOT_YET_VALID"
    EXPIRED = "EXPIRED"
    REPLAY = "REPLAY"


class ControllerLeaseEvidenceValidator:
    def __init__(self, trusted_verifiers: dict[str, KeyVerifier]) -> None:
        self._trusted_verifiers = dict(trusted_verifiers)
        self._seen_nonces: set[tuple[str, str]] = set()
        self._lock = threading.RLock()

    def validate(self, evidence: SignedControllerLeaseEvidence, *, now: float) -> ControllerEvidenceDecision:
        if not isinstance(evidence, SignedControllerLeaseEvidence):
            raise ValueError("evidence must be SignedControllerLeaseEvidence")
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("now must be a finite number")
        verifier = self._trusted_verifiers.get(evidence.issuer_id)
        if verifier is None:
            return ControllerEvidenceDecision.ISSUER_UNKNOWN
        if not verifier.verify(evidence.canonical_bytes, evidence.signature):
            return ControllerEvidenceDecision.SIGNATURE_INVALID
        if now < evidence.issued_at:
            return ControllerEvidenceDecision.NOT_YET_VALID
        if now >= evidence.expires_at:
            return ControllerEvidenceDecision.EXPIRED
        nonce_key = (evidence.issuer_id, evidence.nonce)
        with self._lock:
            if nonce_key in self._seen_nonces:
                return ControllerEvidenceDecision.REPLAY
            self._seen_nonces.add(nonce_key)
            return ControllerEvidenceDecision.ALLOW
