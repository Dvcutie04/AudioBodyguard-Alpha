import hashlib
import json
import math
import time
from copy import deepcopy
from inspect import iscoroutinefunction

from .contracts import AuthorizedActionIntent,DeviceState
from .endpoint_execution_ledger import EndpointExecutionLedger,_identifier,_positive_integer
from .endpoint_action_admission import EndpointActionVerifier
from .transport import PhysicalTransport


# Reference guard; production also requires endpoint authorization and rollback protection.
class EndpointLedgerGuardedTransport:
    def __init__(self,transport,ledger,*,authority_epoch,endpoint_action_verifier=None):
        if type(ledger) is not EndpointExecutionLedger:
            raise ValueError("endpoint execution ledger is required")
        if transport is None or not isinstance(transport,PhysicalTransport) or not iscoroutinefunction(transport.execute_intent):
            raise ValueError("asynchronous endpoint transport is required")
        try:
            device_id=transport.device.identity.device_id
        except Exception:
            raise ValueError("endpoint transport device identity is invalid") from None
        if type(device_id) is not str or device_id!=ledger._device_id:
            raise ValueError("endpoint transport device identity mismatch")
        self._transport=transport
        self._ledger=ledger
        self._authority_epoch=_positive_integer(authority_epoch,"authority_epoch")
        if endpoint_action_verifier is not None and type(endpoint_action_verifier) is not EndpointActionVerifier:
            raise ValueError("endpoint action verifier is invalid")
        self._endpoint_action_verifier=endpoint_action_verifier

    @property
    def device(self):
        return self._transport.device

    def _bound_request(self,intent):
        if type(intent) is not AuthorizedActionIntent:
            raise ValueError("authorized endpoint intent is required")
        request=deepcopy(intent)
        if _identifier(request.device_id,"device_id")!=self._ledger._device_id or self.device.identity.device_id!=self._ledger._device_id:
            raise ValueError("endpoint transport device identity mismatch")
        if type(request.target_state) is not DeviceState or type(request.expected_pre_state) is not DeviceState:
            raise ValueError("endpoint request physical state is invalid")
        if type(request.deadline_at) not in (int,float) or not math.isfinite(request.deadline_at):
            raise ValueError("endpoint request deadline is invalid")
        fields=(_identifier(request.transaction_id,"transaction_id"),_identifier(request.intent_id,"intent_id"),_identifier(request.action,"action"),_identifier(request.operation,"operation"),_identifier(request.controller_resource_id,"controller_resource_id"),_identifier(request.controller_id,"controller_id"),_positive_integer(request.controller_fencing_token,"controller_fencing_token"),_identifier(request.capability_digest,"capability_digest"),_identifier(request.authorization_digest,"authorization_digest"),request.lease_id,request.target_state.state_digest,request.expected_pre_state.state_digest,request.deadline_at)
        encoded=json.dumps(["AQSS/endpoint-execution-request/v1",request.device_id,*fields],ensure_ascii=True,separators=(",",":"),allow_nan=False).encode("utf-8")
        context=dict(intent_id=request.intent_id,request_digest=hashlib.sha256(encoded).hexdigest(),capability_digest=request.capability_digest,authorization_digest=request.authorization_digest,controller_id=request.controller_id,controller_fencing_token=request.controller_fencing_token,authority_epoch=self._authority_epoch)
        return request,context

    def close_if_unstarted(self,intent):
        request,context=self._bound_request(intent)
        return self._ledger.close_if_unstarted(request.transaction_id,**context)

    async def execute_intent(self,intent,transaction_digest=None,capability_digest=None,*,signed_intent=None,capability_lease=None,controller_evidence=None):
        evidence=(signed_intent,capability_lease,controller_evidence)
        if self._endpoint_action_verifier is not None:
            if any(item is None for item in evidence):
                raise ValueError("endpoint action signed evidence is required")
            intent=self._endpoint_action_verifier.admit(signed_intent=signed_intent,capability_lease=capability_lease,controller_evidence=controller_evidence,authorized_intent=intent,now=time.time())
        elif any(item is not None for item in evidence):
            raise ValueError("endpoint action verifier is required")
        request,context=self._bound_request(intent)
        if transaction_digest is not None and transaction_digest!=request.transaction_id:
            raise ValueError("endpoint transaction digest mismatch")
        if capability_digest is not None and capability_digest!=request.capability_digest:
            raise ValueError("endpoint capability digest mismatch")
        if request.deadline_at<=time.time():
            raise ValueError("endpoint request deadline expired")
        if self._ledger.claim_execution(request.transaction_id,**context) is not True:
            raise ValueError("endpoint execution is closed or already claimed")
        return await self._transport.execute_intent(intent=request,transaction_digest=request.transaction_id,capability_digest=request.capability_digest)
