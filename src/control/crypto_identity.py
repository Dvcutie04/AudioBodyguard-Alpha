import hashlib
import hmac
import os


class KeyVerifier:
    def __init__(self, key_id: str, secret_key: bytes):
        self.key_id = key_id
        self._secret_key = secret_key

    def verify(self, data: bytes, signature: str) -> bool:
        expected = hmac.new(self._secret_key, data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


class KeyPair:
    def __init__(self, key_id: str, secret_key: bytes):
        self.key_id = key_id
        self._secret_key = secret_key
        self.public_verifier = KeyVerifier(key_id, secret_key)

    @classmethod
    def generate(cls, key_id: str = None) -> "KeyPair":
        secret = os.urandom(32)
        kid = key_id or f"key_{secret[:4].hex()}"
        return cls(kid, secret)

    def sign(self, data: bytes) -> str:
        return hmac.new(self._secret_key, data, hashlib.sha256).hexdigest()
