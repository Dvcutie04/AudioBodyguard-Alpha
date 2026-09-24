from __future__ import annotations
import hashlib
import math
import time
from inspect import iscoroutinefunction
from dataclasses import dataclass
from typing import Any, Optional

from src.core.monotonic_clock_domain import current_monotonic_clock_domain_id,validate_monotonic_clock_domain_id
from src.control.authorized_intent import SignedActionIntent
from src.control.active_controller_lease import ActiveControllerLease
from src.control.capability_lease import SignedCapabilityLease
from src.control.controller_bound_intent import ControllerBoundActionIntent
from src.control.controller_bound_intent_firewall import ControllerBoundRejectionCode
from src.control.controller_lease_evidence import SignedControllerLeaseEvidence
from src.control.controller_authority_gate import ControllerAuthorityDecision,ControllerAuthorityGate
from src.control.controller_command_proof import SignedControllerCommandProof
from src.control.controller_lease_grant import SignedControllerLeaseGrant
from src.control.intent_firewall import IntentFirewall, AuthRejectionCode
from src.control.media_control_verified_state import VerifiedMediaControlState
from src.control.media_control_prior_state import MediaControlPriorState
from src.control.media_control_undo_candidate import MediaControlUndoCandidate
from src.control.protection_supervisor import ProtectionSupervisor, ProtectionUnavailableError
from src.control.protection_physical_recovery import ProtectionPhysicalRecoveryCoordinator
from src.device_fabric.contracts import AuthorizedActionIntent, ActuationStatus, DeviceState, CapabilityLease, PhysicalSnapshot, PhysicalVerificationRecord, VerificationStatus
from src.device_fabric.physical_commit_gate import PhysicalCommitGate, PreconditionResult
from src.device_fabric.transport import PhysicalTransport, PhysicalTransportTimeout, dispatch_physical_transport
from src.device_fabric.fenced_transport import FencedPhysicalTransport
from src.device_fabric.monotonic_fence_anchor import require_production_monotonic_anchor
from src.device_fabric.physical_recovery_store import PhysicalRecoveryPersistenceError, PhysicalRecoveryRecord, PhysicalRecoveryStatus, PhysicalRecoveryStore

class PhysicalCommitRejected(Exception):
    pass

@dataclass(frozen=True)
class BridgeResult:
    status: str
    intent_id: str
    receipt: Any = None
    rejection: Optional[Any] = None
    authorization_digest: Optional[str] = None
    transaction_id: Optional[str] = None
    capability_digest: Optional[str] = None
    verification: Any = None
    verified_state: Any = None
    prior_state: Any = None
    undo_candidate: Any = None

_POST_STATE_OBSERVER_UNSET=object()

class _ProtectionAdmissionInvalidated(RuntimeError):
    pass


class _ProtectionBoundTransport:
    def __init__(self,transport,supervisor,admission_generation):
        self._transport=transport
        self._supervisor=supervisor
        self._admission_generation=admission_generation

    @property
    def device(self):
        return self._transport.device

    def _require_admission(self):
        status=self._supervisor.require_automation(now=time.time(),monotonic_now=time.monotonic())
        if status.admission_generation != self._admission_generation:
            raise _ProtectionAdmissionInvalidated()

    async def execute_intent(self,intent,transaction_digest=None,capability_digest=None):
        self._require_admission()
        if type(self._transport) is FencedPhysicalTransport:
            return await self._transport.execute_intent(intent=intent,transaction_digest=transaction_digest,capability_digest=capability_digest,_final_admission_check=self._require_admission)
        return await self._transport.execute_intent(intent=intent,transaction_digest=transaction_digest,capability_digest=capability_digest)


class Gen3DeviceFabricBridge:
    def __init__(self, firewall: IntentFirewall, adapter: PhysicalTransport, *, transport_timeout_seconds: float = 2.0, recovery_store: Optional[PhysicalRecoveryStore] = None, protection_supervisor: Optional[ProtectionSupervisor] = None, controller_authority_gate: Optional[ControllerAuthorityGate] = None, monotonic_clock=time.monotonic, monotonic_clock_domain_id=None):
        if firewall is None: raise ValueError("IntentFirewall is required")
        if adapter is None or not isinstance(adapter,PhysicalTransport): raise ValueError("Device Fabric adapter with execute_intent() is required")
        if not iscoroutinefunction(adapter.execute_intent): raise ValueError("Device Fabric adapter must implement asynchronous PhysicalTransport")
        if protection_supervisor is not None and not isinstance(protection_supervisor,ProtectionSupervisor): raise ValueError("ProtectionSupervisor is required")
        if controller_authority_gate is not None and not isinstance(controller_authority_gate,ControllerAuthorityGate): raise ValueError("ControllerAuthorityGate is required")
        if not callable(monotonic_clock): raise ValueError("monotonic clock is required")
        self._monotonic_clock=monotonic_clock
        if monotonic_clock_domain_id is None: monotonic_clock_domain_id=current_monotonic_clock_domain_id()
        self._monotonic_clock_domain_id=validate_monotonic_clock_domain_id(monotonic_clock_domain_id)
        self.firewall=firewall
        self.adapter=adapter
        self.transport_timeout_seconds=transport_timeout_seconds
        self.recovery_store=recovery_store
        self.protection_supervisor=protection_supervisor
        self.controller_authority_gate=controller_authority_gate
        if self.protection_supervisor is not None and isinstance(self.recovery_store,PhysicalRecoveryStore):
            ProtectionPhysicalRecoveryCoordinator(self.protection_supervisor,self.recovery_store).restore_pending(now=time.time(),monotonic_now=time.monotonic())

    def _protected_transport(self,admission_generation=None):
        if self.protection_supervisor is None: return self.adapter
        if type(admission_generation) is not int: raise ValueError("protection admission generation is required")
        return _ProtectionBoundTransport(self.adapter,self.protection_supervisor,admission_generation)

    def _protection_rejection(self,intent,admission=None):
        if self.protection_supervisor is None: return None
        try:
            status=self.protection_supervisor.require_automation(now=time.time(),monotonic_now=time.monotonic())
        except ProtectionUnavailableError as exc:
            return BridgeResult("REJECTED",intent.intent_id,rejection="PROTECTION_"+exc.status.state.value)
        except Exception:
            return BridgeResult("REJECTED",intent.intent_id,rejection="PROTECTION_UNKNOWN_PHYSICAL_STATE")
        if admission is not None:
            if not admission:
                admission.append(status.admission_generation)
            elif admission[0] != status.admission_generation:
                return BridgeResult("REJECTED",intent.intent_id,rejection="PROTECTION_ADMISSION_INVALIDATED")
        return None

    def _record_indeterminate(self,intent,target,expected_pre_state,auth_digest,capability_digest,precondition_epoch=None):
        recorded_at=time.time()
        if self.recovery_store is not None:
            try:
                self.recovery_store.record(PhysicalRecoveryRecord(transaction_id=intent.transaction_id,intent_id=intent.intent_id,device_id=intent.device_id,operation=intent.operation,target_state_digest=target.state_digest,expected_pre_state_digest=expected_pre_state.state_digest,authorization_digest=auth_digest,capability_digest=capability_digest,recorded_at=recorded_at,status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,precondition_epoch=precondition_epoch))
            except Exception as exc:
                if self.protection_supervisor is not None:
                    self.protection_supervisor.interrupt("POST_CONDITION_UNOBSERVED",now=recorded_at,monotonic_now=time.monotonic(),physical_state_known=False)
                if isinstance(exc,PhysicalRecoveryPersistenceError):
                    raise
                raise PhysicalRecoveryPersistenceError(intent.transaction_id,capability_digest) from exc
        if self.protection_supervisor is not None:
            self.protection_supervisor.interrupt("POST_CONDITION_UNOBSERVED",now=recorded_at,monotonic_now=time.monotonic(),physical_state_known=False,physical_transaction_id=intent.transaction_id if self.recovery_store is not None else None)

    def _validate_lease(self, lease: SignedCapabilityLease) -> Optional[str]:
        verifier=getattr(self.firewall,"trusted_verifiers",{}).get(lease.issuer_id)
        if verifier is None: return "LEASE_ISSUER_UNKNOWN"
        if not verifier.verify(lease.canonical_bytes,lease.signature): return "LEASE_SIGNATURE_INVALID"
        return None

    def _authorization_digest(self, intent: SignedActionIntent) -> str:
        return hashlib.sha256(intent.canonical_bytes).hexdigest()

    def _translate_state(self,intent: SignedActionIntent,pre_state: DeviceState) -> DeviceState:
        state=DeviceState(power=pre_state.power,volume=pre_state.volume,muted=pre_state.muted,input_source=pre_state.input_source,channel=pre_state.channel,custom_state=dict(pre_state.custom_state),playback_position_seconds=pre_state.playback_position_seconds)
        p=dict(intent.parameters)
        op=intent.operation.upper()
        if op=="SET_POWER" and "power" in p: state.power=bool(p["power"])
        elif op=="SET_VOLUME" and set(p) == {"volume_percent"}:
            value=p["volume_percent"]
            if type(value) is not int or not 0<=value<=100:
                raise PhysicalCommitRejected("Invalid volume percent")
            state.volume=value
        elif op=="SET_VOLUME" and set(p) == {"volume"}: state.volume=p["volume"]
        elif op=="SET_EQ_BANDS" and set(p) == {"bands"}:
            bands=p["bands"]
            if type(bands) is not list or not 1<=len(bands)<=10:
                raise PhysicalCommitRejected("Invalid EQ bands")
            normalized_bands=[]
            previous_frequency=None
            for band in bands:
                if type(band) is not dict or set(band) != {"frequency_hz", "gain_db"}:
                    raise PhysicalCommitRejected("Invalid EQ band")
                frequency=band["frequency_hz"]
                gain=band["gain_db"]
                if type(frequency) not in (int, float) or not 20.0<=frequency<=20000.0:
                    raise PhysicalCommitRejected("Invalid EQ band frequency")
                if type(gain) not in (int, float) or not -12.0<=gain<=12.0:
                    raise PhysicalCommitRejected("Invalid EQ band gain")
                if previous_frequency is not None and frequency<=previous_frequency:
                    raise PhysicalCommitRejected("EQ band frequencies must increase")
                normalized_bands.append({"frequency_hz": float(frequency), "gain_db": float(gain)})
                previous_frequency=frequency
            state.custom_state["eq_bands"]=normalized_bands
            state.custom_state.pop("eq_preset", None)
        elif op=="SET_EQ_PRESET" and set(p) == {"preset"}:
            preset=p["preset"]
            if type(preset) is not str or preset not in {"DIALOGUE", "MUSIC", "NIGHT", "FLAT"}:
                raise PhysicalCommitRejected("Invalid EQ preset")
            state.custom_state["eq_preset"]=preset
            state.custom_state.pop("eq_bands", None)
        elif op=="SET_CAPTIONS_ENABLED" and set(p) == {"enabled"}:
            enabled=p["enabled"]
            if type(enabled) is not bool:
                raise PhysicalCommitRejected("Invalid captions enabled value")
            state.custom_state["captions_enabled"]=enabled
        elif op=="SET_MUTED" and "muted" in p: state.muted=bool(p["muted"])
        elif op=="SET_INPUT_SOURCE" and "input_source" in p: state.input_source=str(p["input_source"])
        elif op=="SET_CHANNEL" and "channel" in p: state.channel=str(p["channel"])
        elif op=="SET_PLAYBACK_POSITION" and "playback_position_seconds" in p:
            value=p["playback_position_seconds"]
            current=pre_state.playback_position_seconds
            segment_start=p.get("segment_start_seconds")
            segment_end=p.get("segment_end_seconds")
            if type(value) not in (int,float) or not math.isfinite(value) or value<0:
                raise PhysicalCommitRejected("Invalid playback position")
            if type(current) not in (int,float) or not math.isfinite(current) or current<0:
                raise PhysicalCommitRejected("Invalid observed playback position")
            if type(segment_start) not in (int,float) or not math.isfinite(segment_start) or segment_start<0 or type(segment_end) not in (int,float) or not math.isfinite(segment_end) or segment_end<=segment_start:
                raise PhysicalCommitRejected("Invalid playback evidence segment")
            if value!=segment_end:
                raise PhysicalCommitRejected("PLAYBACK_TARGET_EVIDENCE_MISMATCH")
            if not segment_start<=current<segment_end:
                raise PhysicalCommitRejected("PLAYBACK_OUTSIDE_EVIDENCE_SEGMENT")
            if value<=current:
                raise PhysicalCommitRejected("Playback position must advance")
            state.playback_position_seconds=float(value)
        elif op=="SET_ATTENUATION" and "db" in p: state.custom_state["db"]=p["db"]
        else: raise PhysicalCommitRejected("Unsupported or malformed operation: "+intent.operation)
        return state

    async def authorize_and_commit(self,intent: SignedActionIntent,lease: SignedCapabilityLease,physical_lease: CapabilityLease,snapshot: PhysicalSnapshot,expected_pre_state: DeviceState,commit_gate: Optional[PhysicalCommitGate]=None,world_state_evidence_digest: Optional[str]=None,post_state_observer: Any=_POST_STATE_OBSERVER_UNSET,observed_state_evidence_digest: Optional[str]=None,controller_evidence: Optional[SignedControllerLeaseEvidence]=None,now: Optional[float]=None,controller_grant: Optional[SignedControllerLeaseGrant]=None,controller_command_proof: Optional[SignedControllerCommandProof]=None,controller_request=None,controller_result=None) -> BridgeResult:
        if intent is None or lease is None or physical_lease is None or snapshot is None or expected_pre_state is None:
            raise PhysicalCommitRejected("Missing physical commit input")
        admission=[]
        protection_rejection=self._protection_rejection(intent,admission)
        if protection_rejection is not None: return protection_rejection
        if self.controller_authority_gate is not None:
            remote_supplied=controller_request is not None or controller_result is not None
            legacy_supplied=controller_grant is not None
            if remote_supplied and legacy_supplied:
                return BridgeResult("REJECTED",intent.intent_id,rejection="CONTROLLER_AUTHORITY_INVALID")
            if controller_command_proof is None or (remote_supplied and (controller_request is None or controller_result is None)) or (not remote_supplied and controller_grant is None):
                return BridgeResult("REJECTED",intent.intent_id,rejection="CONTROLLER_AUTHORITY_REQUIRED")
            try:
                controller_action_digest=self._authorization_digest(intent)
                if remote_supplied:
                    controller_decision=self.controller_authority_gate.validate_remote(result=controller_result,request=controller_request,proof=controller_command_proof,now=now,expected_action_digest=controller_action_digest)
                else:
                    controller_decision=self.controller_authority_gate.validate(grant=controller_grant,proof=controller_command_proof,now=now,expected_action_digest=controller_action_digest)
            except Exception:
                return BridgeResult("REJECTED",intent.intent_id,rejection="CONTROLLER_AUTHORITY_INVALID")
            if controller_decision is not ControllerAuthorityDecision.ALLOW:
                return BridgeResult("REJECTED",intent.intent_id,rejection=controller_decision)
        elif controller_grant is not None or controller_command_proof is not None or controller_request is not None or controller_result is not None:
            return BridgeResult("REJECTED",intent.intent_id,rejection="CONTROLLER_AUTHORITY_UNCONFIGURED")
        if isinstance(intent, ControllerBoundActionIntent) and controller_evidence is None:
            return BridgeResult("REJECTED",intent.intent_id,rejection=ControllerBoundRejectionCode.CONTROLLER_EVIDENCE_REQUIRED)
        try:
            provenance_invalid=world_state_evidence_digest is not None and (not isinstance(world_state_evidence_digest,str) or not world_state_evidence_digest.strip())
        except Exception:
            return BridgeResult("REJECTED",intent.intent_id,rejection="WORLD_STATE_PROVENANCE_INVALID")
        if provenance_invalid: return BridgeResult("REJECTED",intent.intent_id,rejection="WORLD_STATE_PROVENANCE_INVALID")
        try:
            media_operation=str(intent.operation).upper()=="SET_PLAYBACK_POSITION"
        except Exception:
            media_operation=False
        media_evidence_mismatch=False
        if media_operation:
            try:
                signed_evidence_digest=dict(intent.parameters).get("evidence_digest")
                media_evidence_mismatch=type(signed_evidence_digest) is not str or not signed_evidence_digest.strip() or world_state_evidence_digest!=signed_evidence_digest
            except Exception:
                media_evidence_mismatch=True
        if media_evidence_mismatch: return BridgeResult("REJECTED",intent.intent_id,rejection="WORLD_STATE_EVIDENCE_MISMATCH")
        if media_operation and isinstance(intent,ControllerBoundActionIntent):
            try:
                signed_clock_domain_id=dict(intent.parameters).get("evidence_clock_domain_id")
            except Exception:
                signed_clock_domain_id=None
            if type(signed_clock_domain_id) is not str or not signed_clock_domain_id.strip():
                return BridgeResult("REJECTED",intent.intent_id,rejection="MEDIA_EVIDENCE_CLOCK_DOMAIN_INVALID")
            if signed_clock_domain_id!=self._monotonic_clock_domain_id:
                return BridgeResult("REJECTED",intent.intent_id,rejection="MEDIA_EVIDENCE_CLOCK_DOMAIN_MISMATCH")
            try:
                observed_monotonic=dict(intent.parameters).get("observed_monotonic")
                evidence_expires_monotonic=dict(intent.parameters).get("evidence_expires_monotonic")
                commit_monotonic=self._monotonic_clock()
                media_freshness_invalid=type(observed_monotonic) not in (int,float) or type(evidence_expires_monotonic) not in (int,float) or type(commit_monotonic) not in (int,float) or not 0<=observed_monotonic<float("inf") or not observed_monotonic<evidence_expires_monotonic<float("inf") or not observed_monotonic<=commit_monotonic<float("inf")
            except Exception:
                media_freshness_invalid=True
            if media_freshness_invalid:
                return BridgeResult("REJECTED",intent.intent_id,rejection="MEDIA_EVIDENCE_FRESHNESS_INVALID")
            if commit_monotonic>evidence_expires_monotonic:
                return BridgeResult("REJECTED",intent.intent_id,rejection="MEDIA_EVIDENCE_EXPIRED")
            media_verification_missing=post_state_observer is _POST_STATE_OBSERVER_UNSET or post_state_observer is None or not callable(post_state_observer) or type(observed_state_evidence_digest) is not str or not observed_state_evidence_digest.strip()
            if media_verification_missing:
                return BridgeResult("REJECTED",intent.intent_id,rejection="MEDIA_POST_STATE_VERIFICATION_REQUIRED")
        try:
            observed_provenance_invalid=observed_state_evidence_digest is not None and (not isinstance(observed_state_evidence_digest,str) or not observed_state_evidence_digest.strip())
        except Exception:
            return BridgeResult("REJECTED",intent.intent_id,rejection="OBSERVED_STATE_PROVENANCE_INVALID")
        if observed_provenance_invalid: return BridgeResult("REJECTED",intent.intent_id,rejection="OBSERVED_STATE_PROVENANCE_INVALID")
        if observed_state_evidence_digest is not None and (post_state_observer is _POST_STATE_OBSERVER_UNSET or post_state_observer is None): return BridgeResult("REJECTED",intent.intent_id,rejection="OBSERVED_STATE_PROVENANCE_INVALID")
        if controller_evidence is not None:
            try:
                validation=self.firewall.validate(intent,lease,controller_evidence,now=now)
            except Exception:
                return BridgeResult("REJECTED",intent.intent_id,rejection=ControllerBoundRejectionCode.INVALID_INPUT)
            if isinstance(validation,ControllerBoundRejectionCode): return BridgeResult("REJECTED",intent.intent_id,rejection=validation)
            if not isinstance(validation,ControllerBoundActionIntent) or validation is not intent: return BridgeResult("REJECTED",intent.intent_id,rejection=ControllerBoundRejectionCode.INVALID_INPUT)
        else:
            try:
                lease_error=self._validate_lease(lease)
            except Exception:
                return BridgeResult("REJECTED",intent.intent_id,rejection="LEASE_SIGNATURE_INVALID")
            if lease_error: return BridgeResult("REJECTED",intent.intent_id,rejection=lease_error)
            try:
                issuer_mismatch=intent.issuer_id!=lease.issuer_id
            except Exception:
                return BridgeResult("REJECTED",intent.intent_id,rejection="ISSUER_MISMATCH")
            if issuer_mismatch: return BridgeResult("REJECTED",intent.intent_id,rejection="ISSUER_MISMATCH")
            try:
                validation=self.firewall.validate_intent(intent,lease)
            except Exception:
                return BridgeResult("REJECTED",intent.intent_id,rejection=AuthRejectionCode.AUTH_SIGNATURE_INVALID)
            if isinstance(validation,AuthRejectionCode): return BridgeResult("REJECTED",intent.intent_id,rejection=validation)
            if not isinstance(validation,SignedActionIntent): return BridgeResult("REJECTED",intent.intent_id,rejection=AuthRejectionCode.AUTH_SIGNATURE_INVALID)
            if validation is not intent: return BridgeResult("REJECTED",intent.intent_id,rejection=AuthRejectionCode.AUTH_SIGNATURE_INVALID)
        try:
            identity=getattr(getattr(self.adapter,"device",None),"identity",None)
            device_id=getattr(identity,"device_id",None)
        except Exception:
            return BridgeResult("REJECTED",intent.intent_id,rejection=PreconditionResult.DEVICE_MISMATCH)
        try:
            adapter_device_mismatch=intent.device_id!=device_id
        except Exception:
            return BridgeResult("REJECTED",intent.intent_id,rejection=PreconditionResult.DEVICE_MISMATCH)
        if adapter_device_mismatch: return BridgeResult("REJECTED",intent.intent_id,rejection=PreconditionResult.DEVICE_MISMATCH)
        if isinstance(intent,ControllerBoundActionIntent) and intent.expected_pre_state_digest is not None:
            try:
                signed_precondition_drift=intent.expected_pre_state_digest!=expected_pre_state.state_digest
            except Exception:
                return BridgeResult("REJECTED",intent.intent_id,rejection=PreconditionResult.PRECONDITION_DRIFT)
            if signed_precondition_drift:
                return BridgeResult("REJECTED",intent.intent_id,rejection=PreconditionResult.PRECONDITION_DRIFT)
        try: target=self._translate_state(intent,snapshot.state)
        except PhysicalCommitRejected as exc: return BridgeResult("REJECTED",intent.intent_id,rejection=str(exc))
        except Exception: return BridgeResult("REJECTED",intent.intent_id,rejection="STATE_TRANSLATION_INVALID")
        if media_operation and not isinstance(intent,ControllerBoundActionIntent):
            return BridgeResult("REJECTED",intent.intent_id,rejection="CONTROLLER_BOUND_INTENT_REQUIRED")
        try: op=intent.operation.lower()
        except Exception: return BridgeResult("REJECTED",intent.intent_id,rejection="OPERATION_NORMALIZATION_INVALID")
        try: auth_digest=self._authorization_digest(intent)
        except Exception: return BridgeResult("REJECTED",intent.intent_id,rejection="AUTHORIZATION_DIGEST_INVALID")
        try: authorized=AuthorizedActionIntent(intent_id=intent.intent_id,lease_id=lease.payload_digest,action=op,device_id=intent.device_id,operation=op,target_state=target,expected_pre_state=expected_pre_state,authorization_digest=auth_digest,deadline_at=intent.expires_at,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest,controller_resource_id=controller_evidence.resource_id if controller_evidence is not None else (controller_result.resource_id if controller_result is not None else (controller_grant.resource_id if controller_grant is not None else "")),controller_id=controller_evidence.controller_id if controller_evidence is not None else (controller_result.controller_id if controller_result is not None else (controller_grant.controller_id if controller_grant is not None else "")),controller_fencing_token=controller_evidence.fencing_token if controller_evidence is not None else (controller_result.fencing_token if controller_result is not None else (controller_grant.fencing_token if controller_grant is not None else 0)))
        except Exception: return BridgeResult("REJECTED",intent.intent_id,rejection="AUTHORIZED_INTENT_INVALID")
        prior_state=None
        prior_state_eligible=op in ("set_eq_bands","set_eq_preset","set_captions_enabled") or (op=="set_volume" and set(dict(intent.parameters))=={"volume_percent"})
        if prior_state_eligible and type(snapshot.evidence_digest) is str and snapshot.evidence_digest.strip():
            try:
                prior_state=MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)
            except Exception:
                return BridgeResult("REJECTED",intent.intent_id,rejection="PRIOR_STATE_CAPTURE_INVALID",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        try:
            if commit_gate is None:
                controller_authority=None
                controller_lease=None
                if controller_evidence is not None:
                    controller_authority=getattr(self.firewall,"active_controller_authority",None)
                    if controller_authority is not None:
                        controller_lease=ActiveControllerLease(resource_id=controller_evidence.resource_id,controller_id=controller_evidence.controller_id,fencing_token=controller_evidence.fencing_token,issued_at=controller_evidence.issued_at,expires_at=controller_evidence.expires_at)
                elif controller_result is not None and self.controller_authority_gate is not None:
                    controller_authority=self.controller_authority_gate.lease_authority
                    controller_lease=ActiveControllerLease(resource_id=controller_result.resource_id,controller_id=controller_result.controller_id,fencing_token=controller_result.fencing_token,issued_at=controller_result.issued_at,expires_at=controller_result.expires_at)
                elif controller_grant is not None and self.controller_authority_gate is not None:
                    controller_authority=self.controller_authority_gate.lease_authority
                    controller_lease=ActiveControllerLease(resource_id=controller_grant.resource_id,controller_id=controller_grant.controller_id,fencing_token=controller_grant.fencing_token,issued_at=controller_grant.issued_at,expires_at=controller_grant.expires_at)
                if controller_authority is not None and controller_lease is not None:
                    gate=PhysicalCommitGate(controller_authority=controller_authority,controller_lease=controller_lease,controller_now=now,transport_timeout_seconds=self.transport_timeout_seconds)
                else:
                    gate=PhysicalCommitGate()
                    gate.transport_timeout_seconds=self.transport_timeout_seconds
            else:
                gate=commit_gate
            if not gate: raise TypeError("commit gate must be truthy")
            commit=getattr(gate,"commit")
            if not callable(commit): raise TypeError("commit gate must expose callable commit")
        except Exception: return BridgeResult("REJECTED",intent.intent_id,rejection="COMMIT_GATE_INVALID")
        protection_rejection=self._protection_rejection(intent,admission)
        if protection_rejection is not None: return protection_rejection
        try: result=await commit(authorized,physical_lease,snapshot,self._protected_transport(admission[0] if admission else None))
        except ProtectionUnavailableError as exc:
            return BridgeResult("REJECTED",intent.intent_id,rejection="PROTECTION_"+exc.status.state.value)
        except _ProtectionAdmissionInvalidated:
            return BridgeResult("REJECTED",intent.intent_id,rejection="PROTECTION_ADMISSION_INVALIDATED")
        except PhysicalTransportTimeout:
            self._record_indeterminate(intent,target,expected_pre_state,auth_digest,lease.payload_digest,snapshot.epoch)
            return BridgeResult("FAILED",intent.intent_id,rejection="UNKNOWN_PHYSICAL_STATE",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        except Exception: return BridgeResult("FAILED",intent.intent_id,rejection="COMMIT_EXECUTION_FAILED",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        try: precondition_result=isinstance(result,PreconditionResult)
        except Exception: return BridgeResult("FAILED",intent.intent_id,receipt=result,rejection="COMMIT_RESULT_INVALID",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        if precondition_result:
            return BridgeResult("REJECTED",intent.intent_id,rejection=result,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        receipt=result
        try:
            receipt_intent_id=getattr(receipt,"intent_id",intent.intent_id)
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_INTENT_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        try:
            receipt_intent_mismatch=receipt_intent_id!=intent.intent_id
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_INTENT_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        if receipt_intent_mismatch: return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_INTENT_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        try:
            receipt_device_id=getattr(receipt,"device_id",device_id)
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_DEVICE_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        try:
            receipt_device_mismatch=receipt_device_id!=device_id
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_DEVICE_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        if receipt_device_mismatch: return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_DEVICE_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        try:
            receipt_transaction_id=getattr(receipt,"transaction_id","")
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_TRANSACTION_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        if receipt_transaction_id!=intent.transaction_id: return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_TRANSACTION_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        try:
            receipt_capability_digest=getattr(receipt,"capability_digest","")
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_CAPABILITY_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        if receipt_capability_digest!=lease.payload_digest: return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_CAPABILITY_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        try:
            rs=getattr(receipt,"status",None)
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        verification=None
        verified_state=None
        if rs is ActuationStatus.REJECTED:
            return BridgeResult("REJECTED",intent.intent_id,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest,verification=None)
        try:
            executed_status=rs in (ActuationStatus.EXECUTED,ActuationStatus.COMMITTED)
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        if executed_status and (post_state_observer is None or post_state_observer is _POST_STATE_OBSERVER_UNSET):
            try:
                status={ActuationStatus.EXECUTED:"EXECUTED",ActuationStatus.COMMITTED:"EXECUTED"}.get(rs,"FAILED")
            except Exception:
                return BridgeResult("FAILED",intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
            return BridgeResult(status,intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest,verification=None)
        if executed_status:
            try:
                observed_snapshot=await post_state_observer(device_id)
                if not isinstance(observed_snapshot,PhysicalSnapshot) or observed_snapshot.device_id!=device_id:
                    raise ValueError("invalid post-state observation")
                if not math.isfinite(observed_snapshot.observed_at):
                    raise ValueError("invalid post-state observation timestamp")
                observation_now=time.time()
                if physical_lease.max_clock_skew_ms > 0 and (observed_snapshot.observed_at - observation_now) * 1000.0 > physical_lease.max_clock_skew_ms:
                    raise ValueError("future post-state observation")
                if physical_lease.max_world_state_age_ms > 0 and (observation_now - observed_snapshot.observed_at) * 1000.0 > physical_lease.max_world_state_age_ms:
                    raise ValueError("stale post-state observation")
                if observed_snapshot.epoch <= snapshot.epoch:
                    raise ValueError("stale post-state observation epoch")
                observed_state=observed_snapshot.state
                if observed_state is None or observed_state.state_digest!=target.state_digest:
                    return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="POST_STATE_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
                observed_snapshot_evidence_digest=getattr(observed_snapshot,"evidence_digest","")
                if media_operation:
                    post_state_evidence_mismatch=type(observed_snapshot_evidence_digest) is not str or not observed_snapshot_evidence_digest.strip() or observed_snapshot_evidence_digest!=observed_state_evidence_digest
                else:
                    post_state_evidence_mismatch=observed_snapshot_evidence_digest not in ("",None) and (type(observed_snapshot_evidence_digest) is not str or not observed_snapshot_evidence_digest.strip() or observed_snapshot_evidence_digest!=observed_state_evidence_digest)
                if post_state_evidence_mismatch:
                    return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="POST_STATE_EVIDENCE_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
            except Exception:
                return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="POST_STATE_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
            try:
                receipt_id=getattr(receipt,"receipt_id","")
                if not isinstance(receipt_id,str) or not receipt_id.strip():
                    return BridgeResult("FAILED",intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
            except Exception:
                return BridgeResult("FAILED",intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
            try:
                verification=PhysicalVerificationRecord(intent_id=intent.intent_id,device_id=device_id,receipt_id=receipt_id,expected_state_digest=target.state_digest,observed_state_digest=observed_state.state_digest,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest,world_state_evidence_digest=world_state_evidence_digest or "",observed_state_evidence_digest=observed_state_evidence_digest or "",world_state_epoch=snapshot.epoch,observed_state_epoch=observed_snapshot.epoch,verification_status=VerificationStatus.VERIFIED)
                verified_media_control_operation=op in ("set_eq_bands","set_eq_preset","set_captions_enabled") or (op=="set_volume" and set(dict(intent.parameters))=={"volume_percent"})
                if verified_media_control_operation and type(observed_snapshot_evidence_digest) is str and observed_snapshot_evidence_digest.strip() and observed_snapshot_evidence_digest==observed_state_evidence_digest:
                    verified_state=VerifiedMediaControlState.from_physical_verification(observed_snapshot,verification)
            except Exception:
                return BridgeResult("FAILED",intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        undo_candidate=None
        if verified_state is not None and prior_state is not None:
            try:
                undo_candidate=MediaControlUndoCandidate.from_verified_change(prior_state,verified_state)
            except ValueError:
                undo_candidate=None
        try:
            status={ActuationStatus.EXECUTED:"EXECUTED",ActuationStatus.COMMITTED:"EXECUTED",ActuationStatus.DUPLICATE_ABSORBED:"DUPLICATE_ABSORBED",ActuationStatus.REJECTED:"REJECTED",ActuationStatus.FAILED:"FAILED"}.get(rs,"FAILED")
        except Exception:
            return BridgeResult("FAILED",intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        return BridgeResult(status,intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest,verification=verification,verified_state=verified_state,prior_state=prior_state if verified_state is not None else None,undo_candidate=undo_candidate)

    async def authorize_and_execute(self,intent: SignedActionIntent,lease: SignedCapabilityLease,pre_state: DeviceState) -> BridgeResult:
        """DEPRECATED LEGACY compatibility path; production physical actuation must use authorize_and_commit()."""
        if intent is None or lease is None or pre_state is None: raise PhysicalCommitRejected("Missing bridge input")
        try:
            legacy_media_operation=str(intent.operation).upper()=="SET_PLAYBACK_POSITION"
        except Exception:
            legacy_media_operation=False
        if legacy_media_operation:
            return BridgeResult("REJECTED",intent.intent_id,rejection="PHYSICAL_COMMIT_REQUIRED")
        admission=[]
        protection_rejection=self._protection_rejection(intent,admission)
        if protection_rejection is not None: return protection_rejection
        lease_error=self._validate_lease(lease)
        if lease_error: return BridgeResult("REJECTED",intent.intent_id,rejection=lease_error)
        if intent.issuer_id!=lease.issuer_id: return BridgeResult("REJECTED",intent.intent_id,rejection="ISSUER_MISMATCH")
        validation=self.firewall.validate_intent(intent,lease)
        if isinstance(validation,AuthRejectionCode): return BridgeResult("REJECTED",intent.intent_id,rejection=validation)
        now=time.time()
        if intent.expires_at<=now: return BridgeResult("REJECTED",intent.intent_id,rejection="INTENT_EXPIRED")
        if lease.expires_at<=now: return BridgeResult("REJECTED",intent.intent_id,rejection="LEASE_EXPIRED")
        try:
            identity=getattr(getattr(self.adapter,"device",None),"identity",None)
            device_id=getattr(identity,"device_id",None)
        except Exception:
            return BridgeResult("REJECTED",intent.intent_id,rejection=PreconditionResult.DEVICE_MISMATCH)
        if intent.device_id!=device_id: return BridgeResult("REJECTED",intent.intent_id,rejection=PreconditionResult.DEVICE_MISMATCH)
        try: target=self._translate_state(intent,pre_state)
        except PhysicalCommitRejected as exc: return BridgeResult("REJECTED",intent.intent_id,rejection=str(exc))
        auth_digest=self._authorization_digest(intent)
        authorized=AuthorizedActionIntent(intent_id=intent.intent_id,lease_id=lease.payload_digest,action=intent.operation,device_id=intent.device_id,operation=intent.operation,target_state=target,expected_pre_state=pre_state,authorization_digest=auth_digest,deadline_at=intent.expires_at,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        protection_rejection=self._protection_rejection(intent,admission)
        if protection_rejection is not None: return protection_rejection
        try:
            receipt=await dispatch_physical_transport(
                transport=self._protected_transport(admission[0] if admission else None),
                intent=authorized,
                transaction_digest=intent.transaction_id,
                capability_digest=lease.payload_digest,
                timeout_seconds=self.transport_timeout_seconds,
            )
        except ProtectionUnavailableError as exc:
            return BridgeResult("REJECTED",intent.intent_id,rejection="PROTECTION_"+exc.status.state.value)
        except _ProtectionAdmissionInvalidated:
            return BridgeResult("REJECTED",intent.intent_id,rejection="PROTECTION_ADMISSION_INVALIDATED")
        except PhysicalTransportTimeout:
            self._record_indeterminate(intent,target,pre_state,auth_digest,lease.payload_digest)
            return BridgeResult("FAILED",intent.intent_id,rejection="UNKNOWN_PHYSICAL_STATE",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        except Exception as exc:
            return BridgeResult("FAILED",intent.intent_id,rejection=type(exc).__name__+": "+str(exc),authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        if getattr(receipt,"intent_id",intent.intent_id)!=intent.intent_id: return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_INTENT_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        if getattr(receipt,"device_id",device_id)!=device_id: return BridgeResult("FAILED",intent.intent_id,receipt=receipt,rejection="RECEIPT_DEVICE_MISMATCH",authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)
        rs=getattr(receipt,"status",None)
        if rs==ActuationStatus.EXECUTED: status="EXECUTED"
        elif rs==ActuationStatus.COMMITTED: status="COMMITTED"
        elif rs==ActuationStatus.DUPLICATE_ABSORBED: status="DUPLICATE_ABSORBED"
        elif rs==ActuationStatus.REJECTED: status="REJECTED"
        elif rs==ActuationStatus.FAILED: status="FAILED"
        else: status="FAILED"
        return BridgeResult(status,intent.intent_id,receipt=receipt,authorization_digest=auth_digest,transaction_id=intent.transaction_id,capability_digest=lease.payload_digest)


def build_protected_device_fabric_bridge(firewall: IntentFirewall, adapter: PhysicalTransport, protection_supervisor: ProtectionSupervisor, *, transport_timeout_seconds: float = 2.0, recovery_store: Optional[PhysicalRecoveryStore] = None) -> Gen3DeviceFabricBridge:
    if not isinstance(protection_supervisor,ProtectionSupervisor):
        raise ValueError("ProtectionSupervisor is required")
    return Gen3DeviceFabricBridge(firewall,adapter,transport_timeout_seconds=transport_timeout_seconds,recovery_store=recovery_store,protection_supervisor=protection_supervisor)


def build_fenced_protected_device_fabric_bridge(firewall: IntentFirewall, adapter: PhysicalTransport, protection_supervisor: ProtectionSupervisor, *, fence_store, transaction_finality_store=None, transport_timeout_seconds: float = 2.0, recovery_store: Optional[PhysicalRecoveryStore] = None) -> Gen3DeviceFabricBridge:
    if not isinstance(protection_supervisor,ProtectionSupervisor):
        raise ValueError("ProtectionSupervisor is required")
    fenced_adapter=FencedPhysicalTransport(adapter,fence_store,transaction_finality_store=transaction_finality_store)
    return Gen3DeviceFabricBridge(firewall,fenced_adapter,transport_timeout_seconds=transport_timeout_seconds,recovery_store=recovery_store,protection_supervisor=protection_supervisor)


def build_production_fenced_protected_device_fabric_bridge(firewall: IntentFirewall, adapter: PhysicalTransport, protection_supervisor: ProtectionSupervisor, *, fence_store, transaction_finality_store=None, transport_timeout_seconds: float = 2.0, recovery_store: Optional[PhysicalRecoveryStore] = None) -> Gen3DeviceFabricBridge:
    require_production_monotonic_anchor(getattr(fence_store,"monotonic_anchor",None))
    if transaction_finality_store is None or not callable(getattr(transaction_finality_store,"permits_execution",None)):
        raise ValueError("endpoint transaction finality store is required")
    if not callable(getattr(transaction_finality_store,"claim_execution",None)):
        raise ValueError("endpoint transaction finality store atomic execution claim is required")
    from ..device_fabric.endpoint_transaction_finality_store import EndpointTransactionFinalityStore
    if type(transaction_finality_store) is not EndpointTransactionFinalityStore or transaction_finality_store._trusted_authority is None:
        raise ValueError("endpoint transaction finality store trusted authority is required")
    if transaction_finality_store._require_existing is not True:
        raise ValueError("production endpoint finality existing history is required")
    if transaction_finality_store._minimum_profile_version!=2:
        raise ValueError("production endpoint finality profile v2 is required")
    raise ValueError("production endpoint execution boundary is required")
    return build_fenced_protected_device_fabric_bridge(firewall,adapter,protection_supervisor,fence_store=fence_store,transaction_finality_store=transaction_finality_store,transport_timeout_seconds=transport_timeout_seconds,recovery_store=recovery_store)
