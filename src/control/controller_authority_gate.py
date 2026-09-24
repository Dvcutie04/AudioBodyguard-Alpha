import fcntl
import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from enum import Enum

from src.control.active_controller_lease import ActiveControllerLease,ControllerLeaseDecision
from src.control.controller_command_proof import ControllerCommandDecision
from src.control.controller_lease_grant import ControllerLeaseGrantDecision
from src.control.remote_controller_protocol import AtomicControllerRequest,RemoteControllerResultDecision,SignedAtomicControllerResult


class ControllerAuthorityDecision(Enum):
    ALLOW = "ALLOW"
    GRANT_REJECTED = "GRANT_REJECTED"
    STALE_FENCE = "STALE_FENCE"
    LEASE_REJECTED = "LEASE_REJECTED"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    REPLAYED_SEQUENCE = "REPLAYED_SEQUENCE"


class ControllerAuthorityGate:
    def __init__(self, authority, grant_verifier, command_verifier, state_path=None, remote_result_verifier=None) -> None:
        self._authority = authority
        self._grant_verifier = grant_verifier
        self._command_verifier = command_verifier
        self._remote_result_verifier = remote_result_verifier
        self._lock = threading.RLock()
        self._state_path = Path(state_path) if state_path is not None else None
        self._lock_path = Path(str(self._state_path)+".lock") if self._state_path is not None else None
        self._sequence_watermarks = {}
        with self._state_guard():
            self._load_state()

    @contextmanager
    def _state_guard(self):
        with self._lock:
            if self._lock_path is None:
                yield
                return
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock_path.open("a+") as lock_handle:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    def _load_state(self) -> None:
        if self._state_path is None or not self._state_path.exists():
            self._sequence_watermarks = {}
            return
        with self._state_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if type(raw) is not dict or set(raw) != {"version", "resources"} or raw.get("version") != 1 or type(raw.get("resources")) is not dict:
            raise ValueError("invalid controller command watermark state")
        loaded = {}
        for resource_id, item in raw["resources"].items():
            if not isinstance(resource_id, str) or not resource_id.strip() or type(item) is not dict or set(item) != {"fencing_token", "highest_sequence"}:
                raise ValueError("invalid controller command watermark state")
            fencing_token = item["fencing_token"]
            highest_sequence = item["highest_sequence"]
            if type(fencing_token) is not int or fencing_token <= 0 or type(highest_sequence) is not int or highest_sequence <= 0:
                raise ValueError("invalid controller command watermark state")
            loaded[resource_id] = (fencing_token, highest_sequence)
        self._sequence_watermarks = loaded

    def _save_state(self, watermarks) -> None:
        if self._state_path is None:
            return
        parent = self._state_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "resources": {resource_id: {"fencing_token": values[0], "highest_sequence": values[1]} for resource_id, values in sorted(watermarks.items())}}
        descriptor, temporary_name = tempfile.mkstemp(prefix=self._state_path.name+".", suffix=".tmp", dir=str(parent))
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self._state_path)
        finally:
            temporary_path = Path(temporary_name)
            if temporary_path.exists():
                temporary_path.unlink()

    @property
    def lease_authority(self):
        return self._authority

    def validate_remote(self, *, result, request, proof, now, expected_action_digest=None) -> ControllerAuthorityDecision:
        with self._state_guard():
            if self._state_path is not None:
                self._load_state()
            if not isinstance(request,AtomicControllerRequest) or not isinstance(result,SignedAtomicControllerResult) or self._remote_result_verifier is None:
                return ControllerAuthorityDecision.GRANT_REJECTED
            result_decision=self._remote_result_verifier.validate(result,request=request,now=now)
            if result_decision is not RemoteControllerResultDecision.ALLOW:
                return ControllerAuthorityDecision.GRANT_REJECTED
            lease=ActiveControllerLease(resource_id=result.resource_id,controller_id=result.controller_id,fencing_token=result.fencing_token,issued_at=result.issued_at,expires_at=result.expires_at)
            lease_decision=self._authority.validate(lease,now=now)
            if lease_decision is ControllerLeaseDecision.STALE_FENCE:
                return ControllerAuthorityDecision.STALE_FENCE
            if lease_decision is not ControllerLeaseDecision.ALLOW:
                return ControllerAuthorityDecision.LEASE_REJECTED
            command_decision=self._command_verifier.validate_remote(proof,result)
            if command_decision is not ControllerCommandDecision.ALLOW:
                return ControllerAuthorityDecision.COMMAND_REJECTED
            if expected_action_digest is not None:
                if not isinstance(expected_action_digest,str) or not expected_action_digest.strip() or proof.action_digest!=expected_action_digest:
                    return ControllerAuthorityDecision.COMMAND_REJECTED
            watermark=self._sequence_watermarks.get(result.resource_id)
            if watermark is not None:
                accepted_fence,highest_sequence=watermark
                if result.fencing_token<accepted_fence:
                    return ControllerAuthorityDecision.STALE_FENCE
                if result.fencing_token==accepted_fence and proof.command_sequence<=highest_sequence:
                    return ControllerAuthorityDecision.REPLAYED_SEQUENCE
            updated_watermarks=dict(self._sequence_watermarks)
            updated_watermarks[result.resource_id]=(result.fencing_token,proof.command_sequence)
            self._save_state(updated_watermarks)
            self._sequence_watermarks=updated_watermarks
            return ControllerAuthorityDecision.ALLOW

    def validate(self, *, grant, proof, now, expected_action_digest=None) -> ControllerAuthorityDecision:
        with self._state_guard():
            if self._state_path is not None:
                self._load_state()
            grant_decision = self._grant_verifier.validate(grant, now=now)
            if grant_decision is not ControllerLeaseGrantDecision.ALLOW:
                return ControllerAuthorityDecision.GRANT_REJECTED
            lease = ActiveControllerLease(resource_id=grant.resource_id,controller_id=grant.controller_id,fencing_token=grant.fencing_token,issued_at=grant.issued_at,expires_at=grant.expires_at)
            lease_decision = self._authority.validate(lease, now=now)
            if lease_decision is ControllerLeaseDecision.STALE_FENCE:
                return ControllerAuthorityDecision.STALE_FENCE
            if lease_decision is not ControllerLeaseDecision.ALLOW:
                return ControllerAuthorityDecision.LEASE_REJECTED
            command_decision = self._command_verifier.validate(proof, grant)
            if command_decision is not ControllerCommandDecision.ALLOW:
                return ControllerAuthorityDecision.COMMAND_REJECTED
            if expected_action_digest is not None:
                if not isinstance(expected_action_digest, str) or not expected_action_digest.strip() or proof.action_digest != expected_action_digest:
                    return ControllerAuthorityDecision.COMMAND_REJECTED
            watermark = self._sequence_watermarks.get(grant.resource_id)
            if watermark is not None:
                accepted_fence, highest_sequence = watermark
                if grant.fencing_token < accepted_fence:
                    return ControllerAuthorityDecision.STALE_FENCE
                if grant.fencing_token == accepted_fence and proof.command_sequence <= highest_sequence:
                    return ControllerAuthorityDecision.REPLAYED_SEQUENCE
            updated_watermarks = dict(self._sequence_watermarks)
            updated_watermarks[grant.resource_id] = (grant.fencing_token, proof.command_sequence)
            self._save_state(updated_watermarks)
            self._sequence_watermarks = updated_watermarks
            return ControllerAuthorityDecision.ALLOW
