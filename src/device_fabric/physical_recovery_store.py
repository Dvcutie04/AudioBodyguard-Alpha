from contextlib import closing
from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import math
from pathlib import Path
import sqlite3


class PhysicalRecoveryStatus(str, Enum):
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    VERIFIED_APPLIED = "VERIFIED_APPLIED"
    VERIFIED_NOT_APPLIED = "VERIFIED_NOT_APPLIED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class PhysicalRecoveryPersistenceError(RuntimeError):
    def __init__(self, transaction_id, capability_digest):
        super().__init__("indeterminate physical state could not be persisted")
        self.transaction_id = transaction_id
        self.capability_digest = capability_digest


@dataclass(frozen=True)
class PhysicalRecoveryRecord:
    transaction_id: str
    intent_id: str
    device_id: str
    operation: str
    target_state_digest: str
    expected_pre_state_digest: str
    authorization_digest: str
    capability_digest: str
    recorded_at: float
    status: PhysicalRecoveryStatus
    observed_state_digest: str = ""
    observed_at: float | None = None
    precondition_epoch: int | None = None
    finality_closed: bool = False
    supervisor_release_completed: bool = False
    finality_report_digest: str = ""
    finality_report_bytes: bytes = b""
    finality_endpoint_key_id: str = ""
    finality_algorithm: str = ""
    finality_signature: str = ""


def _identifier(value):
    return type(value) is str and bool(value.strip()) and value == value.strip()


def _digest(value):
    return type(value) is str and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _validate(record):
    if not isinstance(record, PhysicalRecoveryRecord):
        raise ValueError("invalid physical recovery record")
    if any(not _identifier(value) for value in (record.transaction_id, record.intent_id, record.device_id, record.operation)):
        raise ValueError("invalid physical recovery identifier")
    if any(not _digest(value) for value in (record.target_state_digest, record.expected_pre_state_digest, record.authorization_digest, record.capability_digest)):
        raise ValueError("invalid physical recovery digest")
    if type(record.recorded_at) not in (int, float) or not math.isfinite(record.recorded_at) or record.recorded_at < 0:
        raise ValueError("invalid physical recovery timestamp")
    if record.precondition_epoch is not None and (type(record.precondition_epoch) is not int or record.precondition_epoch < 0):
        raise ValueError("invalid physical recovery precondition epoch")
    if type(record.finality_closed) is not bool:
        raise ValueError("invalid physical recovery finality state")
    if type(record.supervisor_release_completed) is not bool:
        raise ValueError("invalid physical recovery supervisor release state")
    if record.supervisor_release_completed and not record.finality_closed:
        raise ValueError("physical recovery supervisor release requires closed finality")
    if record.finality_closed and (not _digest(record.finality_report_digest) or type(record.finality_report_bytes) is not bytes or not record.finality_report_bytes or hashlib.sha256(record.finality_report_bytes).hexdigest()!=record.finality_report_digest):
        raise ValueError("closed physical recovery requires matching finality report evidence")
    if record.finality_closed and any(type(value) is not str or not value.strip() for value in (record.finality_endpoint_key_id,record.finality_algorithm,record.finality_signature)):
        raise ValueError("closed physical recovery requires finality authentication envelope")
    if not record.finality_closed and (record.finality_report_digest != "" or record.finality_report_bytes != b"" or any(value != "" for value in (record.finality_endpoint_key_id,record.finality_algorithm,record.finality_signature))):
        raise ValueError("open physical recovery cannot contain finality report evidence")
    if record.finality_closed and record.status not in (PhysicalRecoveryStatus.VERIFIED_APPLIED, PhysicalRecoveryStatus.VERIFIED_NOT_APPLIED):
        raise ValueError("physical recovery finality requires verified observation")
    if record.status is PhysicalRecoveryStatus.RECOVERY_REQUIRED:
        if record.observed_state_digest != "" or record.observed_at is not None:
            raise ValueError("pending physical recovery cannot contain observation evidence")
    elif record.status in (PhysicalRecoveryStatus.VERIFIED_APPLIED, PhysicalRecoveryStatus.VERIFIED_NOT_APPLIED, PhysicalRecoveryStatus.MANUAL_REVIEW_REQUIRED):
        if not _digest(record.observed_state_digest) or type(record.observed_at) not in (int, float) or not math.isfinite(record.observed_at) or record.observed_at < record.recorded_at:
            raise ValueError("invalid physical recovery observation evidence")
    else:
        raise ValueError("invalid physical recovery status")


def _from_row(row):
    record=PhysicalRecoveryRecord(transaction_id=row[0], intent_id=row[1], device_id=row[2], operation=row[3], target_state_digest=row[4], expected_pre_state_digest=row[5], authorization_digest=row[6], capability_digest=row[7], recorded_at=row[8], status=PhysicalRecoveryStatus(row[9]), observed_state_digest="" if row[10] is None else row[10], observed_at=row[11], precondition_epoch=row[12], finality_closed=row[13] == 1, supervisor_release_completed=row[14] == 1, finality_report_digest="" if row[15] is None else row[15], finality_report_bytes=b"" if row[16] is None else row[16], finality_endpoint_key_id="" if row[17] is None else row[17], finality_algorithm="" if row[18] is None else row[18], finality_signature="" if row[19] is None else row[19])
    if row[13] not in (0,1):
        raise ValueError("invalid stored physical recovery finality state")
    if row[14] not in (0,1):
        raise ValueError("invalid stored physical recovery supervisor release state")
    _validate(record)
    return record


class PhysicalRecoveryStore:
    _COLUMNS = "transaction_id, intent_id, device_id, operation, target_state_digest, expected_pre_state_digest, authorization_digest, capability_digest, recorded_at, status, observed_state_digest, observed_at, precondition_epoch, finality_closed, supervisor_release_completed, finality_report_digest, finality_report_bytes, finality_endpoint_key_id, finality_algorithm, finality_signature"

    def __init__(self, path):
        raw_path = str(path)
        if not raw_path or raw_path == ":memory:":
            raise ValueError("a persistent recovery database path is required")
        self.path = raw_path
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                connection.execute("CREATE TABLE IF NOT EXISTS physical_recovery_records (transaction_id TEXT PRIMARY KEY NOT NULL, intent_id TEXT NOT NULL, device_id TEXT NOT NULL, operation TEXT NOT NULL, target_state_digest TEXT NOT NULL, expected_pre_state_digest TEXT NOT NULL, authorization_digest TEXT NOT NULL, capability_digest TEXT NOT NULL, recorded_at REAL NOT NULL, status TEXT NOT NULL, observed_state_digest TEXT, observed_at REAL, precondition_epoch INTEGER, finality_closed INTEGER NOT NULL DEFAULT 0, supervisor_release_completed INTEGER NOT NULL DEFAULT 0, finality_report_digest TEXT, finality_report_bytes BLOB, finality_endpoint_key_id TEXT, finality_algorithm TEXT, finality_signature TEXT)")
                columns = {row[1] for row in connection.execute("PRAGMA table_info(physical_recovery_records)")}
                if "observed_state_digest" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN observed_state_digest TEXT")
                if "observed_at" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN observed_at REAL")
                if "precondition_epoch" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN precondition_epoch INTEGER")
                if "finality_closed" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN finality_closed INTEGER NOT NULL DEFAULT 0")
                if "supervisor_release_completed" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN supervisor_release_completed INTEGER NOT NULL DEFAULT 0")
                if "finality_report_digest" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN finality_report_digest TEXT")
                if "finality_report_bytes" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN finality_report_bytes BLOB")
                if "finality_endpoint_key_id" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN finality_endpoint_key_id TEXT")
                if "finality_algorithm" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN finality_algorithm TEXT")
                if "finality_signature" not in columns:
                    connection.execute("ALTER TABLE physical_recovery_records ADD COLUMN finality_signature TEXT")

    def record(self, record):
        _validate(record)
        if record.status is not PhysicalRecoveryStatus.RECOVERY_REQUIRED:
            raise ValueError("new physical recovery record must require recovery")
        values = (record.transaction_id, record.intent_id, record.device_id, record.operation, record.target_state_digest, record.expected_pre_state_digest, record.authorization_digest, record.capability_digest, record.recorded_at, record.status.value, None, None, record.precondition_epoch, 0, 0, None, None, None, None, None)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                cursor = connection.execute("INSERT OR IGNORE INTO physical_recovery_records (" + self._COLUMNS + ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
                if cursor.rowcount == 1:
                    return True
                row = connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE transaction_id = ?", (record.transaction_id,)).fetchone()
        if row is None or _from_row(row) != record:
            raise ValueError("conflicting physical recovery record")
        return False

    def reconcile_observation(self, transaction_id, *, observed_state_digest, observed_at):
        if not _identifier(transaction_id):
            raise ValueError("invalid transaction identifier")
        if not _digest(observed_state_digest):
            raise ValueError("invalid observed state digest")
        if type(observed_at) not in (int, float) or not math.isfinite(observed_at) or observed_at < 0:
            raise ValueError("invalid observation timestamp")
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                row = connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE transaction_id = ?", (transaction_id,)).fetchone()
                if row is None:
                    raise KeyError("physical recovery record not found")
                current = _from_row(row)
                if current.status is not PhysicalRecoveryStatus.RECOVERY_REQUIRED:
                    if current.observed_state_digest == observed_state_digest and current.observed_at == observed_at:
                        return current
                    raise ValueError("physical recovery record already reconciled")
                if observed_at < current.recorded_at:
                    raise ValueError("observation predates recovery record")
                if observed_state_digest == current.target_state_digest:
                    resolved_status = PhysicalRecoveryStatus.VERIFIED_APPLIED
                elif observed_state_digest == current.expected_pre_state_digest:
                    resolved_status = PhysicalRecoveryStatus.VERIFIED_NOT_APPLIED
                else:
                    resolved_status = PhysicalRecoveryStatus.MANUAL_REVIEW_REQUIRED
                connection.execute("UPDATE physical_recovery_records SET status = ?, observed_state_digest = ?, observed_at = ? WHERE transaction_id = ? AND status = ?", (resolved_status.value, observed_state_digest, observed_at, transaction_id, PhysicalRecoveryStatus.RECOVERY_REQUIRED.value))
                resolved = connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE transaction_id = ?", (transaction_id,)).fetchone()
        return _from_row(resolved)

    def confirm_finality(self, record, *, report_digest, report_bytes, endpoint_key_id, algorithm, signature):
        _validate(record)
        if not _digest(report_digest) or type(report_bytes) is not bytes or not report_bytes or hashlib.sha256(report_bytes).hexdigest()!=report_digest:
            raise ValueError("physical recovery finality requires matching report evidence")
        if any(type(value) is not str or not value.strip() for value in (endpoint_key_id,algorithm,signature)):
            raise ValueError("physical recovery finality requires authentication envelope")
        if record.status not in (PhysicalRecoveryStatus.VERIFIED_APPLIED, PhysicalRecoveryStatus.VERIFIED_NOT_APPLIED):
            raise ValueError("physical recovery finality requires a verified record")
        if record.finality_closed and (record.finality_report_digest != report_digest or record.finality_report_bytes != report_bytes or (record.finality_endpoint_key_id,record.finality_algorithm,record.finality_signature)!=(endpoint_key_id,algorithm,signature)):
            raise ValueError("physical recovery finality report evidence changed")
        expected_closed=record if record.finality_closed else replace(record,finality_closed=True,finality_report_digest=report_digest,finality_report_bytes=report_bytes,finality_endpoint_key_id=endpoint_key_id,finality_algorithm=algorithm,finality_signature=signature)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                row=connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE transaction_id = ?",(record.transaction_id,)).fetchone()
                if row is None:
                    raise KeyError("physical recovery record not found")
                current=_from_row(row)
                if record.finality_closed:
                    if current != record:
                        raise ValueError("physical recovery record changed after finality")
                    return current
                if current == expected_closed:
                    return current
                if current != record:
                    raise ValueError("physical recovery record changed before finality")
                parameters=(report_digest,report_bytes,endpoint_key_id,algorithm,signature,record.transaction_id,record.intent_id,record.device_id,record.operation,record.target_state_digest,record.expected_pre_state_digest,record.authorization_digest,record.capability_digest,record.recorded_at,record.status.value,record.observed_state_digest,record.observed_at,record.precondition_epoch)
                cursor=connection.execute("UPDATE physical_recovery_records SET finality_closed = 1, finality_report_digest = ?, finality_report_bytes = ?, finality_endpoint_key_id = ?, finality_algorithm = ?, finality_signature = ? WHERE transaction_id = ? AND intent_id = ? AND device_id = ? AND operation = ? AND target_state_digest = ? AND expected_pre_state_digest = ? AND authorization_digest = ? AND capability_digest = ? AND recorded_at = ? AND status = ? AND observed_state_digest = ? AND observed_at IS ? AND precondition_epoch IS ? AND finality_closed = 0 AND supervisor_release_completed = 0 AND finality_report_digest IS NULL AND finality_report_bytes IS NULL AND finality_endpoint_key_id IS NULL AND finality_algorithm IS NULL AND finality_signature IS NULL",parameters)
                if cursor.rowcount != 1:
                    raise ValueError("physical recovery record changed before finality")
                closed_row=connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE transaction_id = ?",(record.transaction_id,)).fetchone()
                if closed_row is None:
                    raise ValueError("physical recovery finality was not persisted")
                closed=_from_row(closed_row)
                if closed != expected_closed:
                    raise ValueError("physical recovery finality was not persisted")
        return closed

    def confirm_supervisor_release(self, record):
        _validate(record)
        if not record.finality_closed:
            raise ValueError("physical recovery supervisor release requires finality")
        expected_released=record if record.supervisor_release_completed else replace(record,supervisor_release_completed=True)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                row=connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE transaction_id = ?",(record.transaction_id,)).fetchone()
                if row is None:
                    raise KeyError("physical recovery record not found")
                current=_from_row(row)
                if current == expected_released:
                    return current
                if current != record:
                    raise ValueError("physical recovery record changed before supervisor release")
                parameters=(record.transaction_id,record.intent_id,record.device_id,record.operation,record.target_state_digest,record.expected_pre_state_digest,record.authorization_digest,record.capability_digest,record.recorded_at,record.status.value,record.observed_state_digest,record.observed_at,record.precondition_epoch,record.finality_report_digest,record.finality_report_bytes,record.finality_endpoint_key_id,record.finality_algorithm,record.finality_signature)
                cursor=connection.execute("UPDATE physical_recovery_records SET supervisor_release_completed = 1 WHERE transaction_id = ? AND intent_id = ? AND device_id = ? AND operation = ? AND target_state_digest = ? AND expected_pre_state_digest = ? AND authorization_digest = ? AND capability_digest = ? AND recorded_at = ? AND status = ? AND observed_state_digest = ? AND observed_at IS ? AND precondition_epoch IS ? AND finality_closed = 1 AND supervisor_release_completed = 0 AND finality_report_digest = ? AND finality_report_bytes = ? AND finality_endpoint_key_id = ? AND finality_algorithm = ? AND finality_signature = ?",parameters)
                if cursor.rowcount != 1:
                    raise ValueError("physical recovery record changed before supervisor release")
                released_row=connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE transaction_id = ?",(record.transaction_id,)).fetchone()
                released=_from_row(released_row) if released_row is not None else None
                if released != expected_released:
                    raise ValueError("physical recovery supervisor release was not persisted")
        return released

    def get(self, transaction_id):
        if not _identifier(transaction_id):
            raise ValueError("invalid transaction identifier")
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE transaction_id = ?", (transaction_id,)).fetchone()
        return None if row is None else _from_row(row)

    def pending(self):
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records WHERE status IN (?, ?) ORDER BY recorded_at, transaction_id", (PhysicalRecoveryStatus.RECOVERY_REQUIRED.value, PhysicalRecoveryStatus.MANUAL_REVIEW_REQUIRED.value)).fetchall()
        return tuple(_from_row(row) for row in rows)

    def records(self):
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute("SELECT " + self._COLUMNS + " FROM physical_recovery_records ORDER BY recorded_at, transaction_id").fetchall()
        return tuple(_from_row(row) for row in rows)

    def unresolved(self):
        return tuple(record for record in self.records() if record.finality_closed is False)
