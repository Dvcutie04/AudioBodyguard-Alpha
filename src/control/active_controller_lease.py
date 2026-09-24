import fcntl
import json
import math
import os
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict

from src.control.controller_reauthorization import SignedControllerReauthorizationGrant


class ControllerLeaseDecision(Enum):
    ALLOW = "ALLOW"
    STALE_FENCE = "STALE_FENCE"
    EXPIRED = "EXPIRED"
    UNKNOWN_RESOURCE = "UNKNOWN_RESOURCE"


@dataclass(frozen=True)
class ActiveControllerLease:
    resource_id: str
    controller_id: str
    fencing_token: int
    issued_at: float
    expires_at: float


class ActiveControllerLeaseAuthority:
    def __init__(self, state_path=None, recovery_verifiers=None) -> None:
        self._lock = threading.RLock()
        self._active: Dict[str, ActiveControllerLease] = {}
        self._highest_tokens: Dict[str, int] = {}
        self._used_reauthorization_nonces: set[tuple[str, str]] = set()
        self._recovery_verifiers = dict(recovery_verifiers or {})
        self._state_path = Path(state_path) if state_path is not None else None
        self._lock_path = Path(str(self._state_path) + ".lock") if self._state_path is not None else None
        with self._state_guard(exclusive=False):
            pass

    @staticmethod
    def _validate_identifier(value: str, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty string")

    @staticmethod
    def _validate_time(value: float, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        return float(value)

    @classmethod
    def _validate_ttl(cls, ttl_seconds: float) -> float:
        ttl = cls._validate_time(ttl_seconds, "ttl_seconds")
        if ttl <= 0.0:
            raise ValueError("ttl_seconds must be positive")
        return ttl

    def _load_state(self) -> None:
        if self._state_path is None or not self._state_path.exists():
            self._active = {}
            self._highest_tokens = {}
            self._used_reauthorization_nonces = set()
            return
        with self._state_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if type(raw) is not dict or type(raw.get("version")) is not int:
            raise ValueError("invalid active controller lease state")
        if raw["version"] == 1 and set(raw) == {"version", "resources"} and type(raw["resources"]) is dict:
            resources = raw["resources"]
            used_nonces = set()
        elif raw["version"] == 2 and set(raw) == {"version", "resources", "used_reauthorization_nonces"} and type(raw["resources"]) is dict and type(raw["used_reauthorization_nonces"]) is list:
            resources = raw["resources"]
            used_nonces = set()
            for item in raw["used_reauthorization_nonces"]:
                if type(item) is not list or len(item) != 2 or any(type(value) is not str or not value.strip() for value in item):
                    raise ValueError("invalid controller reauthorization nonce record")
                nonce_key = (item[0], item[1])
                if nonce_key in used_nonces:
                    raise ValueError("invalid controller reauthorization nonce record")
                used_nonces.add(nonce_key)
        else:
            raise ValueError("invalid active controller lease state")
        active = {}
        highest_tokens = {}
        required = {"controller_id", "fencing_token", "issued_at", "expires_at", "highest_token"}
        for resource_id, record in resources.items():
            if type(resource_id) is not str or not resource_id.strip() or type(record) is not dict or set(record) != required:
                raise ValueError("invalid active controller lease record")
            controller_id = record["controller_id"]
            fencing_token = record["fencing_token"]
            highest_token = record["highest_token"]
            issued_at = record["issued_at"]
            expires_at = record["expires_at"]
            if type(controller_id) is not str or not controller_id.strip() or type(fencing_token) is not int or fencing_token <= 0 or type(highest_token) is not int or highest_token < fencing_token:
                raise ValueError("invalid active controller lease record")
            if isinstance(issued_at, bool) or not isinstance(issued_at, (int, float)) or not math.isfinite(issued_at) or isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)) or not math.isfinite(expires_at) or float(expires_at) <= float(issued_at):
                raise ValueError("invalid active controller lease record")
            active[resource_id] = ActiveControllerLease(resource_id, controller_id, fencing_token, float(issued_at), float(expires_at))
            highest_tokens[resource_id] = highest_token
        self._active = active
        self._highest_tokens = highest_tokens
        self._used_reauthorization_nonces = used_nonces

    def _save_state(self, active, highest_tokens, used_reauthorization_nonces=None) -> None:
        if self._state_path is None:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        resources = {}
        for resource_id, lease in active.items():
            resources[resource_id] = {"controller_id": lease.controller_id, "fencing_token": lease.fencing_token, "issued_at": lease.issued_at, "expires_at": lease.expires_at, "highest_token": highest_tokens[resource_id]}
        used_nonces = self._used_reauthorization_nonces if used_reauthorization_nonces is None else used_reauthorization_nonces
        payload = {"version": 2, "resources": resources, "used_reauthorization_nonces": [list(item) for item in sorted(used_nonces)]}
        descriptor, temp_path = tempfile.mkstemp(prefix=self._state_path.name + ".", suffix=".tmp", dir=str(self._state_path.parent))
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self._state_path)
            directory_fd = os.open(str(self._state_path.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @contextmanager
    def _state_guard(self, *, exclusive):
        with self._lock:
            if self._state_path is None:
                yield
                return
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock_path.open("a+") as lock_handle:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                try:
                    self._load_state()
                    yield
                finally:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    def acquire(self, *, resource_id: str, controller_id: str, now: float, ttl_seconds: float) -> ActiveControllerLease:
        self._validate_identifier(resource_id, "resource_id")
        self._validate_identifier(controller_id, "controller_id")
        current_time = self._validate_time(now, "now")
        ttl = self._validate_ttl(ttl_seconds)
        with self._state_guard(exclusive=True):
            current = self._active.get(resource_id)
            if current is not None and current_time < current.expires_at:
                raise RuntimeError("resource already has an active controller")
            token = self._highest_tokens.get(resource_id, 0) + 1
            lease = ActiveControllerLease(resource_id, controller_id, token, current_time, current_time + ttl)
            active = dict(self._active)
            highest_tokens = dict(self._highest_tokens)
            active[resource_id] = lease
            highest_tokens[resource_id] = token
            self._save_state(active, highest_tokens)
            self._active = active
            self._highest_tokens = highest_tokens
            return lease

    def handoff(self, *, current_lease: ActiveControllerLease, next_controller_id: str, now: float, ttl_seconds: float) -> ActiveControllerLease:
        if not isinstance(current_lease, ActiveControllerLease):
            raise ValueError("current_lease must be an ActiveControllerLease")
        self._validate_identifier(next_controller_id, "next_controller_id")
        current_time = self._validate_time(now, "now")
        ttl = self._validate_ttl(ttl_seconds)
        with self._state_guard(exclusive=True):
            active_lease = self._active.get(current_lease.resource_id)
            if active_lease != current_lease:
                raise RuntimeError("current lease is not active")
            if current_time >= active_lease.expires_at:
                raise RuntimeError("current lease has expired")
            token = self._highest_tokens.get(active_lease.resource_id, active_lease.fencing_token) + 1
            lease = ActiveControllerLease(active_lease.resource_id, next_controller_id, token, current_time, current_time + ttl)
            active = dict(self._active)
            highest_tokens = dict(self._highest_tokens)
            active[active_lease.resource_id] = lease
            highest_tokens[active_lease.resource_id] = token
            self._save_state(active, highest_tokens)
            self._active = active
            self._highest_tokens = highest_tokens
            return lease

    def reauthorize(self, grant: SignedControllerReauthorizationGrant, *, now: float, ttl_seconds: float) -> ActiveControllerLease:
        if not isinstance(grant, SignedControllerReauthorizationGrant):
            raise ValueError("grant must be a SignedControllerReauthorizationGrant")
        current_time = self._validate_time(now, "now")
        ttl = self._validate_ttl(ttl_seconds)
        verifier = self._recovery_verifiers.get(grant.issuer_id)
        if verifier is None:
            raise RuntimeError("controller reauthorization issuer is not trusted")
        if not verifier.verify(grant.canonical_bytes, grant.signature):
            raise RuntimeError("controller reauthorization signature is invalid")
        if current_time < grant.issued_at:
            raise RuntimeError("controller reauthorization grant is not yet valid")
        if current_time >= grant.expires_at:
            raise RuntimeError("controller reauthorization grant has expired")
        nonce_key = (grant.issuer_id, grant.nonce)
        with self._state_guard(exclusive=True):
            if nonce_key in self._used_reauthorization_nonces:
                raise RuntimeError("controller reauthorization grant was replayed")
            highest = self._highest_tokens.get(grant.resource_id, 0)
            if grant.previous_fencing_token < highest:
                raise RuntimeError("controller reauthorization fence is stale")
            token = max(highest, grant.previous_fencing_token) + 1
            lease = ActiveControllerLease(grant.resource_id, grant.controller_id, token, current_time, current_time + ttl)
            active = dict(self._active)
            highest_tokens = dict(self._highest_tokens)
            used_nonces = set(self._used_reauthorization_nonces)
            active[grant.resource_id] = lease
            highest_tokens[grant.resource_id] = token
            used_nonces.add(nonce_key)
            self._save_state(active, highest_tokens, used_nonces)
            self._active = active
            self._highest_tokens = highest_tokens
            self._used_reauthorization_nonces = used_nonces
            return lease

    def validate(self, lease: ActiveControllerLease, *, now: float) -> ControllerLeaseDecision:
        if not isinstance(lease, ActiveControllerLease):
            raise ValueError("lease must be an ActiveControllerLease")
        current_time = self._validate_time(now, "now")
        with self._state_guard(exclusive=False):
            active = self._active.get(lease.resource_id)
            if active is None:
                return ControllerLeaseDecision.UNKNOWN_RESOURCE
            if active != lease:
                return ControllerLeaseDecision.STALE_FENCE
            if current_time >= active.expires_at:
                return ControllerLeaseDecision.EXPIRED
            return ControllerLeaseDecision.ALLOW
