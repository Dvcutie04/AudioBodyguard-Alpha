import hashlib
import json
import os
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from ..control.remote_controller_protocol import P256AuthorityPublicVerifier
from .controller_fence_store import ControllerFenceStore
from .endpoint_execution_ledger import _identifier, _positive_integer
from .endpoint_handoff_fence import SignedEndpointFenceDirective, VerifiedEndpointFenceInstaller


class EndpointHandoffBarrier:
    """Reference admission journal; physical containment is not certified here."""

    def __init__(self, path, *, device_id, fence_store, trusted_verifiers, enroll=False):
        if type(enroll) is not bool or type(fence_store) is not ControllerFenceStore:
            raise ValueError("endpoint handoff barrier configuration is invalid")
        self._device_id = _identifier(device_id, "device_id")
        self._fence_store = fence_store
        if type(trusted_verifiers) is not dict or not trusted_verifiers:
            raise ValueError("endpoint barrier trusted verifiers are required")
        entries = []
        for key_id, verifier in trusted_verifiers.items():
            if type(key_id) is not str or not key_id.strip() or type(verifier) is not P256AuthorityPublicVerifier or type(verifier.key_id) is not str or verifier.key_id != key_id:
                raise ValueError("endpoint barrier trusted verifier is invalid")
            entries.append((key_id, verifier.export_spki_base64()))
        entries.sort()
        self._trusted_verifiers = {key_id: P256AuthorityPublicVerifier.from_spki_base64(key_id, encoded) for key_id, encoded in entries}
        trust_payload = json.dumps(["AQSS/endpoint-handoff-trust/v1", entries], ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self._trusted_verifiers_digest = hashlib.sha256(trust_payload).hexdigest()
        self._path = Path(path)
        if not self._path.parent.exists():
            raise ValueError("endpoint barrier parent does not exist")
        if enroll:
            try:
                os.close(os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600))
            except FileExistsError:
                raise ValueError("endpoint barrier already exists") from None
        elif not self._path.exists():
            raise ValueError("endpoint barrier history is missing")
        with self._write(create=enroll):
            pass

    @contextmanager
    def _write(self, *, create=False):
        if not self._path.exists():
            raise ValueError("endpoint barrier history is missing")
        uri = self._path.resolve().as_uri() + "?mode=rw"
        with closing(sqlite3.connect(uri, uri=True, timeout=5.0, isolation_level=None)) as db:
            mode = db.execute("PRAGMA journal_mode=DELETE" if create else "PRAGMA journal_mode").fetchone()[0]
            if mode.lower() != "delete":
                raise ValueError("endpoint barrier journal mode is invalid")
            db.execute("PRAGMA synchronous=EXTRA")
            if db.execute("PRAGMA synchronous").fetchone()[0] != 3:
                raise ValueError("endpoint barrier synchronous mode is invalid")
            db.execute("BEGIN IMMEDIATE")
            try:
                if create:
                    db.execute("CREATE TABLE endpoint_barrier_identity (slot INTEGER PRIMARY KEY CHECK(slot=1), device_id TEXT NOT NULL, schema_version INTEGER NOT NULL, trusted_verifiers_digest TEXT NOT NULL)")
                    db.execute("CREATE TABLE endpoint_barrier_admissions (transaction_id TEXT PRIMARY KEY, resource_id TEXT NOT NULL, controller_id TEXT NOT NULL, fencing_token INTEGER NOT NULL)")
                    db.execute("CREATE TABLE endpoint_barrier_handoffs (request_id TEXT PRIMARY KEY, resource_id TEXT NOT NULL, controller_id TEXT NOT NULL, fencing_token INTEGER NOT NULL, previous_controller_id TEXT NOT NULL, previous_fencing_token INTEGER NOT NULL, directive_digest TEXT NOT NULL)")
                    db.execute("CREATE TABLE endpoint_barrier_holds (resource_id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE, content_digest TEXT NOT NULL, canonical_claims BLOB NOT NULL, signature TEXT NOT NULL)")
                    db.execute("INSERT INTO endpoint_barrier_identity VALUES (1,?,3,?)", (self._device_id, self._trusted_verifiers_digest))
                identity = db.execute("SELECT device_id,schema_version,trusted_verifiers_digest FROM endpoint_barrier_identity WHERE slot=1").fetchone()
                if identity != (self._device_id, 3, self._trusted_verifiers_digest):
                    raise ValueError("endpoint barrier identity mismatch")
                db.execute("SELECT 1 FROM endpoint_barrier_admissions LIMIT 1")
                db.execute("SELECT 1 FROM endpoint_barrier_handoffs LIMIT 1")
                db.execute("SELECT 1 FROM endpoint_barrier_holds LIMIT 1")
                yield db
            except BaseException:
                db.rollback()
                raise
            else:
                db.commit()

    def admit(self, *, transaction_id, resource_id, controller_id, fencing_token):
        transaction_id = _identifier(transaction_id, "transaction_id")
        resource_id = _identifier(resource_id, "resource_id")
        controller_id = _identifier(controller_id, "controller_id")
        fencing_token = _positive_integer(fencing_token, "fencing_token")
        with self._write() as db:
            binding = (resource_id, controller_id, fencing_token)
            existing = db.execute("SELECT resource_id,controller_id,fencing_token FROM endpoint_barrier_admissions WHERE transaction_id=?", (transaction_id,)).fetchone()
            if existing is not None:
                if existing != binding:
                    raise ValueError("endpoint admission binding mismatch")
                return False
            if db.execute("SELECT 1 FROM endpoint_barrier_holds WHERE resource_id=?", (resource_id,)).fetchone() is not None:
                return False
            if self._fence_store.snapshot().get(resource_id) != (fencing_token, controller_id):
                return False
            db.execute("INSERT INTO endpoint_barrier_admissions VALUES (?,?,?,?)", (transaction_id, *binding))
            return True

    def install(self, directive, *, now):
        if type(directive) is not SignedEndpointFenceDirective:
            return False
        installer = VerifiedEndpointFenceInstaller(device_id=self._device_id, fence_store=self._fence_store, trusted_verifiers=self._trusted_verifiers)
        with self._write() as db:
            if installer.validate(directive, now=now) is not True:
                return False
            existing = db.execute("SELECT directive_digest FROM endpoint_barrier_handoffs WHERE request_id=?", (directive.request_id,)).fetchone()
            if existing is not None:
                return False
            if db.execute("SELECT 1 FROM endpoint_barrier_holds WHERE resource_id=? OR request_id=?", (directive.resource_id, directive.request_id)).fetchone() is not None:
                return False
            canonical = directive.canonical_bytes
            hold = (directive.resource_id, directive.request_id, hashlib.sha256(canonical).hexdigest(), canonical, directive.signature)
            db.execute("INSERT INTO endpoint_barrier_holds VALUES (?,?,?,?,?)", hold)
        # The hold must commit before the independent fence mutation.
        if installer.install(directive, now=now) is not True:
            return False
        with self._write() as db:
            retained = db.execute("SELECT resource_id,request_id,content_digest,canonical_claims,signature FROM endpoint_barrier_holds WHERE resource_id=?", (directive.resource_id,)).fetchone()
            if retained != hold:
                raise ValueError("endpoint barrier hold mismatch")
            digest = hashlib.sha256(canonical + b"\x00" + directive.signature.encode("utf-8")).hexdigest()
            db.execute("INSERT INTO endpoint_barrier_handoffs VALUES (?,?,?,?,?,?,?)", (directive.request_id, directive.resource_id, directive.controller_id, directive.fencing_token, directive.previous_controller_id, directive.previous_fencing_token, digest))
            return True

    def is_ready(self, request_id):
        request_id = _identifier(request_id, "request_id")
        with self._write() as db:
            handoff = db.execute("SELECT resource_id,controller_id,fencing_token,previous_controller_id,previous_fencing_token FROM endpoint_barrier_handoffs WHERE request_id=?", (request_id,)).fetchone()
            if handoff is None:
                return False
            resource_id, controller_id, token, previous_id, previous_token = handoff
            if self._fence_store.snapshot().get(resource_id) != (token, controller_id):
                return False
            outstanding = db.execute("SELECT 1 FROM endpoint_barrier_admissions WHERE resource_id=? AND controller_id=? AND fencing_token<=? LIMIT 1", (resource_id, previous_id, previous_token)).fetchone()
            if outstanding is not None:
                return False
            return False  # A native future-effect exclusion certificate is still required.
