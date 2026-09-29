import time
import math
import threading
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
    AUTH_INVALID_INPUT = "AUTH_INVALID_INPUT"
    AUTH_NOT_YET_VALID = "AUTH_NOT_YET_VALID"
    AUTH_PROTOCOL_MISMATCH = "AUTH_PROTOCOL_MISMATCH"


class IntentFirewall:
    def __init__(self, trusted_verifiers: Dict[str, KeyVerifier]):
        self.trusted_verifiers = trusted_verifiers
        self.seen_nonces: Set[str] = set()
        self._lock = threading.Lock()

    def validate_intent(
        self, intent: SignedActionIntent, lease: SignedCapabilityLease
    ) -> Union[SignedActionIntent, AuthRejectionCode]:
        if not isinstance(intent, SignedActionIntent) or not isinstance(lease, SignedCapabilityLease):
            return AuthRejectionCode.AUTH_INVALID_INPUT
        if any(type(value) is not str or not value.strip() for value in
               (intent.issuer_id, lease.issuer_id, intent.nonce, intent.protocol_version, lease.protocol_version)):
            return AuthRejectionCode.AUTH_INVALID_INPUT
        if intent.issuer_id not in self.trusted_verifiers:
            return AuthRejectionCode.AUTH_ISSUER_UNKNOWN

        verifier = self.trusted_verifiers[intent.issuer_id]
        try:
            if not verifier.verify(intent.canonical_bytes, intent.signature):
                return AuthRejectionCode.AUTH_SIGNATURE_INVALID
            if lease.issuer_id != intent.issuer_id or not verifier.verify(lease.canonical_bytes, lease.signature):
                return AuthRejectionCode.AUTH_LEASE_MISMATCH
        except (TypeError, ValueError, OverflowError):
            return AuthRejectionCode.AUTH_SIGNATURE_INVALID

        if intent.device_id != lease.device_id:
            return AuthRejectionCode.AUTH_DEVICE_MISMATCH

        if intent.capability_lease_digest != lease.payload_digest:
            return AuthRejectionCode.AUTH_LEASE_MISMATCH
        if intent.protocol_version != lease.protocol_version:
            return AuthRejectionCode.AUTH_PROTOCOL_MISMATCH

        now = time.time()
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in
               (now, intent.created_at, intent.expires_at, lease.issued_at, lease.expires_at)):
            return AuthRejectionCode.AUTH_INVALID_INPUT
        if (now >= intent.expires_at or now >= lease.expires_at or
                intent.expires_at <= intent.created_at or lease.expires_at <= lease.issued_at or
                intent.expires_at > lease.expires_at):
            return AuthRejectionCode.AUTH_EXPIRED
        if now < intent.created_at or now < lease.issued_at or intent.created_at < lease.issued_at:
            return AuthRejectionCode.AUTH_NOT_YET_VALID

        with self._lock:
            if intent.nonce in self.seen_nonces:
                return AuthRejectionCode.AUTH_REPLAY
            self.seen_nonces.add(intent.nonce)
            return intent
