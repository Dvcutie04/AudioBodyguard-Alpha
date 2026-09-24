import base64
import fcntl
import hashlib
from threading import RLock
from contextlib import contextmanager
import json
import math
import os
import tempfile
from pathlib import Path
from dataclasses import dataclass,replace
from enum import Enum

from .protection_supervisor import ProtectionState,ProtectionSupervisor


@dataclass(frozen=True,slots=True)
class ProtectionSupervisorCheckpoint:
    state: ProtectionState
    reason: str
    observed_at: float
    runtime_generation: str
    checkpoint_sequence: int=1

    def __post_init__(self) -> None:
        if not isinstance(self.state,ProtectionState):
            raise TypeError("state must be ProtectionState")
        if type(self.reason) is not str or not self.reason.strip() or self.reason!=self.reason.strip():
            raise ValueError("reason must be a nonempty identifier")
        if isinstance(self.observed_at,bool) or not isinstance(self.observed_at,(int,float)) or not math.isfinite(self.observed_at):
            raise ValueError("observed_at must be finite")
        if type(self.runtime_generation) is not str or not self.runtime_generation.strip() or self.runtime_generation!=self.runtime_generation.strip():
            raise ValueError("runtime_generation must be a nonempty identifier")
        if type(self.checkpoint_sequence) is not int or not 1<=self.checkpoint_sequence<=2**63-1:
            raise ValueError("checkpoint_sequence must be a positive 63-bit integer")


class ProtectionSupervisorCheckpointCodec:
    SCHEMA_VERSION=2
    MAX_ENCODED_BYTES=4096
    _FIELDS=frozenset(("schema_version","state","reason","observed_at","runtime_generation","checkpoint_sequence"))

    @classmethod
    def encode(cls,checkpoint) -> bytes:
        if not isinstance(checkpoint,ProtectionSupervisorCheckpoint):
            raise TypeError("checkpoint must be ProtectionSupervisorCheckpoint")
        payload={"schema_version":cls.SCHEMA_VERSION,"state":checkpoint.state.value,"reason":checkpoint.reason,"observed_at":checkpoint.observed_at,"runtime_generation":checkpoint.runtime_generation,"checkpoint_sequence":checkpoint.checkpoint_sequence}
        encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
        if len(encoded)>cls.MAX_ENCODED_BYTES:
            raise ValueError("checkpoint payload is too large")
        return encoded

    @classmethod
    def decode(cls,encoded) -> ProtectionSupervisorCheckpoint:
        if type(encoded) is not bytes:
            raise TypeError("encoded checkpoint must be bytes")
        if len(encoded)>cls.MAX_ENCODED_BYTES:
            raise ValueError("checkpoint payload is too large")
        def unique_object(pairs):
            result={}
            for key,value in pairs:
                if key in result:
                    raise ValueError("duplicate checkpoint field")
                result[key]=value
            return result
        def reject_constant(value):
            raise ValueError("checkpoint numbers must be finite")
        try:
            payload=json.loads(encoded.decode("utf-8"),object_pairs_hook=unique_object,parse_constant=reject_constant)
        except (UnicodeDecodeError,json.JSONDecodeError) as error:
            raise ValueError("invalid checkpoint encoding") from error
        if type(payload) is not dict or set(payload)!=cls._FIELDS:
            raise ValueError("checkpoint fields are invalid")
        if type(payload["schema_version"]) is not int or payload["schema_version"]!=cls.SCHEMA_VERSION:
            raise ValueError("unsupported checkpoint schema")
        try:
            state=ProtectionState(payload["state"])
        except (TypeError,ValueError) as error:
            raise ValueError("invalid checkpoint state") from error
        return ProtectionSupervisorCheckpoint(state=state,reason=payload["reason"],observed_at=payload["observed_at"],runtime_generation=payload["runtime_generation"],checkpoint_sequence=payload["checkpoint_sequence"])


class ProtectionSupervisorCheckpointStore:
    def __init__(self,path) -> None:
        self.path=Path(path)

    def _write_encoded(self,encoded: bytes) -> None:
        parent=self.path.parent
        descriptor=None
        temporary_path=None
        try:
            descriptor,temporary_name=tempfile.mkstemp(prefix=self.path.name+".",suffix=".tmp",dir=parent)
            temporary_path=Path(temporary_name)
            os.fchmod(descriptor,0o600)
            with os.fdopen(descriptor,"wb") as temporary:
                descriptor=None
                temporary.write(encoded)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path,self.path)
            temporary_path=None
            directory_descriptor=os.open(parent,os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass

    def _read_encoded(self,maximum_bytes: int) -> bytes:
        with self.path.open("rb") as checkpoint_file:
            return checkpoint_file.read(maximum_bytes+1)

    def save(self,checkpoint) -> None:
        self._write_encoded(ProtectionSupervisorCheckpointCodec.encode(checkpoint))

    def load(self) -> ProtectionSupervisorCheckpoint:
        encoded=self._read_encoded(ProtectionSupervisorCheckpointCodec.MAX_ENCODED_BYTES)
        return ProtectionSupervisorCheckpointCodec.decode(encoded)


class AuthenticatedProtectionSupervisorCheckpointStore(ProtectionSupervisorCheckpointStore):
    ENVELOPE_VERSION=1
    MAX_ENVELOPE_BYTES=8192
    _FIELDS=frozenset(("envelope_version","key_id","payload","signature"))

    def __init__(self,path,*,signing_key,verifiers) -> None:
        super().__init__(path)
        if signing_key is None or type(getattr(signing_key,"key_id",None)) is not str or not signing_key.key_id.strip():
            raise ValueError("signing_key is invalid")
        if type(verifiers) is not dict or not verifiers:
            raise ValueError("verifiers must be nonempty")
        trusted_verifiers=dict(verifiers)
        verifier=trusted_verifiers.get(signing_key.key_id)
        if verifier is None or getattr(verifier,"key_id",None)!=signing_key.key_id:
            raise ValueError("signing key verifier is unavailable")
        verification_probe=b"AQSS_CHECKPOINT_SIGNING_KEY_VERIFICATION_V1"
        try:
            probe_signature=signing_key.sign(verification_probe)
            verified=type(probe_signature) is str and bool(probe_signature) and verifier.verify(verification_probe,probe_signature) is True
        except Exception:
            verified=False
        if not verified:
            raise ValueError("signing key verifier is unavailable")
        self.signing_key=signing_key
        self.verifiers=trusted_verifiers

    def save(self,checkpoint) -> None:
        payload=ProtectionSupervisorCheckpointCodec.encode(checkpoint)
        signature=self.signing_key.sign(payload)
        if type(signature) is not str or not signature:
            raise ValueError("checkpoint signature is invalid")
        envelope={"envelope_version":self.ENVELOPE_VERSION,"key_id":self.signing_key.key_id,"payload":base64.b64encode(payload).decode("ascii"),"signature":signature}
        encoded=json.dumps(envelope,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
        if len(encoded)>self.MAX_ENVELOPE_BYTES:
            raise ValueError("checkpoint envelope is too large")
        self._write_encoded(encoded)

    def load(self) -> ProtectionSupervisorCheckpoint:
        try:
            encoded=self._read_encoded(self.MAX_ENVELOPE_BYTES)
            if len(encoded)>self.MAX_ENVELOPE_BYTES:
                raise ValueError("checkpoint envelope is too large")
            def unique_object(pairs):
                result={}
                for key,value in pairs:
                    if key in result:
                        raise ValueError("duplicate checkpoint envelope field")
                    result[key]=value
                return result
            envelope=json.loads(encoded.decode("utf-8"),object_pairs_hook=unique_object)
            if type(envelope) is not dict or set(envelope)!=self._FIELDS:
                raise ValueError("checkpoint envelope fields are invalid")
            if type(envelope["envelope_version"]) is not int or envelope["envelope_version"]!=self.ENVELOPE_VERSION:
                raise ValueError("checkpoint envelope version is invalid")
            key_id=envelope["key_id"]
            if type(key_id) is not str or key_id not in self.verifiers:
                raise ValueError("checkpoint key is unknown")
            if type(envelope["payload"]) is not str or type(envelope["signature"]) is not str:
                raise ValueError("checkpoint envelope values are invalid")
            payload=base64.b64decode(envelope["payload"].encode("ascii"),validate=True)
            verifier=self.verifiers[key_id]
            if getattr(verifier,"key_id",None)!=key_id or not verifier.verify(payload,envelope["signature"]):
                raise ValueError("checkpoint signature is invalid")
            return ProtectionSupervisorCheckpointCodec.decode(payload)
        except Exception as error:
            raise ValueError("checkpoint authentication failed") from error


@dataclass(frozen=True,slots=True)
class SignedCheckpointFreshnessRecord:
    installation_id:str
    sequence:int
    digest:str
    issuer_id:str
    algorithm:str="ECDSA_P256_SHA256"
    signature:str=""

    @property
    def canonical_bytes(self):
        payload={"algorithm":self.algorithm,"digest":self.digest,"installation_id":self.installation_id,"issuer_id":self.issuer_id,"sequence":self.sequence}
        return json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

    @classmethod
    def issue(cls,*,installation_id,sequence,digest,signing_key):
        if type(installation_id) is not str or not installation_id.strip() or installation_id!=installation_id.strip() or len(installation_id)>256 or any(ord(character)<33 or ord(character)>126 for character in installation_id):
            raise ValueError("installation_id is invalid")
        if type(sequence) is not int or not 1<=sequence<=2**63-1:
            raise ValueError("checkpoint sequence is invalid")
        if type(digest) is not str or len(digest)!=64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("checkpoint digest is invalid")
        if signing_key is None or type(getattr(signing_key,"key_id",None)) is not str or not signing_key.key_id.strip() or getattr(signing_key,"algorithm",None)!="ECDSA_P256_SHA256":
            raise ValueError("witness signing key is invalid")
        unsigned=cls(installation_id=installation_id,sequence=sequence,digest=digest,issuer_id=signing_key.key_id,algorithm=signing_key.algorithm)
        signature=signing_key.sign(unsigned.canonical_bytes)
        if type(signature) is not str or not signature:
            raise ValueError("witness signature is invalid")
        return replace(unsigned,signature=signature)


class CheckpointFreshnessRecordDecision(Enum):
    ALLOW="ALLOW"
    MALFORMED="MALFORMED"
    INSTALLATION_MISMATCH="INSTALLATION_MISMATCH"
    UNKNOWN_ISSUER="UNKNOWN_ISSUER"
    INVALID_SIGNATURE="INVALID_SIGNATURE"


class CheckpointFreshnessRecordVerifier:
    def __init__(self,trusted_verifiers):
        self._trusted_verifiers=dict(trusted_verifiers)

    def validate(self,record,*,installation_id):
        if not isinstance(record,SignedCheckpointFreshnessRecord):
            return CheckpointFreshnessRecordDecision.MALFORMED
        if type(installation_id) is not str or not installation_id.strip() or installation_id!=installation_id.strip() or len(installation_id)>256 or any(ord(character)<33 or ord(character)>126 for character in installation_id):
            return CheckpointFreshnessRecordDecision.MALFORMED
        identifiers=(record.installation_id,record.digest,record.issuer_id,record.algorithm,record.signature)
        if any(type(value) is not str or not value.strip() for value in identifiers):
            return CheckpointFreshnessRecordDecision.MALFORMED
        if type(record.sequence) is not int or not 1<=record.sequence<=2**63-1 or len(record.digest)!=64 or any(character not in "0123456789abcdef" for character in record.digest):
            return CheckpointFreshnessRecordDecision.MALFORMED
        verifier=self._trusted_verifiers.get(record.issuer_id)
        if verifier is None:
            return CheckpointFreshnessRecordDecision.UNKNOWN_ISSUER
        try:
            verified=record.algorithm==getattr(verifier,"algorithm",None) and verifier.verify(record.canonical_bytes,record.signature) is True
        except Exception:
            verified=False
        if not verified:
            return CheckpointFreshnessRecordDecision.INVALID_SIGNATURE
        if record.installation_id!=installation_id:
            return CheckpointFreshnessRecordDecision.INSTALLATION_MISMATCH
        return CheckpointFreshnessRecordDecision.ALLOW


class VerifiedCheckpointFreshnessWitness:
    def __init__(self,witness,*,trusted_verifiers):
        if witness is None or not callable(getattr(witness,"read",None)) or not callable(getattr(witness,"compare_and_advance",None)):
            raise ValueError("checkpoint witness is invalid")
        self.witness=witness
        self.verifier=CheckpointFreshnessRecordVerifier(trusted_verifiers)

    def _verify(self,record,installation_id,*,allow_none):
        if record is None and allow_none:
            return None
        decision=self.verifier.validate(record,installation_id=installation_id)
        if decision is not CheckpointFreshnessRecordDecision.ALLOW:
            raise CheckpointFreshnessAnchorUnavailable("checkpoint witness authentication failed")
        return record.sequence,record.digest

    def read(self,installation_id):
        return self._verify(self.witness.read(installation_id),installation_id,allow_none=True)

    def compare_and_advance(self,installation_id,sequence,digest):
        verified=self._verify(self.witness.compare_and_advance(installation_id,sequence,digest),installation_id,allow_none=False)
        if verified!=(sequence,digest):
            raise CheckpointFreshnessAnchorUnavailable("checkpoint witness response is invalid")
        return verified


class SigningCheckpointFreshnessWitness:
    def __init__(self,witness,*,signing_key):
        if witness is None or not callable(getattr(witness,"read",None)) or not callable(getattr(witness,"compare_and_advance",None)):
            raise ValueError("checkpoint witness is invalid")
        if signing_key is None or type(getattr(signing_key,"key_id",None)) is not str or not signing_key.key_id.strip() or getattr(signing_key,"algorithm",None)!="ECDSA_P256_SHA256" or not callable(getattr(signing_key,"sign",None)):
            raise ValueError("witness signing key is invalid")
        self.witness=witness
        self.signing_key=signing_key

    def _sign(self,installation_id,record,*,allow_none):
        if record is None and allow_none:
            return None
        if type(record) is not tuple or len(record)!=2:
            raise ValueError("checkpoint witness response is invalid")
        sequence,digest=record
        return SignedCheckpointFreshnessRecord.issue(installation_id=installation_id,sequence=sequence,digest=digest,signing_key=self.signing_key)

    def read(self,installation_id):
        return self._sign(installation_id,self.witness.read(installation_id),allow_none=True)

    def compare_and_advance(self,installation_id,sequence,digest):
        record=self.witness.compare_and_advance(installation_id,sequence,digest)
        if record!=(sequence,digest):
            raise ValueError("checkpoint witness response is invalid")
        return self._sign(installation_id,record,allow_none=False)


class InMemoryCheckpointFreshnessAnchor:
    """Process-local reference semantics; not a durable security boundary."""

    def __init__(self) -> None:
        self._lock=RLock()
        self._record=None

    def read(self):
        with self._lock:
            return self._record

    def advance(self,sequence,digest) -> None:
        if type(sequence) is not int or not 1<=sequence<=2**63-1:
            raise ValueError("checkpoint sequence is invalid")
        if type(digest) is not str or len(digest)!=64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("checkpoint digest is invalid")
        with self._lock:
            if self._record is None:
                if sequence!=1:
                    raise ValueError("checkpoint sequence is not monotonic")
                self._record=(sequence,digest)
                return
            current_sequence,current_digest=self._record
            if sequence==current_sequence:
                if digest==current_digest:
                    return
                raise ValueError("checkpoint freshness conflict")
            if sequence!=current_sequence+1:
                raise ValueError("checkpoint sequence is not monotonic")
            self._record=(sequence,digest)


class InMemoryCheckpointFreshnessWitness:
    """Reference server semantics; production deployments require independent durable storage."""

    def __init__(self) -> None:
        self._lock=RLock()
        self._records={}

    @staticmethod
    def _validate_installation_id(installation_id) -> None:
        if type(installation_id) is not str or not installation_id or installation_id!=installation_id.strip() or len(installation_id)>256 or any(ord(character)<33 or ord(character)>126 for character in installation_id):
            raise ValueError("installation_id is invalid")

    def read(self,installation_id):
        self._validate_installation_id(installation_id)
        with self._lock:
            return self._records.get(installation_id)

    def compare_and_advance(self,installation_id,sequence,digest):
        self._validate_installation_id(installation_id)
        if type(sequence) is not int or not 1<=sequence<=2**63-1:
            raise ValueError("checkpoint sequence is invalid")
        if type(digest) is not str or len(digest)!=64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("checkpoint digest is invalid")
        proposed=(sequence,digest)
        with self._lock:
            current=self._records.get(installation_id)
            if current is None:
                if sequence!=1:
                    raise ValueError("checkpoint sequence is not monotonic")
                self._records[installation_id]=proposed
                return proposed
            if sequence==current[0]:
                if proposed==current:
                    return current
                raise ValueError("checkpoint freshness conflict")
            if sequence!=current[0]+1:
                raise ValueError("checkpoint sequence is not monotonic")
            self._records[installation_id]=proposed
            return proposed


class DurableFileCheckpointFreshnessWitness:
    """Reference durable witness; deploy outside the protected device trust domain."""

    _MAX_STATE_BYTES=1024*1024

    def __init__(self,state_path):
        if state_path is None:
            raise ValueError("checkpoint witness state path is invalid")
        self._state_path=Path(state_path)
        self._lock_path=Path(str(self._state_path)+".lock")
        self._lock=RLock()
        self._records={}
        with self._state_guard(exclusive=False):
            pass

    def _load_state(self):
        if not self._state_path.exists():
            self._records={}
            return
        def reject_duplicates(pairs):
            result={}
            for key,value in pairs:
                if key in result:
                    raise ValueError("invalid checkpoint witness state")
                result[key]=value
            return result
        with self._state_path.open("r",encoding="utf-8") as handle:
            if os.fstat(handle.fileno()).st_size>self._MAX_STATE_BYTES:
                raise ValueError("checkpoint witness state is too large")
            raw=json.load(handle,object_pairs_hook=reject_duplicates)
        if type(raw) is not dict or set(raw)!={"version","records"} or raw.get("version")!=1 or type(raw["records"]) is not dict:
            raise ValueError("invalid checkpoint witness state")
        records={}
        for installation_id,record in raw["records"].items():
            InMemoryCheckpointFreshnessWitness._validate_installation_id(installation_id)
            if type(record) is not list or len(record)!=2:
                raise ValueError("invalid checkpoint witness record")
            sequence,digest=record
            if type(sequence) is not int or not 1<=sequence<=2**63-1 or type(digest) is not str or len(digest)!=64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError("invalid checkpoint witness record")
            records[installation_id]=(sequence,digest)
        self._records=records

    def _save_state(self,records):
        self._state_path.parent.mkdir(parents=True,exist_ok=True)
        payload={"version":1,"records":{installation_id:list(record) for installation_id,record in records.items()}}
        encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
        if len(encoded)>self._MAX_STATE_BYTES:
            raise ValueError("checkpoint witness state is too large")
        descriptor,temp_path=tempfile.mkstemp(prefix=self._state_path.name+".",suffix=".tmp",dir=str(self._state_path.parent))
        try:
            with os.fdopen(descriptor,"wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path,self._state_path)
            directory_fd=os.open(str(self._state_path.parent),os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @contextmanager
    def _state_guard(self,*,exclusive):
        with self._lock:
            self._lock_path.parent.mkdir(parents=True,exist_ok=True)
            with self._lock_path.open("a+") as lock_handle:
                fcntl.flock(lock_handle.fileno(),fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                try:
                    self._load_state()
                    yield
                finally:
                    fcntl.flock(lock_handle.fileno(),fcntl.LOCK_UN)

    def read(self,installation_id):
        InMemoryCheckpointFreshnessWitness._validate_installation_id(installation_id)
        with self._state_guard(exclusive=False):
            return self._records.get(installation_id)

    def compare_and_advance(self,installation_id,sequence,digest):
        InMemoryCheckpointFreshnessWitness._validate_installation_id(installation_id)
        if type(sequence) is not int or not 1<=sequence<=2**63-1:
            raise ValueError("checkpoint sequence is invalid")
        if type(digest) is not str or len(digest)!=64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("checkpoint digest is invalid")
        proposed=(sequence,digest)
        with self._state_guard(exclusive=True):
            current=self._records.get(installation_id)
            if current is None:
                if sequence!=1:
                    raise ValueError("checkpoint sequence is not monotonic")
            elif sequence==current[0]:
                if proposed==current:
                    return current
                raise ValueError("checkpoint freshness conflict")
            elif sequence!=current[0]+1:
                raise ValueError("checkpoint sequence is not monotonic")
            candidate=dict(self._records)
            candidate[installation_id]=proposed
            self._save_state(candidate)
            self._records=candidate
            return proposed


class WitnessedCheckpointFreshnessAnchor:
    def __init__(self,witness,*,installation_id) -> None:
        if witness is None or not callable(getattr(witness,"read",None)) or not callable(getattr(witness,"compare_and_advance",None)):
            raise ValueError("checkpoint witness is invalid")
        InMemoryCheckpointFreshnessWitness._validate_installation_id(installation_id)
        self.witness=witness
        self.installation_id=installation_id

    def read(self):
        try:
            record=self.witness.read(self.installation_id)
        except Exception as error:
            raise CheckpointFreshnessAnchorUnavailable("checkpoint witness unavailable") from error
        if record is None:
            return None
        if type(record) is not tuple or len(record)!=2 or type(record[0]) is not int or not 1<=record[0]<=2**63-1 or type(record[1]) is not str or len(record[1])!=64 or any(character not in "0123456789abcdef" for character in record[1]):
            raise CheckpointFreshnessAnchorUnavailable("checkpoint witness response is invalid")
        return record

    def advance(self,sequence,digest) -> None:
        if type(sequence) is not int or not 1<=sequence<=2**63-1:
            raise ValueError("checkpoint sequence is invalid")
        if type(digest) is not str or len(digest)!=64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("checkpoint digest is invalid")
        try:
            record=self.witness.compare_and_advance(self.installation_id,sequence,digest)
        except CheckpointFreshnessAnchorUnavailable:
            raise
        except ValueError:
            raise
        except Exception as error:
            raise CheckpointFreshnessAnchorUnavailable("checkpoint witness unavailable") from error
        if record!=(sequence,digest):
            raise CheckpointFreshnessAnchorUnavailable("checkpoint witness response is invalid")


class CheckpointFreshnessAnchorUnavailable(ValueError):
    pass


class CheckpointRollbackDetected(ValueError):
    pass


class RollbackProtectedProtectionSupervisorCheckpointStore(AuthenticatedProtectionSupervisorCheckpointStore):
    def __init__(self,path,*,signing_key,verifiers,freshness_anchor) -> None:
        super().__init__(path,signing_key=signing_key,verifiers=verifiers)
        if freshness_anchor is None or not callable(getattr(freshness_anchor,"read",None)) or not callable(getattr(freshness_anchor,"advance",None)):
            raise ValueError("freshness_anchor is invalid")
        self.freshness_anchor=freshness_anchor

    @staticmethod
    def _commitment(checkpoint) -> tuple[int,str]:
        payload=ProtectionSupervisorCheckpointCodec.encode(checkpoint)
        return checkpoint.checkpoint_sequence,hashlib.sha256(payload).hexdigest()

    def save(self,checkpoint) -> None:
        sequence,digest=self._commitment(checkpoint)
        try:
            self.freshness_anchor.advance(sequence,digest)
        except CheckpointFreshnessAnchorUnavailable:
            raise
        except Exception as error:
            raise ValueError("checkpoint freshness advance failed") from error
        super().save(checkpoint)

    def load(self) -> ProtectionSupervisorCheckpoint:
        checkpoint=super().load()
        expected=self._commitment(checkpoint)
        try:
            record=self.freshness_anchor.read()
        except Exception as error:
            raise CheckpointFreshnessAnchorUnavailable("checkpoint freshness anchor unavailable") from error
        if type(record) is not tuple or len(record)!=2 or type(record[0]) is not int or type(record[1]) is not str:
            raise CheckpointFreshnessAnchorUnavailable("checkpoint freshness anchor unavailable")
        if record!=expected:
            raise CheckpointRollbackDetected("checkpoint rollback detected")
        return checkpoint


class ProtectionSupervisorCheckpointRestorer:
    def restore_from_store(self,supervisor,store,*,current_runtime_generation: str,now: float,monotonic_now: float | None=None) -> ProtectionState:
        if not isinstance(supervisor,ProtectionSupervisor):
            raise TypeError("supervisor must be ProtectionSupervisor")
        if not isinstance(store,ProtectionSupervisorCheckpointStore):
            raise TypeError("store must be ProtectionSupervisorCheckpointStore")
        if type(current_runtime_generation) is not str or not current_runtime_generation.strip() or current_runtime_generation!=current_runtime_generation.strip():
            raise ValueError("current_runtime_generation must be a nonempty identifier")
        try:
            checkpoint=store.load()
        except CheckpointRollbackDetected:
            return supervisor.require_revalidation("CHECKPOINT_ROLLBACK_DETECTED",observed_at=None,now=now,monotonic_now=monotonic_now)
        except CheckpointFreshnessAnchorUnavailable:
            return supervisor.require_revalidation("CHECKPOINT_FRESHNESS_ANCHOR_UNAVAILABLE",observed_at=None,now=now,monotonic_now=monotonic_now)
        except (OSError,TypeError,ValueError):
            return supervisor.require_revalidation("CHECKPOINT_UNAVAILABLE_OR_INVALID",observed_at=None,now=now,monotonic_now=monotonic_now)
        return self.restore(supervisor,checkpoint,current_runtime_generation=current_runtime_generation,now=now,monotonic_now=monotonic_now)

    def restore(self,supervisor,checkpoint,*,current_runtime_generation: str,now: float,monotonic_now: float | None=None) -> ProtectionState:
        if not isinstance(supervisor,ProtectionSupervisor):
            raise TypeError("supervisor must be ProtectionSupervisor")
        if not isinstance(checkpoint,ProtectionSupervisorCheckpoint):
            raise TypeError("checkpoint must be ProtectionSupervisorCheckpoint")
        if type(current_runtime_generation) is not str or not current_runtime_generation.strip() or current_runtime_generation!=current_runtime_generation.strip():
            raise ValueError("current_runtime_generation must be a nonempty identifier")
        if isinstance(now,bool) or not isinstance(now,(int,float)) or not math.isfinite(now):
            raise ValueError("now must be finite")
        if monotonic_now is not None and (isinstance(monotonic_now,bool) or not isinstance(monotonic_now,(int,float)) or not math.isfinite(monotonic_now)):
            raise ValueError("monotonic_now must be finite")
        if checkpoint.state is ProtectionState.UNKNOWN_PHYSICAL_STATE:
            reason=checkpoint.reason
            physical_state_known=False
        else:
            if checkpoint.runtime_generation==current_runtime_generation:
                reason="RUNTIME_GENERATION_REUSE"
            else:
                reason="HISTORICAL_ACTIVE_REQUIRES_REVALIDATION" if checkpoint.state is ProtectionState.ACTIVE else "CHECKPOINT_REVALIDATION_REQUIRED"
            physical_state_known=True
        return supervisor.require_revalidation(reason,observed_at=checkpoint.observed_at,now=now,monotonic_now=monotonic_now,physical_state_known=physical_state_known)
