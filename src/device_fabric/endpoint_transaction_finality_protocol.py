from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Optional


class EndpointTransactionState(str,Enum):
    UNKNOWN="UNKNOWN"
    EXECUTION_CLAIMED="EXECUTION_CLAIMED"
    APPLIED="APPLIED"
    NOT_APPLIED="NOT_APPLIED"
    INDETERMINATE="INDETERMINATE"
    CONFLICT="CONFLICT"


_TERMINAL_STATES=frozenset({EndpointTransactionState.APPLIED,EndpointTransactionState.NOT_APPLIED,EndpointTransactionState.CONFLICT})
_ALLOWED_TRANSITIONS={
    EndpointTransactionState.UNKNOWN:frozenset({EndpointTransactionState.EXECUTION_CLAIMED,EndpointTransactionState.NOT_APPLIED}),
    EndpointTransactionState.EXECUTION_CLAIMED:frozenset({EndpointTransactionState.APPLIED,EndpointTransactionState.INDETERMINATE,EndpointTransactionState.CONFLICT}),
    EndpointTransactionState.INDETERMINATE:frozenset({EndpointTransactionState.APPLIED,EndpointTransactionState.NOT_APPLIED,EndpointTransactionState.CONFLICT}),
}


def transition_endpoint_transaction_state(current_state,next_state):
    if type(current_state) is not EndpointTransactionState or type(next_state) is not EndpointTransactionState:
        raise ValueError("endpoint transaction state is invalid")
    if current_state is next_state:
        return current_state
    if current_state in _TERMINAL_STATES:
        raise ValueError("terminal endpoint transaction state")
    if next_state not in _ALLOWED_TRANSITIONS.get(current_state,frozenset()):
        raise ValueError("endpoint transaction transition is invalid")
    return next_state


class EndpointFinalityDecision(str,Enum):
    NOT_APPLIED="NOT_APPLIED"


@dataclass(frozen=True,slots=True)
class EndpointFinalityAssertionClaims:
    profile_version:int
    proof_id:str
    issuer_id:str
    audience:str
    device_id:str
    transaction_id:str
    intent_id:str
    capability_digest:str
    authorization_digest:str
    controller_id:str
    controller_fencing_token:int
    decision:EndpointFinalityDecision
    reason_code:str
    authority_epoch:int
    issued_at:float
    not_before:float
    expires_at:float
    previous_proof_digest:Optional[str]
    request_digest:Optional[str]=None

    def __post_init__(self):
        if type(self.profile_version) is not int or self.profile_version not in (1,2):
            raise ValueError("profile_version is invalid")
        if type(self.controller_fencing_token) is not int or self.controller_fencing_token<=0:
            raise ValueError("controller_fencing_token is invalid")
        if type(self.authority_epoch) is not int or self.authority_epoch<=0:
            raise ValueError("authority_epoch is invalid")
        if type(self.decision) is not EndpointFinalityDecision:
            raise ValueError("decision is invalid")
        for field in ("issued_at","not_before","expires_at"):
            value=getattr(self,field)
            if type(value) not in (int,float) or not isfinite(value):
                raise ValueError(field+" is invalid")
        if not self.not_before<=self.issued_at<self.expires_at:
            raise ValueError("finality assertion time window is invalid")
        for field in ("proof_id","issuer_id","audience","device_id","transaction_id","intent_id","capability_digest","authorization_digest","controller_id","reason_code"):
            value=getattr(self,field)
            if type(value) is not str or not value.strip() or value!=value.strip():
                raise ValueError(field+" is invalid")
        if self.profile_version==1:
            if self.request_digest is not None:
                raise ValueError("request_digest is invalid for profile v1")
        elif type(self.request_digest) is not str or not self.request_digest.strip() or self.request_digest!=self.request_digest.strip():
            raise ValueError("request_digest is invalid")
        if self.previous_proof_digest is not None and (type(self.previous_proof_digest) is not str or not self.previous_proof_digest.strip() or self.previous_proof_digest!=self.previous_proof_digest.strip()):
            raise ValueError("previous_proof_digest is invalid")


def validate_endpoint_finality_binding(claims,*,device_id,transaction_id,intent_id,capability_digest,authorization_digest,controller_id,controller_fencing_token,audience,issuer_id,authority_epoch,request_digest=None):
    if type(claims) is not EndpointFinalityAssertionClaims:
        raise ValueError("finality assertion claims are invalid")
    bindings=(("device_id",device_id),("transaction_id",transaction_id),("intent_id",intent_id),("capability_digest",capability_digest),("authorization_digest",authorization_digest),("controller_id",controller_id),("controller_fencing_token",controller_fencing_token),("audience",audience),("issuer_id",issuer_id),("authority_epoch",authority_epoch))
    for field,expected in bindings:
        if getattr(claims,field)!=expected:
            raise ValueError("finality assertion "+field+" mismatch")
    if claims.profile_version==2:
        if type(request_digest) is not str or not request_digest.strip() or request_digest!=request_digest.strip():
            raise ValueError("finality assertion request_digest is required")
        if claims.request_digest!=request_digest:
            raise ValueError("finality assertion request_digest mismatch")
    elif request_digest is not None:
        raise ValueError("finality assertion request_digest is unsupported for profile v1")
    return claims


def validate_endpoint_finality_freshness(claims,*,now):
    if type(claims) is not EndpointFinalityAssertionClaims:
        raise ValueError("finality assertion claims are invalid")
    if type(now) not in (int,float) or not isfinite(now):
        raise ValueError("now is invalid")
    if now<claims.not_before:
        raise ValueError("finality assertion is not yet valid")
    if now>=claims.expires_at:
        raise ValueError("finality assertion is expired")
    return claims


def transition_endpoint_transaction_state_from_finality_assertion(current_state,claims):
    if type(claims) is not EndpointFinalityAssertionClaims:
        raise ValueError("finality assertion claims are invalid")
    if claims.decision is EndpointFinalityDecision.NOT_APPLIED:
        return transition_endpoint_transaction_state(current_state,EndpointTransactionState.NOT_APPLIED)
    raise ValueError("finality assertion decision is unsupported")


def validate_endpoint_finality_chain(claims,*,previous_proof_digest):
    if type(claims) is not EndpointFinalityAssertionClaims:
        raise ValueError("finality assertion claims are invalid")
    if previous_proof_digest is not None and (type(previous_proof_digest) is not str or not previous_proof_digest.strip() or previous_proof_digest!=previous_proof_digest.strip()):
        raise ValueError("previous_proof_digest is invalid")
    if claims.previous_proof_digest!=previous_proof_digest:
        raise ValueError("finality assertion previous_proof_digest mismatch")
    return claims


def endpoint_finality_proof_identity(claims):
    if type(claims) is not EndpointFinalityAssertionClaims:
        raise ValueError("finality assertion claims are invalid")
    return claims.issuer_id,claims.proof_id


class EndpointFinalityReplayClassification(str,Enum):
    UNSEEN="UNSEEN"
    IDENTICAL_REPLAY="IDENTICAL_REPLAY"
    ID_CONFLICT="ID_CONFLICT"


def _same_typed_finality_claim_values(left,right):
    for name in EndpointFinalityAssertionClaims.__slots__:
        left_value=getattr(left,name)
        right_value=getattr(right,name)
        if type(left_value) is not type(right_value) or left_value!=right_value:
            return False
        if type(left_value) is float and left_value.hex()!=right_value.hex():
            return False
    return True


def classify_endpoint_finality_replay(claims,*,accepted_claims):
    if type(claims) is not EndpointFinalityAssertionClaims:
        raise ValueError("finality assertion claims are invalid")
    if accepted_claims is None:
        return EndpointFinalityReplayClassification.UNSEEN
    if type(accepted_claims) is not EndpointFinalityAssertionClaims:
        raise ValueError("accepted finality assertion claims are invalid")
    if endpoint_finality_proof_identity(claims)!=endpoint_finality_proof_identity(accepted_claims):
        raise ValueError("accepted finality assertion identity mismatch")
    if _same_typed_finality_claim_values(claims,accepted_claims):
        return EndpointFinalityReplayClassification.IDENTICAL_REPLAY
    return EndpointFinalityReplayClassification.ID_CONFLICT


@dataclass(frozen=True,slots=True)
class EndpointFinalityAcceptedResult:
    claims:EndpointFinalityAssertionClaims
    prior_state:EndpointTransactionState
    result_state:EndpointTransactionState
    accepted_at:float

    def __post_init__(self):
        if type(self.claims) is not EndpointFinalityAssertionClaims:
            raise ValueError("accepted finality result claims are invalid")
        if type(self.prior_state) is not EndpointTransactionState:
            raise ValueError("accepted finality result prior_state is invalid")
        if type(self.result_state) is not EndpointTransactionState:
            raise ValueError("accepted finality result result_state is invalid")
        if type(self.accepted_at) not in (int,float) or not isfinite(self.accepted_at):
            raise ValueError("accepted finality result accepted_at is invalid")
        expected_result_state=transition_endpoint_transaction_state_from_finality_assertion(self.prior_state,self.claims)
        if self.result_state is not expected_result_state:
            raise ValueError("accepted finality result transition mismatch")


def endpoint_finality_replay_result(claims,*,accepted_result):
    if type(accepted_result) is not EndpointFinalityAcceptedResult:
        raise ValueError("accepted finality result is invalid")
    classification=classify_endpoint_finality_replay(claims,accepted_claims=accepted_result.claims)
    if classification is EndpointFinalityReplayClassification.IDENTICAL_REPLAY:
        return accepted_result
    if classification is EndpointFinalityReplayClassification.ID_CONFLICT:
        raise ValueError("accepted finality proof identity conflict")
    raise ValueError("finality replay result is unavailable")
