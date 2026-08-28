import base64
import hashlib
from typing import Tuple, Union
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


class KeyPair:
    """
    Wrapper for Ed25519 private/public key management and signing.
    Used exclusively by authority components (e.g., Safety Governor).
    """
    def __init__(self, private_key: ed25519.Ed25519PrivateKey):
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @classmethod
    def generate(cls) -> "KeyPair":
        """Generates a new secure Ed25519 keypair."""
        return cls(ed25519.Ed25519PrivateKey.generate())

    @property
    def key_id(self) -> str:
        """Computes a deterministic SHA-256 Key ID from the raw public key bytes."""
        raw_pub = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return hashlib.sha256(raw_pub).hexdigest()[:16]

    @property
    def public_verifier(self) -> "PublicVerifier":
        """Returns the public verification interface."""
        return PublicVerifier(self._public_key, self.key_id)

    def sign(self, payload: bytes) -> str:
        """Signs raw canonical bytes and returns a base64-encoded signature string."""
        raw_signature = self._private_key.sign(payload)
        return base64.b64encode(raw_signature).decode("utf-8")

    def export_private_bytes(self) -> bytes:
        """Exports raw 32-byte private key."""
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )


class PublicVerifier:
    """
    Verification interface holding ONLY public key material.
    Safe for distribution across Routers, Device Adapters, and Hardware Nodes.
    """
    def __init__(self, public_key: ed25519.Ed25519PublicKey, key_id: str):
        self._public_key = public_key
        self.key_id = key_id

    @classmethod
    def from_base64(cls, base64_key: str, key_id: str) -> "PublicVerifier":
        """Instantiates a verifier from a base64-encoded raw public key."""
        raw_bytes = base64.b64decode(base64_key.encode("utf-8"))
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)
        return cls(pub_key, key_id)

    def to_base64(self) -> str:
        """Exports public key as base64 string for manifest registration."""
        raw_pub = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(raw_pub).decode("utf-8")

    def verify(self, payload: bytes, signature_base64: str) -> bool:
        """
        Verifies an Ed25519 signature against canonical payload bytes.
        Returns True if signature is cryptographically valid, False otherwise.
        """
        try:
            raw_signature = base64.b64decode(signature_base64.encode("utf-8"))
            self._public_key.verify(raw_signature, payload)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False
