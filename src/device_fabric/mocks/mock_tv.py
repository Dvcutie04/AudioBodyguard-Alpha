import threading
from typing import Any, Dict, Optional, Set
from src.device_fabric.contracts import ActuationReceipt, ActuationStatus, AuthorizedActionIntent, DeviceCapabilities, DeviceIdentity, DeviceState, DeviceType

class MockTV:
    def __init__(self, device_id: str = "tv_integration_node_1", name: str = "Living Room TV"):
        self.identity = DeviceIdentity(device_id=device_id, device_type=DeviceType.TV, name=name, vendor="MockCorp")
        self.capabilities = DeviceCapabilities(device_id=device_id, capabilities={"set_power", "set_volume", "set_muted", "set_input_source", "set_playback_position"})
        self.state = DeviceState(power=False, volume=10.0, muted=False, input_source="HDMI_1")

class MockTVAdapter:
    def __init__(self, device_id_or_tv: Any = "tv_integration_node_1", *, fence_store=None):
        if isinstance(device_id_or_tv, MockTV):
            self.device = device_id_or_tv
        else:
            self.device = MockTV(device_id=str(device_id_or_tv))
        self._executed_intents: Set[str] = set()
        self._fence_store = fence_store
        self._highest_controller_fences: Dict[str, tuple[int, str]] = {} if fence_store is None else fence_store.snapshot()
        self._fence_lock = threading.RLock()

    async def execute_intent(self, intent: AuthorizedActionIntent, transaction_digest: Optional[str] = None, capability_digest: Optional[str] = None) -> ActuationReceipt:
        with self._fence_lock:
            resource_id=getattr(intent,"controller_resource_id","")
            controller_id=getattr(intent,"controller_id","")
            token=getattr(intent,"controller_fencing_token",0)
            controller_bound=bool(resource_id or controller_id or token)
            if controller_bound:
                valid=type(resource_id) is str and bool(resource_id.strip()) and type(controller_id) is str and bool(controller_id.strip()) and type(token) is int and token>0
                current=self._highest_controller_fences.get(resource_id) if valid else None
                stale=not valid or (current is not None and (token<current[0] or (token==current[0] and controller_id!=current[1])))
                if not stale and self._fence_store is not None:
                    try:
                        stale=self._fence_store.accept(resource_id,controller_id,token) is not True
                    except Exception:
                        stale=True
                if stale:
                    return ActuationReceipt(receipt_id=f"rcpt_{intent.intent_id}",intent_id=intent.intent_id,status=ActuationStatus.REJECTED,device_id=self.device.identity.device_id,transaction_id=transaction_digest or intent.transaction_id,capability_digest=capability_digest or intent.capability_digest)
                if current is None or token>current[0]:
                    self._highest_controller_fences[resource_id]=(token,controller_id)
            if intent.intent_id in self._executed_intents:
                return ActuationReceipt(receipt_id=f"rcpt_{intent.intent_id}", intent_id=intent.intent_id, status=ActuationStatus.DUPLICATE_ABSORBED, device_id=self.device.identity.device_id, transaction_id=transaction_digest or intent.transaction_id, capability_digest=capability_digest or intent.capability_digest)
            self._executed_intents.add(intent.intent_id)
            if intent.target_state:
                self.device.state = intent.target_state
            return ActuationReceipt(receipt_id=f"rcpt_{intent.intent_id}", intent_id=intent.intent_id, status=ActuationStatus.EXECUTED, device_id=self.device.identity.device_id, transaction_id=transaction_digest or intent.transaction_id, capability_digest=capability_digest or intent.capability_digest)
