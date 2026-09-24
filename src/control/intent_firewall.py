import time
from enum import Enum
from typing import Dict, Set, Union
from src.control.crypto_identity import KeyVerifier
from src.control.capability_lease import SignedCapabilityLease
from src.control.authorized_intent import SignedActionIntent


class AuthRejectionCode(Enum):
    AUTH_SIGNATURE_INVALID = "AUTH_SIGNATURE_INVALID"
    AUTH_DEVICE_MISMATCH = "AUTH_DEVICE_MISMATCH"
    AUTH_LEASE_MISMATCH = "AUTH_LEASE_MISMATCH"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_REPLAY = "AUTH_REPLAY"
    AUTH_ISSUER_UNKNOWN = "AUTH_ISSUER_UNKNOWN"


class IntentFirewall:
    def __init__(self, trusted_verifiers: Dict[str, KeyVerifier]):
        self.trusted_verifiers = trusted_verifiers
        self.seen_nonces: Set[str] = set()

    def validate_intent(
        self, intent: SignedActionIntent, lease: SignedCapabilityLease
    ) -> Union[SignedActionIntent, AuthRejectionCode]:
        if intent.issuer_id not in self.trusted_verifiers:
            return AuthRejectionCode.AUTH_ISSUER_UNKNOWN

        verifier = self.trusted_verifiers[intent.issuer_id]
        if not verifier.verify(intent.canonical_bytes, intent.signature):
            return AuthRejectionCode.AUTH_SIGNATURE_INVALID

        if intent.device_id != lease.device_id:
            return AuthRejectionCode.AUTH_DEVICE_MISMATCH

        if intent.capability_lease_digest != lease.payload_digest:
            return AuthRejectionCode.AUTH_LEASE_MISMATCH

        now = time.time()
        if intent.expires_at < now or lease.expires_at < now:
            return AuthRejectionCode.AUTH_EXPIRED

        if intent.nonce in self.seen_nonces:
            return AuthRejectionCode.AUTH_REPLAY

        self.seen_nonces.add(intent.nonce)
        return intent
