import math
import threading
from enum import Enum

from src.control.active_controller_lease import ActiveControllerLease, ActiveControllerLeaseAuthority, ControllerLeaseDecision
from src.control.capability_lease import SignedCapabilityLease
from src.control.controller_bound_intent import ControllerBoundActionIntent
from src.control.controller_lease_evidence import SignedControllerLeaseEvidence
from src.control.crypto_identity import KeyVerifier


class ControllerBoundRejectionCode(Enum):
    INVALID_INPUT = "INVALID_INPUT"
    POLICY_ISSUER_UNKNOWN = "POLICY_ISSUER_UNKNOWN"
    POLICY_SIGNATURE_INVALID = "POLICY_SIGNATURE_INVALID"
    CAPABILITY_ISSUER_MISMATCH = "CAPABILITY_ISSUER_MISMATCH"
    CAPABILITY_SIGNATURE_INVALID = "CAPABILITY_SIGNATURE_INVALID"
    DEVICE_MISMATCH = "DEVICE_MISMATCH"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    CONTROLLER_ISSUER_UNKNOWN = "CONTROLLER_ISSUER_UNKNOWN"
    CONTROLLER_SIGNATURE_INVALID = "CONTROLLER_SIGNATURE_INVALID"
    CONTROLLER_BINDING_MISMATCH = "CONTROLLER_BINDING_MISMATCH"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    NOT_YET_VALID = "NOT_YET_VALID"
    EXPIRED = "EXPIRED"
    STALE_FENCE = "STALE_FENCE"
    CONTROLLER_EVIDENCE_REQUIRED = "CONTROLLER_EVIDENCE_REQUIRED"
    REPLAY = "REPLAY"


class ControllerBoundIntentFirewall:
    def __init__(self, *, policy_verifiers: dict[str, KeyVerifier], controller_verifiers: dict[str, KeyVerifier], active_controller_authority: ActiveControllerLeaseAuthority | None = None) -> None:
        self.policy_verifiers = dict(policy_verifiers)
        self.controller_verifiers = dict(controller_verifiers)
        self.active_controller_authority = active_controller_authority
        self._seen_nonces: set[tuple[str, str]] = set()
        self._lock = threading.RLock()

    def validate(self, intent: ControllerBoundActionIntent, capability_lease: SignedCapabilityLease, controller_evidence: SignedControllerLeaseEvidence, *, now: float):
        if not isinstance(intent, ControllerBoundActionIntent) or not isinstance(capability_lease, SignedCapabilityLease) or not isinstance(controller_evidence, SignedControllerLeaseEvidence):
            return ControllerBoundRejectionCode.INVALID_INPUT
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
            return ControllerBoundRejectionCode.INVALID_INPUT
        policy_verifier = self.policy_verifiers.get(intent.issuer_id)
        if policy_verifier is None:
            return ControllerBoundRejectionCode.POLICY_ISSUER_UNKNOWN
        if not policy_verifier.verify(intent.canonical_bytes, intent.signature):
            return ControllerBoundRejectionCode.POLICY_SIGNATURE_INVALID
        if capability_lease.issuer_id != intent.issuer_id:
            return ControllerBoundRejectionCode.CAPABILITY_ISSUER_MISMATCH
        if not policy_verifier.verify(capability_lease.canonical_bytes, capability_lease.signature):
            return ControllerBoundRejectionCode.CAPABILITY_SIGNATURE_INVALID
        if intent.device_id != capability_lease.device_id:
            return ControllerBoundRejectionCode.DEVICE_MISMATCH
        if intent.capability_lease_digest != capability_lease.payload_digest:
            return ControllerBoundRejectionCode.CAPABILITY_MISMATCH
        controller_verifier = self.controller_verifiers.get(controller_evidence.issuer_id)
        if controller_verifier is None:
            return ControllerBoundRejectionCode.CONTROLLER_ISSUER_UNKNOWN
        if not controller_verifier.verify(controller_evidence.canonical_bytes, controller_evidence.signature):
            return ControllerBoundRejectionCode.CONTROLLER_SIGNATURE_INVALID
        binding = (intent.resource_id, intent.controller_id, intent.controller_lease_digest, intent.fencing_token)
        expected_binding = (controller_evidence.resource_id, controller_evidence.controller_id, controller_evidence.evidence_digest, controller_evidence.fencing_token)
        if binding != expected_binding:
            return ControllerBoundRejectionCode.CONTROLLER_BINDING_MISMATCH
        if intent.operation not in controller_evidence.scope:
            return ControllerBoundRejectionCode.SCOPE_MISMATCH
        if intent.created_at < capability_lease.issued_at or intent.created_at < controller_evidence.issued_at or now < intent.created_at:
            return ControllerBoundRejectionCode.NOT_YET_VALID
        if now >= intent.expires_at or now >= capability_lease.expires_at or now >= controller_evidence.expires_at:
            return ControllerBoundRejectionCode.EXPIRED
        if intent.expires_at > capability_lease.expires_at or intent.expires_at > controller_evidence.expires_at:
            return ControllerBoundRejectionCode.EXPIRED
        if self.active_controller_authority is not None:
            active_lease = ActiveControllerLease(resource_id=controller_evidence.resource_id, controller_id=controller_evidence.controller_id, fencing_token=controller_evidence.fencing_token, issued_at=controller_evidence.issued_at, expires_at=controller_evidence.expires_at)
            if self.active_controller_authority.validate(active_lease, now=now) is not ControllerLeaseDecision.ALLOW:
                return ControllerBoundRejectionCode.STALE_FENCE
        nonce_key = (intent.issuer_id, intent.nonce)
        with self._lock:
            if nonce_key in self._seen_nonces:
                return ControllerBoundRejectionCode.REPLAY
            self._seen_nonces.add(nonce_key)
            return intent
