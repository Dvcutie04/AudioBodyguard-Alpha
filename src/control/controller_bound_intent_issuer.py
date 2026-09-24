import math
from dataclasses import replace

from src.control.capability_lease import SignedCapabilityLease
from src.control.controller_bound_intent import ControllerBoundActionIntent
from src.control.controller_lease_evidence import SignedControllerLeaseEvidence
from src.control.crypto_identity import KeyVerifier
from src.extensions.normalization import NormalizedCandidate


class ControllerBoundIntentIssuer:
    def __init__(self, key_pair, *, controller_verifiers: dict[str, KeyVerifier], protocol_version: str, candidate_admission=None) -> None:
        self._key_pair = key_pair
        self._controller_verifiers = dict(controller_verifiers)
        self.protocol_version = protocol_version
        self._candidate_admission = candidate_admission

    @staticmethod
    def _finite(value, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        return float(value)

    def issue(self, *, candidate, capability_lease, controller_evidence, policy_digest: str, intent_id: str, transaction_id: str, nonce: str, created_at: float, expires_at: float, expected_pre_state_digest: str | None = None) -> ControllerBoundActionIntent:
        if not isinstance(candidate, NormalizedCandidate) or not isinstance(capability_lease, SignedCapabilityLease) or not isinstance(controller_evidence, SignedControllerLeaseEvidence):
            raise ValueError("candidate, capability lease, and controller evidence must have valid types")
        if str(candidate.operation).upper()=="SET_PLAYBACK_POSITION":
            if self._candidate_admission is None:
                raise ValueError("trusted candidate admission is required")
            if self._candidate_admission(candidate) is not True:
                raise ValueError("trusted candidate admission rejected candidate")
        if self._key_pair.key_id != capability_lease.issuer_id:
            raise ValueError("capability lease issuer does not match protected intent issuer")
        if not self._key_pair.public_verifier.verify(capability_lease.canonical_bytes, capability_lease.signature):
            raise ValueError("capability lease signature is invalid")
        if candidate.target_id != capability_lease.device_id:
            raise ValueError("candidate target does not match capability lease device")
        if capability_lease.protocol_version != self.protocol_version:
            raise ValueError("capability lease protocol does not match protected intent issuer protocol")
        controller_verifier = self._controller_verifiers.get(controller_evidence.issuer_id)
        if controller_verifier is None:
            raise ValueError("controller evidence issuer is not trusted")
        if not controller_verifier.verify(controller_evidence.canonical_bytes, controller_evidence.signature):
            raise ValueError("controller evidence signature is invalid")
        if candidate.operation not in controller_evidence.scope:
            raise ValueError("candidate operation is outside controller evidence scope")
        intent_start = self._finite(created_at, "created_at")
        intent_end = self._finite(expires_at, "expires_at")
        capability_start = self._finite(capability_lease.issued_at, "capability_lease.issued_at")
        capability_end = self._finite(capability_lease.expires_at, "capability_lease.expires_at")
        controller_start = self._finite(controller_evidence.issued_at, "controller_evidence.issued_at")
        controller_end = self._finite(controller_evidence.expires_at, "controller_evidence.expires_at")
        if capability_start >= capability_end:
            raise ValueError("capability lease validity window is invalid")
        if controller_start >= controller_end:
            raise ValueError("controller evidence validity window is invalid")
        if intent_start >= intent_end:
            raise ValueError("intent validity window is invalid")
        if intent_start < capability_start or intent_end > capability_end:
            raise ValueError("intent validity window must be contained within capability lease validity window")
        if intent_start < controller_start or intent_end > controller_end:
            raise ValueError("intent validity window must be contained within controller evidence validity window")
        unsigned = ControllerBoundActionIntent(
            intent_id=intent_id,
            device_id=candidate.target_id,
            operation=candidate.operation,
            parameters=dict(candidate.parameters),
            issuer_id=self._key_pair.key_id,
            policy_digest=policy_digest,
            capability_lease_digest=capability_lease.payload_digest,
            resource_id=controller_evidence.resource_id,
            controller_id=controller_evidence.controller_id,
            controller_lease_digest=controller_evidence.evidence_digest,
            fencing_token=controller_evidence.fencing_token,
            created_at=intent_start,
            expires_at=intent_end,
            nonce=nonce,
            transaction_id=transaction_id,
            protocol_version=self.protocol_version,
            expected_pre_state_digest=expected_pre_state_digest,
        )
        return replace(unsigned, signature=self._key_pair.sign(unsigned.canonical_bytes))
