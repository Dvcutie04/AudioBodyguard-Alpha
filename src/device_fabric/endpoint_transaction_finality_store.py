import json
import sqlite3
from hashlib import sha256
from contextlib import closing, contextmanager
from pathlib import Path
from time import time

from .endpoint_transaction_finality_admission import admit_endpoint_finality_assertion
from .endpoint_transaction_finality_authority import EndpointFinalityAuthoritySnapshot
from .endpoint_transaction_finality_protocol import EndpointTransactionState


def _identifier(value, field):
    if type(value) is not str or not value.strip() or value != value.strip():
        raise ValueError(field + " is invalid")
    return value


def _authority_binding_digest(authority):
    entries=sorted((key.issuer_id,key.audience,key.device_id,key.authority_epoch,key.kid.hex(),key.namespace.hex(),key.public_key.public_numbers().x,key.public_key.public_numbers().y) for key in authority.keys)
    encoded=json.dumps([authority.active_authority_epoch,entries],ensure_ascii=True,separators=(",",":")).encode("utf-8")
    return sha256(b"AQSS endpoint finality authority binding v1:"+encoded).hexdigest()


class EndpointTransactionFinalityStore:
    def __init__(self, path, *, trusted_authority=None, clock=None, require_existing=False, minimum_profile_version=1):
        if type(require_existing) is not bool:
            raise ValueError("endpoint finality require_existing is invalid")
        self._require_existing = require_existing
        if type(minimum_profile_version) is not int or minimum_profile_version not in (1,2):
            raise ValueError("endpoint finality minimum profile version is invalid")
        self._minimum_profile_version = minimum_profile_version
        if trusted_authority is not None and type(trusted_authority) is not EndpointFinalityAuthoritySnapshot:
            raise ValueError("endpoint finality trusted authority is invalid")
        if minimum_profile_version==2 and trusted_authority is None:
            raise ValueError("endpoint finality profile v2 requires trusted authority")
        if clock is not None and not callable(clock):
            raise ValueError("endpoint finality clock is invalid")
        self._trusted_authority = trusted_authority
        self._clock = clock if clock is not None else time
        self._path = Path(path)
        preexisting = self._path.exists()
        if require_existing and not preexisting:
            raise ValueError("endpoint finality history is missing")
        target = self._path.resolve().as_uri()+"?mode=rw" if require_existing else self._path
        if not self._path.parent.exists():
            raise ValueError("endpoint finality store parent does not exist")
        with closing(sqlite3.connect(target, uri=require_existing, timeout=0.05, isolation_level=None)) as connection:
            if connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0].lower() != "delete":
                raise ValueError("endpoint finality journal mode is invalid")
            connection.execute("PRAGMA synchronous=EXTRA")
            if connection.execute("PRAGMA synchronous").fetchone()[0] != 3:
                raise ValueError("endpoint finality synchronous mode is invalid")
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("CREATE TABLE IF NOT EXISTS not_applied_transactions (device_id TEXT NOT NULL, transaction_id TEXT NOT NULL, PRIMARY KEY (device_id,transaction_id))")
                connection.execute("CREATE TABLE IF NOT EXISTS execution_claims (device_id TEXT NOT NULL, transaction_id TEXT NOT NULL, PRIMARY KEY (device_id,transaction_id))")
                connection.execute("CREATE TABLE IF NOT EXISTS verified_not_applied_proofs (issuer_id TEXT NOT NULL, proof_id TEXT NOT NULL, device_id TEXT NOT NULL, transaction_id TEXT NOT NULL, proof_digest TEXT NOT NULL, wire BLOB NOT NULL, PRIMARY KEY (issuer_id,proof_id), UNIQUE (device_id,transaction_id))")
                connection.execute("CREATE TABLE IF NOT EXISTS finality_store_policy (slot INTEGER PRIMARY KEY CHECK(slot=1), mode TEXT NOT NULL)")
                connection.execute("CREATE TABLE IF NOT EXISTS finality_authority_binding (slot INTEGER PRIMARY KEY CHECK(slot=1), digest TEXT NOT NULL)")
                connection.execute("CREATE TABLE IF NOT EXISTS finality_profile_policy (slot INTEGER PRIMARY KEY CHECK(slot=1), minimum_profile_version INTEGER NOT NULL CHECK(minimum_profile_version IN (1,2)))")
                row=connection.execute("SELECT mode FROM finality_store_policy WHERE slot=1").fetchone()
                if row is None:
                    if preexisting and self._trusted_authority is not None:
                        raise ValueError("legacy endpoint finality store cannot be promoted")
                    mode="verified" if self._trusted_authority is not None else "legacy"
                    connection.execute("INSERT INTO finality_store_policy (slot,mode) VALUES (1,?)",(mode,))
                else:
                    mode=row[0]
                if mode not in ("legacy","verified"):
                    raise ValueError("endpoint finality store mode is invalid")
                if mode=="verified" and self._trusted_authority is None:
                    raise ValueError("endpoint finality trusted authority is required")
                if mode=="legacy" and self._trusted_authority is not None:
                    raise ValueError("legacy endpoint finality store cannot be promoted")
                self._policy_mode=mode
                profile_policy=connection.execute("SELECT minimum_profile_version FROM finality_profile_policy WHERE slot=1").fetchone()
                if profile_policy is None:
                    if preexisting:
                        raise ValueError("endpoint finality profile policy is missing")
                    connection.execute("INSERT INTO finality_profile_policy (slot,minimum_profile_version) VALUES (1,?)",(minimum_profile_version,))
                elif profile_policy!=(minimum_profile_version,):
                    raise ValueError("endpoint finality profile policy mismatch")
                if mode=="verified":
                    digest=_authority_binding_digest(self._trusted_authority)
                    existing=connection.execute("SELECT digest FROM finality_authority_binding WHERE slot=1").fetchone()
                    if existing is None:
                        if preexisting:
                            raise ValueError("endpoint finality authority binding is missing")
                        connection.execute("INSERT INTO finality_authority_binding (slot,digest) VALUES (1,?)",(digest,))
                    elif existing!=(digest,):
                        raise ValueError("endpoint finality authority binding mismatch")
                    self._authority_digest=digest
                elif connection.execute("SELECT 1 FROM finality_authority_binding WHERE slot=1").fetchone() is not None:
                    raise ValueError("endpoint finality authority binding is invalid")
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    @contextmanager
    def _connection(self):
        if not self._path.exists():
            raise ValueError("endpoint finality history is missing")
        with closing(sqlite3.connect(self._path.resolve().as_uri()+"?mode=rw", uri=True, timeout=0.05, isolation_level=None)) as connection:
            if connection.execute("PRAGMA journal_mode").fetchone()[0].lower() != "delete":
                raise ValueError("endpoint finality journal mode is invalid")
            connection.execute("PRAGMA synchronous=EXTRA")
            if connection.execute("PRAGMA synchronous").fetchone()[0] != 3:
                raise ValueError("endpoint finality synchronous mode is invalid")
            mode=connection.execute("SELECT mode FROM finality_store_policy WHERE slot=1").fetchone()
            if mode!=(self._policy_mode,):
                raise ValueError("endpoint finality store policy changed")
            profile_policy=connection.execute("SELECT minimum_profile_version FROM finality_profile_policy WHERE slot=1").fetchone()
            if profile_policy!=(self._minimum_profile_version,):
                raise ValueError("endpoint finality profile policy changed")
            if self._policy_mode=="verified":
                binding=connection.execute("SELECT digest FROM finality_authority_binding WHERE slot=1").fetchone()
                if binding!=(self._authority_digest,) or _authority_binding_digest(self._trusted_authority)!=self._authority_digest:
                    raise ValueError("endpoint finality authority binding changed")
            yield connection

    @contextmanager
    def _write(self):
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def record_not_applied(self, transaction_id, *, device_id):
        if self._trusted_authority is not None:
            raise ValueError("endpoint finality verified proof required")
        transaction_id = _identifier(transaction_id, "transaction_id")
        device_id = _identifier(device_id, "device_id")
        with self._write() as connection:
            claimed = connection.execute("SELECT 1 FROM execution_claims WHERE device_id=? AND transaction_id=?", (device_id, transaction_id)).fetchone()
            if claimed is not None:
                raise ValueError("endpoint transaction execution already claimed")
            connection.execute("INSERT OR IGNORE INTO not_applied_transactions (device_id,transaction_id) VALUES (?,?)", (device_id, transaction_id))

    def record_verified_not_applied(self, wire, *, device_id, transaction_id, intent_id, capability_digest, authorization_digest, controller_id, controller_fencing_token, audience, issuer_id, authority_epoch, request_digest=None):
        if self._trusted_authority is None:
            raise ValueError("endpoint finality trusted authority is required")
        if self._minimum_profile_version==2 and (type(request_digest) is not str or not request_digest.strip() or request_digest!=request_digest.strip()):
            raise ValueError("production endpoint finality request_digest is required")
        with self._write() as connection:
            admitted = admit_endpoint_finality_assertion(
                wire=wire, trust=self._trusted_authority, device_id=device_id,
                transaction_id=transaction_id, intent_id=intent_id,
                capability_digest=capability_digest, authorization_digest=authorization_digest,
                controller_id=controller_id, controller_fencing_token=controller_fencing_token,
                audience=audience, issuer_id=issuer_id, authority_epoch=authority_epoch,
                now=self._clock(), current_state=EndpointTransactionState.UNKNOWN,
                previous_proof_digest=None, request_digest=request_digest,
            )
            claims = admitted.accepted_result.claims
            device_id = _identifier(claims.device_id, "device_id")
            transaction_id = _identifier(claims.transaction_id, "transaction_id")
            claimed = connection.execute("SELECT 1 FROM execution_claims WHERE device_id=? AND transaction_id=?", (device_id, transaction_id)).fetchone()
            if claimed is not None:
                raise ValueError("endpoint transaction execution already claimed")
            existing_identity = connection.execute("SELECT device_id, transaction_id, proof_digest FROM verified_not_applied_proofs WHERE issuer_id=? AND proof_id=?", (claims.issuer_id, claims.proof_id)).fetchone()
            existing_transaction = connection.execute("SELECT issuer_id, proof_id, proof_digest FROM verified_not_applied_proofs WHERE device_id=? AND transaction_id=?", (device_id, transaction_id)).fetchone()
            existing_marker = connection.execute("SELECT 1 FROM not_applied_transactions WHERE device_id=? AND transaction_id=?", (device_id, transaction_id)).fetchone()
            if existing_identity is not None or existing_transaction is not None:
                if existing_marker is None:
                    raise ValueError("endpoint finality history is incomplete")
                if existing_identity == (device_id, transaction_id, admitted.proof_digest) and existing_transaction == (claims.issuer_id, claims.proof_id, admitted.proof_digest):
                    return admitted
                raise ValueError("endpoint finality proof identity conflict")
            if existing_marker is not None:
                raise ValueError("endpoint finality marker lacks a verified proof")
            connection.execute("INSERT INTO verified_not_applied_proofs (issuer_id,proof_id,device_id,transaction_id,proof_digest,wire) VALUES (?,?,?,?,?,?)", (claims.issuer_id,claims.proof_id,device_id,transaction_id,admitted.proof_digest,wire))
            connection.execute("INSERT INTO not_applied_transactions (device_id,transaction_id) VALUES (?,?)", (device_id,transaction_id))
            return admitted

    def claim_execution(self, transaction_id, *, device_id):
        transaction_id = _identifier(transaction_id, "transaction_id")
        device_id = _identifier(device_id, "device_id")
        with self._write() as connection:
            blocked = connection.execute("SELECT 1 FROM not_applied_transactions WHERE device_id=? AND transaction_id=? UNION ALL SELECT 1 FROM verified_not_applied_proofs WHERE device_id=? AND transaction_id=? LIMIT 1", (device_id, transaction_id, device_id, transaction_id)).fetchone()
            if blocked is not None:
                return False
            inserted = connection.execute("INSERT OR IGNORE INTO execution_claims (device_id,transaction_id) VALUES (?,?)", (device_id, transaction_id))
            return inserted.rowcount == 1

    def permits_execution(self, transaction_id, *, device_id):
        transaction_id = _identifier(transaction_id, "transaction_id")
        device_id = _identifier(device_id, "device_id")
        with self._connection() as connection:
            row = connection.execute("SELECT 1 FROM not_applied_transactions WHERE device_id=? AND transaction_id=? UNION ALL SELECT 1 FROM execution_claims WHERE device_id=? AND transaction_id=? UNION ALL SELECT 1 FROM verified_not_applied_proofs WHERE device_id=? AND transaction_id=? LIMIT 1", (device_id, transaction_id, device_id, transaction_id, device_id, transaction_id)).fetchone()
        return row is None
