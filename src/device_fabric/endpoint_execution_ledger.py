import os
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path


def _identifier(value, name):
    if type(value) is not str or not value.strip() or value != value.strip():
        raise ValueError(name + " is invalid")
    return value


def _positive_integer(value, name):
    if type(value) is not int or not 0 < value < 2**63:
        raise ValueError(name + " is invalid")
    return value


class EndpointExecutionLedger:
    def __init__(self, path, *, device_id, enroll=False):
        if type(enroll) is not bool:
            raise ValueError("endpoint ledger enrollment option is invalid")
        self._device_id = _identifier(device_id, "device_id")
        self._path = Path(path)
        if not self._path.parent.exists():
            raise ValueError("endpoint ledger parent does not exist")
        if enroll:
            try:
                os.close(os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600))
            except FileExistsError:
                raise ValueError("endpoint ledger already exists") from None
        elif not self._path.exists():
            raise ValueError("endpoint ledger history is missing")
        with self._write(create=enroll):
            pass

    @contextmanager
    def _write(self, *, create=False):
        if not self._path.exists():
            raise ValueError("endpoint ledger history is missing")
        target = self._path.resolve().as_uri() + "?mode=rw"
        with closing(sqlite3.connect(target, uri=True, timeout=5.0, isolation_level=None)) as connection:
            if create:
                journal = connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
            else:
                journal = connection.execute("PRAGMA journal_mode").fetchone()[0]
            if journal.lower() != "delete":
                raise ValueError("endpoint ledger journal mode is invalid")
            connection.execute("PRAGMA synchronous=EXTRA")
            if connection.execute("PRAGMA synchronous").fetchone()[0] != 3:
                raise ValueError("endpoint ledger synchronous mode is invalid")
            connection.execute("BEGIN IMMEDIATE")
            try:
                if create:
                    connection.execute("CREATE TABLE endpoint_ledger_identity (slot INTEGER PRIMARY KEY CHECK(slot=1), device_id TEXT NOT NULL, schema_version INTEGER NOT NULL)")
                    connection.execute("CREATE TABLE endpoint_transactions (transaction_id TEXT PRIMARY KEY, intent_id TEXT NOT NULL, request_digest TEXT NOT NULL, capability_digest TEXT NOT NULL, authorization_digest TEXT NOT NULL, controller_id TEXT NOT NULL, controller_fencing_token INTEGER NOT NULL, authority_epoch INTEGER NOT NULL, state TEXT NOT NULL)")
                    connection.execute("INSERT INTO endpoint_ledger_identity (slot,device_id,schema_version) VALUES (1,?,1)", (self._device_id,))
                identity = connection.execute("SELECT device_id,schema_version FROM endpoint_ledger_identity WHERE slot=1").fetchone()
                if identity != (self._device_id, 1):
                    raise ValueError("endpoint ledger identity mismatch")
                connection.execute("SELECT 1 FROM endpoint_transactions LIMIT 1")
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def _decide(self, transaction_id, state, *, intent_id, request_digest, capability_digest, authorization_digest, controller_id, controller_fencing_token, authority_epoch):
        transaction_id = _identifier(transaction_id, "transaction_id")
        context = (
            _identifier(intent_id, "intent_id"),
            _identifier(request_digest, "request_digest"),
            _identifier(capability_digest, "capability_digest"),
            _identifier(authorization_digest, "authorization_digest"),
            _identifier(controller_id, "controller_id"),
            _positive_integer(controller_fencing_token, "controller_fencing_token"),
            _positive_integer(authority_epoch, "authority_epoch"),
        )
        with self._write() as connection:
            row = connection.execute("SELECT intent_id,request_digest,capability_digest,authorization_digest,controller_id,controller_fencing_token,authority_epoch,state FROM endpoint_transactions WHERE transaction_id=?", (transaction_id,)).fetchone()
            if row is not None:
                if row[:7] != context:
                    raise ValueError("endpoint execution binding mismatch")
                if row[7] not in ("EXECUTION_CLAIMED", "NOT_APPLIED"):
                    raise ValueError("endpoint ledger state is invalid")
                return state == "NOT_APPLIED" and row[7] == "NOT_APPLIED"
            connection.execute("INSERT INTO endpoint_transactions (transaction_id,intent_id,request_digest,capability_digest,authorization_digest,controller_id,controller_fencing_token,authority_epoch,state) VALUES (?,?,?,?,?,?,?,?,?)", (transaction_id, *context, state))
            return True

    def claim_execution(self, transaction_id, *, intent_id, request_digest, capability_digest, authorization_digest, controller_id, controller_fencing_token, authority_epoch):
        return self._decide(transaction_id, "EXECUTION_CLAIMED", intent_id=intent_id, request_digest=request_digest, capability_digest=capability_digest, authorization_digest=authorization_digest, controller_id=controller_id, controller_fencing_token=controller_fencing_token, authority_epoch=authority_epoch)

    def close_if_unstarted(self, transaction_id, *, intent_id, request_digest, capability_digest, authorization_digest, controller_id, controller_fencing_token, authority_epoch):
        return self._decide(transaction_id, "NOT_APPLIED", intent_id=intent_id, request_digest=request_digest, capability_digest=capability_digest, authorization_digest=authorization_digest, controller_id=controller_id, controller_fencing_token=controller_fencing_token, authority_epoch=authority_epoch)
