import time
from enum import Enum
from typing import Union, Dict

from src.control.crypto_identity import PublicVerifier
from src.control.capability_lease import SignedCapabilityLease
from src.control.authorized_intent import SignedActionIntent

class AuthRejectionCode(Enum):
    """Structured terminal rejection states for failed authority constraints."""
    AUTH_SIGNATURE_INVALID = "AUTH_SIGNATURE_INVALID"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_REPLAY = "AUTH_REPLAY"
    AUTH_DEVICE_MISMATCH = "AUTH_DEVICE_MISMATCH"
    AUTH_ISSUER_UNKNOWN = "AUTH_ISSUER_UNKNOWN"
    AUTH_LEASE_MISMATCH = "AUTH_LEASE_MISMATCH"

class IntentFirewall:
    """
    The cryptographic boundary between intelligence and physical execution.
    Holds ONLY public keys. Cannot forge authority. 
    """
    def __init__(self, trusted_verifiers: Dict[str, PublicVerifier]):
        self.trusted_verifiers = trusted_verifiers
        self.seen_nonces = set()

    def validate_intent(
        self, 
        intent: SignedActionIntent, 
        lease: SignedCapabilityLease
    ) -> Union[SignedActionIntent, AuthRejectionCode]:
        
        now = time.time()

        # 1. Issuer Known & Consistent
        verifier = self.trusted_verifiers.get(intent.issuer_id)
        if not verifier or lease.issuer_id != intent.issuer_id:
            return AuthRejectionCode.AUTH_ISSUER_UNKNOWN

        # 2. Temporal Freshness & Replay Prevention
        if intent.expires_at < now or lease.expires_at < now:
            return AuthRejectionCode.AUTH_EXPIRED
            
        if intent.nonce in self.seen_nonces or lease.nonce in self.seen_nonces:
            return AuthRejectionCode.AUTH_REPLAY

        # 3. Scope & Structural Binding
        if intent.device_id != lease.device_id:
            return AuthRejectionCode.AUTH_DEVICE_MISMATCH
            
        if intent.capability_lease_digest != lease.payload_digest:
            return AuthRejectionCode.AUTH_LEASE_MISMATCH

        # 4. Cryptographic Authenticity (The Hard Gates)
        if not verifier.verify(lease.canonical_bytes, lease.signature):
            return AuthRejectionCode.AUTH_SIGNATURE_INVALID
            
        if not verifier.verify(intent.canonical_bytes, intent.signature):
            return AuthRejectionCode.AUTH_SIGNATURE_INVALID

        # 5. Lock in the execution (Commit Nonces)
        self.seen_nonces.add(intent.nonce)
        self.seen_nonces.add(lease.nonce)

        return intent
