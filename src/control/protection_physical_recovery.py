import hashlib
import json
import secrets
from dataclasses import dataclass
from enum import Enum, auto

from .protection_supervisor import ProtectionState, ProtectionSupervisor
from ..device_fabric.physical_recovery_store import PhysicalRecoveryStatus, PhysicalRecoveryStore


class PhysicalTransportFinalityOutcome(Enum):
    APPLIED = auto()
    NOT_APPLIED = auto()


@dataclass(frozen=True, slots=True)
class PhysicalTransportFinalityEvidence:
    transaction_id: str
    intent_id: str
    device_id: str
    operation: str
    authorization_digest: str
    capability_digest: str
    outcome: PhysicalTransportFinalityOutcome
    query_nonce: str
    report_bytes: bytes
    report_digest: str
    endpoint_key_id: str
    algorithm: str
    signature: str


class ProtectionPhysicalRecoveryCoordinator:
    def __init__(self, supervisor: ProtectionSupervisor, recovery_store: PhysicalRecoveryStore, *, finality_source=None, endpoint_verifiers=None, query_nonce_factory=None) -> None:
        if not isinstance(supervisor,ProtectionSupervisor):
            raise ValueError("ProtectionSupervisor is required")
        if not isinstance(recovery_store,PhysicalRecoveryStore):
            raise ValueError("PhysicalRecoveryStore is required")
        if finality_source is not None and not callable(getattr(finality_source,"terminal_evidence",None)):
            raise ValueError("physical transport finality source is invalid")
        if query_nonce_factory is not None and not callable(query_nonce_factory):
            raise ValueError("physical transport finality query nonce factory is invalid")
        try:
            endpoint_verifiers={} if endpoint_verifiers is None else dict(endpoint_verifiers)
        except Exception:
            raise ValueError("physical endpoint verifiers are invalid") from None
        if any(type(key_id) is not str or not key_id.strip() or getattr(verifier,"key_id",None)!=key_id or type(getattr(verifier,"algorithm",None)) is not str or not verifier.algorithm.strip() or not callable(getattr(verifier,"verify",None)) for key_id,verifier in endpoint_verifiers.items()):
            raise ValueError("physical endpoint verifiers are invalid")
        self._supervisor=supervisor
        self._recovery_store=recovery_store
        self._finality_source=finality_source
        self._endpoint_verifiers=endpoint_verifiers
        self._query_nonce_factory=(lambda: secrets.token_hex(32)) if query_nonce_factory is None else query_nonce_factory

    def restore_pending(self, *, now: float, monotonic_now: float | None = None) -> ProtectionState:
        try:
            records=self._recovery_store.records()
        except Exception:
            self._supervisor.interrupt("PHYSICAL_RECOVERY_RESTORE_FAILURE",now=now,monotonic_now=monotonic_now,physical_state_known=False)
            return self._supervisor.state
        for record in records:
            if record.supervisor_release_completed:
                continue
            self._supervisor.interrupt("PENDING_PHYSICAL_RECOVERY",now=now,monotonic_now=monotonic_now,physical_state_known=False,physical_transaction_id=record.transaction_id)
            if record.finality_closed:
                outcome=PhysicalTransportFinalityOutcome.APPLIED if record.status is PhysicalRecoveryStatus.VERIFIED_APPLIED else PhysicalTransportFinalityOutcome.NOT_APPLIED
                try:
                    archived_report=json.loads(record.finality_report_bytes.decode("utf-8"))
                    query_nonce=archived_report.get("query_nonce") if type(archived_report) is dict else None
                except Exception:
                    continue
                evidence=PhysicalTransportFinalityEvidence(transaction_id=record.transaction_id,intent_id=record.intent_id,device_id=record.device_id,operation=record.operation,authorization_digest=record.authorization_digest,capability_digest=record.capability_digest,outcome=outcome,query_nonce=query_nonce,report_bytes=record.finality_report_bytes,report_digest=record.finality_report_digest,endpoint_key_id=record.finality_endpoint_key_id,algorithm=record.finality_algorithm,signature=record.finality_signature)
                if self._finality_matches(record,evidence,query_nonce=query_nonce) is not True:
                    continue
                self._supervisor.resolve_physical_transaction(record.transaction_id,now=now,monotonic_now=monotonic_now)
                self._recovery_store.confirm_supervisor_release(record)
        return self._supervisor.state

    def _finality_matches(self, record, evidence, *, query_nonce) -> bool:
        if type(evidence) is not PhysicalTransportFinalityEvidence:
            return False
        if type(evidence.outcome) is not PhysicalTransportFinalityOutcome or type(evidence.report_bytes) is not bytes or type(evidence.report_digest) is not str:
            return False
        if type(query_nonce) is not str or not 16 <= len(query_nonce) <= 128 or query_nonce != query_nonce.strip() or evidence.query_nonce != query_nonce:
            return False
        if any(type(value) is not str or not value.strip() for value in (evidence.endpoint_key_id,evidence.algorithm,evidence.signature)):
            return False
        canonical=json.dumps({"algorithm":evidence.algorithm,"authorization_digest":evidence.authorization_digest,"capability_digest":evidence.capability_digest,"device_id":evidence.device_id,"endpoint_key_id":evidence.endpoint_key_id,"intent_id":evidence.intent_id,"operation":evidence.operation,"outcome":evidence.outcome.name,"query_nonce":evidence.query_nonce,"transaction_id":evidence.transaction_id},sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
        if evidence.report_bytes != canonical or hashlib.sha256(evidence.report_bytes).hexdigest() != evidence.report_digest:
            return False
        verifier=self._endpoint_verifiers.get(evidence.endpoint_key_id)
        try:
            if verifier is None or getattr(verifier,"key_id",None)!=evidence.endpoint_key_id or getattr(verifier,"algorithm",None)!=evidence.algorithm or verifier.verify(evidence.report_bytes,evidence.signature) is not True:
                return False
        except Exception:
            return False
        if (evidence.transaction_id,evidence.intent_id,evidence.device_id,evidence.operation,evidence.authorization_digest,evidence.capability_digest)!=(record.transaction_id,record.intent_id,record.device_id,record.operation,record.authorization_digest,record.capability_digest):
            return False
        expected=PhysicalTransportFinalityOutcome.APPLIED if record.status is PhysicalRecoveryStatus.VERIFIED_APPLIED else PhysicalTransportFinalityOutcome.NOT_APPLIED
        return evidence.outcome is expected

    def resolve(self, transaction_id: str, *, now: float, monotonic_now: float | None = None) -> ProtectionState:
        if type(transaction_id) is not str or not transaction_id.strip() or transaction_id != transaction_id.strip():
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        record=self._recovery_store.get(transaction_id)
        if record is None:
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        if record.status not in (PhysicalRecoveryStatus.VERIFIED_APPLIED,PhysicalRecoveryStatus.VERIFIED_NOT_APPLIED):
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        if record.finality_closed:
            try:
                archived_report=json.loads(record.finality_report_bytes.decode("utf-8"))
                query_nonce=archived_report.get("query_nonce") if type(archived_report) is dict else None
            except Exception:
                return ProtectionState.UNKNOWN_PHYSICAL_STATE
            outcome=PhysicalTransportFinalityOutcome.APPLIED if record.status is PhysicalRecoveryStatus.VERIFIED_APPLIED else PhysicalTransportFinalityOutcome.NOT_APPLIED
            evidence=PhysicalTransportFinalityEvidence(transaction_id=record.transaction_id,intent_id=record.intent_id,device_id=record.device_id,operation=record.operation,authorization_digest=record.authorization_digest,capability_digest=record.capability_digest,outcome=outcome,query_nonce=query_nonce,report_bytes=record.finality_report_bytes,report_digest=record.finality_report_digest,endpoint_key_id=record.finality_endpoint_key_id,algorithm=record.finality_algorithm,signature=record.finality_signature)
            if self._finality_matches(record,evidence,query_nonce=query_nonce) is not True:
                return ProtectionState.UNKNOWN_PHYSICAL_STATE
            state=self._supervisor.resolve_physical_transaction(transaction_id,now=now,monotonic_now=monotonic_now)
            self._recovery_store.confirm_supervisor_release(record)
            return state
        if self._finality_source is None:
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        try:
            query_nonce=self._query_nonce_factory()
        except Exception:
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        if type(query_nonce) is not str or not 16 <= len(query_nonce) <= 128 or query_nonce != query_nonce.strip():
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        try:
            evidence=self._finality_source.terminal_evidence(record,query_nonce=query_nonce)
        except Exception:
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        if self._finality_matches(record,evidence,query_nonce=query_nonce) is not True:
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        try:
            closed=self._recovery_store.confirm_finality(record,report_digest=evidence.report_digest,report_bytes=evidence.report_bytes,endpoint_key_id=evidence.endpoint_key_id,algorithm=evidence.algorithm,signature=evidence.signature)
        except Exception:
            return ProtectionState.UNKNOWN_PHYSICAL_STATE
        state=self._supervisor.resolve_physical_transaction(transaction_id,now=now,monotonic_now=monotonic_now)
        self._recovery_store.confirm_supervisor_release(closed)
        return state
