import json
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from src.control.controller_lease_grant import SignedControllerLeaseGrant
from src.control.remote_controller_protocol import SignedAtomicControllerResult


class ControllerCommandDecision(Enum):
    ALLOW = "ALLOW"
    MALFORMED = "MALFORMED"
    GRANT_MISMATCH = "GRANT_MISMATCH"
    KEY_MISMATCH = "KEY_MISMATCH"
    UNKNOWN_CONTROLLER_KEY = "UNKNOWN_CONTROLLER_KEY"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"


@dataclass(frozen=True)
class SignedControllerCommandProof:
    grant_digest: str
    command_id: str
    command_sequence: int
    action_digest: str
    controller_key_id: str
    signature: str = ""

    @property
    def canonical_bytes(self) -> bytes:
        payload = {
            "grant_digest": self.grant_digest,
            "command_id": self.command_id,
            "command_sequence": self.command_sequence,
            "action_digest": self.action_digest,
            "controller_key_id": self.controller_key_id,
        }
        return json.dumps(payload, sort_keys=True).encode("utf-8")


class ControllerCommandProofVerifier:
    def __init__(self, controller_verifiers) -> None:
        self._controller_verifiers = dict(controller_verifiers)

    def validate(self, proof: SignedControllerCommandProof, grant) -> ControllerCommandDecision:
        if not isinstance(proof, SignedControllerCommandProof) or not isinstance(grant, SignedControllerLeaseGrant):
            return ControllerCommandDecision.MALFORMED
        identifiers = (proof.grant_digest, proof.command_id, proof.action_digest, proof.controller_key_id, proof.signature)
        if any(not isinstance(value, str) or not value.strip() for value in identifiers):
            return ControllerCommandDecision.MALFORMED
        if type(proof.command_sequence) is not int or proof.command_sequence <= 0:
            return ControllerCommandDecision.MALFORMED
        expected_grant_digest = sha256(grant.canonical_bytes).hexdigest()
        if proof.grant_digest != expected_grant_digest:
            return ControllerCommandDecision.GRANT_MISMATCH
        if proof.controller_key_id != grant.controller_key_id:
            return ControllerCommandDecision.KEY_MISMATCH
        verifier = self._controller_verifiers.get(proof.controller_key_id)
        if verifier is None:
            return ControllerCommandDecision.UNKNOWN_CONTROLLER_KEY
        if not verifier.verify(proof.canonical_bytes, proof.signature):
            return ControllerCommandDecision.INVALID_SIGNATURE
        return ControllerCommandDecision.ALLOW

    def validate_remote(self, proof: SignedControllerCommandProof, result) -> ControllerCommandDecision:
        if not isinstance(proof,SignedControllerCommandProof) or not isinstance(result,SignedAtomicControllerResult):
            return ControllerCommandDecision.MALFORMED
        identifiers=(proof.grant_digest,proof.command_id,proof.action_digest,proof.controller_key_id,proof.signature)
        if any(not isinstance(value,str) or not value.strip() for value in identifiers):
            return ControllerCommandDecision.MALFORMED
        if type(proof.command_sequence) is not int or proof.command_sequence<=0:
            return ControllerCommandDecision.MALFORMED
        expected_result_digest=sha256(result.canonical_bytes).hexdigest()
        if proof.grant_digest!=expected_result_digest:
            return ControllerCommandDecision.GRANT_MISMATCH
        if proof.controller_key_id!=result.controller_key_id:
            return ControllerCommandDecision.KEY_MISMATCH
        verifier=self._controller_verifiers.get(proof.controller_key_id)
        if verifier is None:
            return ControllerCommandDecision.UNKNOWN_CONTROLLER_KEY
        if not verifier.verify(proof.canonical_bytes,proof.signature):
            return ControllerCommandDecision.INVALID_SIGNATURE
        return ControllerCommandDecision.ALLOW
