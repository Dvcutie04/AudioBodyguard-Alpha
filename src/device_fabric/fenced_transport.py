from inspect import iscoroutinefunction
from typing import Optional

from .contracts import ActuationReceipt,ActuationStatus,AuthorizedActionIntent
from .endpoint_handoff_barrier import EndpointHandoffBarrier
from .transport import PhysicalTransport


class FencedPhysicalTransport:
    def __init__(self,transport:PhysicalTransport,fence_store,transaction_finality_store=None,*,handoff_barrier=None):
        if transport is None or not isinstance(transport,PhysicalTransport) or not iscoroutinefunction(transport.execute_intent):
            raise ValueError("asynchronous PhysicalTransport is required")
        if fence_store is None or not callable(getattr(fence_store,"accept",None)):
            raise ValueError("controller fence store is required")
        if transaction_finality_store is not None and not callable(getattr(transaction_finality_store,"permits_execution",None)):
            raise ValueError("endpoint transaction finality store is invalid")
        if handoff_barrier is not None:
            if type(handoff_barrier) is not EndpointHandoffBarrier or handoff_barrier._fence_store is not fence_store:
                raise ValueError("endpoint handoff barrier fence mismatch")
            try:
                device_id=transport.device.identity.device_id
            except Exception:
                raise ValueError("endpoint handoff barrier device mismatch") from None
            if type(device_id) is not str or device_id!=handoff_barrier._device_id:
                raise ValueError("endpoint handoff barrier device mismatch")
        self._transport=transport
        self._fence_store=fence_store
        self._transaction_finality_store=transaction_finality_store
        self._handoff_barrier=handoff_barrier

    @property
    def device(self):
        return self._transport.device

    def _rejected_receipt(self,intent,transaction_digest,capability_digest):
        return ActuationReceipt(receipt_id=f"rcpt_{intent.intent_id}",intent_id=intent.intent_id,status=ActuationStatus.REJECTED,device_id=self.device.identity.device_id,transaction_id=transaction_digest or intent.transaction_id,capability_digest=capability_digest or intent.capability_digest)

    async def execute_intent(self,intent:AuthorizedActionIntent,transaction_digest:Optional[str]=None,capability_digest:Optional[str]=None,*,_final_admission_check=None)->ActuationReceipt:
        try:
            adapter_device_id=self.device.identity.device_id
            intent_device_id=intent.device_id
            device_matches=type(adapter_device_id) is str and bool(adapter_device_id.strip()) and type(intent_device_id) is str and bool(intent_device_id.strip()) and intent_device_id==adapter_device_id
        except Exception:
            device_matches=False
        if not device_matches:
            return self._rejected_receipt(intent,transaction_digest,capability_digest)
        if self._transaction_finality_store is not None:
            try:
                permitted=self._transaction_finality_store.permits_execution(intent.transaction_id,device_id=adapter_device_id) is True
            except Exception:
                permitted=False
            if not permitted:
                return self._rejected_receipt(intent,transaction_digest,capability_digest)
        resource_id=getattr(intent,"controller_resource_id","")
        controller_id=getattr(intent,"controller_id","")
        token=getattr(intent,"controller_fencing_token",0)
        valid=type(resource_id) is str and bool(resource_id.strip()) and type(controller_id) is str and bool(controller_id.strip()) and type(token) is int and token>0
        accepted=False
        if valid:
            try:
                accepted=self._fence_store.accept(resource_id,controller_id,token) is True
            except Exception:
                accepted=False
        if not accepted:
            return self._rejected_receipt(intent,transaction_digest,capability_digest)
        if self._transaction_finality_store is not None:
            try:
                claimed=self._transaction_finality_store.claim_execution(intent.transaction_id,device_id=adapter_device_id) is True
            except Exception:
                claimed=False
            if not claimed:
                return self._rejected_receipt(intent,transaction_digest,capability_digest)
            try:
                current=self._fence_store.accept(resource_id,controller_id,token) is True
            except Exception:
                current=False
            if not current:
                return self._rejected_receipt(intent,transaction_digest,capability_digest)
        if _final_admission_check is not None:
            _final_admission_check()
        if self._handoff_barrier is not None:
            try:
                admitted=self._handoff_barrier.admit(transaction_id=intent.transaction_id,resource_id=resource_id,controller_id=controller_id,fencing_token=token) is True
            except Exception:
                admitted=False
            if not admitted:
                return self._rejected_receipt(intent,transaction_digest,capability_digest)
            if _final_admission_check is not None:
                _final_admission_check()
        return await self._transport.execute_intent(intent=intent,transaction_digest=transaction_digest,capability_digest=capability_digest)
