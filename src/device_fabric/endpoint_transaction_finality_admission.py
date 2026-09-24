from dataclasses import dataclass

from .endpoint_transaction_finality_authority import AuthorityVerifiedEndpointFinalityEnvelope, verify_endpoint_finality_with_authority
from .endpoint_transaction_finality_commitment import compute_endpoint_finality_proof_digest
from .endpoint_transaction_finality_protocol import EndpointFinalityAcceptedResult, validate_endpoint_finality_binding, validate_endpoint_finality_freshness, validate_endpoint_finality_chain, transition_endpoint_transaction_state_from_finality_assertion


@dataclass(frozen=True, slots=True)
class EndpointFinalityAdmissionResult:
    verified: AuthorityVerifiedEndpointFinalityEnvelope
    accepted_result: EndpointFinalityAcceptedResult
    proof_digest: str


def admit_endpoint_finality_assertion(*, wire, trust, device_id, transaction_id, intent_id, capability_digest, authorization_digest, controller_id, controller_fencing_token, audience, issuer_id, authority_epoch, now, current_state, previous_proof_digest, request_digest=None):
    verified = verify_endpoint_finality_with_authority(wire=wire, trust=trust, issuer_id=issuer_id, audience=audience, device_id=device_id, authority_epoch=authority_epoch)
    claims = verified.claims
    validate_endpoint_finality_binding(claims, device_id=device_id, transaction_id=transaction_id, intent_id=intent_id, capability_digest=capability_digest, authorization_digest=authorization_digest, controller_id=controller_id, controller_fencing_token=controller_fencing_token, audience=audience, issuer_id=issuer_id, authority_epoch=authority_epoch, request_digest=request_digest)
    validate_endpoint_finality_freshness(claims, now=now)
    validate_endpoint_finality_chain(claims, previous_proof_digest=previous_proof_digest)
    result_state = transition_endpoint_transaction_state_from_finality_assertion(current_state, claims)
    accepted_result = EndpointFinalityAcceptedResult(claims=claims, prior_state=current_state, result_state=result_state, accepted_at=now)
    proof_digest = compute_endpoint_finality_proof_digest(claims=claims, kid=verified.kid, namespace=verified.namespace)
    return EndpointFinalityAdmissionResult(verified=verified, accepted_result=accepted_result, proof_digest=proof_digest)
