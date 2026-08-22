import unittest
from audio_engine.symmetric_auth import SymmetricAuthenticator
from dataclasses import dataclass, field
from typing import List

@dataclass
class AuthDummyEnv:
    node_id: str = "node_1"
    sequence_id: int = 1
    decision_state: str = "OK"
    evidence_digest: str = "abc"
    trust_epoch: int = 1
    effective_trust: float = 1.0
    trust_reason_codes: List[str] = field(default_factory=list)

class TestSymmetricAuthVerify(unittest.TestCase):
    def test_verify_valid(self):
        key = b"1234567890abcdef"
        auth = SymmetricAuthenticator(key)
        env = AuthDummyEnv()
        tag = auth.sign(env)
        self.assertTrue(auth.verify(env, tag))

if __name__ == "__main__":
    unittest.main()
