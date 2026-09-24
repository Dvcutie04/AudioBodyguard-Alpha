from __future__ import annotations

from src.control.authorized_intent import SignedActionIntent


class TrustedIntentIssuer:
    def __init__(self, key_pair, protocol_version: str):
        self._key_pair = key_pair
        self.protocol_version = protocol_version

    def issue(self, *, candidate, lease, policy_digest: str, intent_id: str, transaction_id: str, nonce: str, created_at: float, expires_at: float) -> SignedActionIntent:
        if self._key_pair.key_id != lease.issuer_id:
            raise ValueError("capability lease issuer does not match trusted intent issuer")
        if not self._key_pair.public_verifier.verify(lease.canonical_bytes, lease.signature):
            raise ValueError("capability lease signature is invalid")
        if candidate.target_id != lease.device_id:
            raise ValueError("candidate target does not match capability lease device")
        if lease.protocol_version != self.protocol_version:
            raise ValueError("capability lease protocol does not match trusted intent issuer protocol")
        import math
        if not math.isfinite(created_at) or not math.isfinite(expires_at):
            raise ValueError("intent validity timestamps must be finite")
        if not math.isfinite(lease.issued_at) or not math.isfinite(lease.expires_at):
            raise ValueError("capability lease validity timestamps must be finite")
        if lease.issued_at >= lease.expires_at:
            raise ValueError("capability lease validity window is invalid")
        if created_at >= expires_at:
            raise ValueError("intent validity window is invalid")
        if created_at < lease.issued_at or expires_at > lease.expires_at:
            raise ValueError("intent validity window must be contained within capability lease validity window")
        if not policy_digest or not policy_digest.strip():
            raise ValueError("policy digest is required")
        if not transaction_id or not transaction_id.strip():
            raise ValueError("transaction id is required")
        if not intent_id or not intent_id.strip():
            raise ValueError("intent id is required")
        if not nonce or not nonce.strip():
            raise ValueError("nonce is required")
        if not candidate.operation or not candidate.operation.strip():
            raise ValueError("operation is required")
        if not candidate.extension_id or not candidate.extension_id.strip():
            raise ValueError("extension id is required")
        intent = SignedActionIntent(
            intent_id=intent_id,
            device_id=candidate.target_id,
            operation=candidate.operation,
            parameters=dict(candidate.parameters),
            issuer_id=self._key_pair.key_id,
            policy_digest=policy_digest,
            capability_lease_digest=lease.payload_digest,
            created_at=created_at,
            expires_at=expires_at,
            nonce=nonce,
            transaction_id=transaction_id,
            protocol_version=self.protocol_version,
            signature="",
        )
        intent.signature = self._key_pair.sign(intent.canonical_bytes)
        return intent
