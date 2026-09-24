import threading
from dataclasses import dataclass
from enum import Enum,auto
from typing import Optional,Protocol,runtime_checkable


class MonotonicAnchorDecision(Enum):
    ADVANCED=auto()
    ALREADY_CURRENT=auto()
    STALE=auto()
    CONTROLLER_MISMATCH=auto()
    MALFORMED=auto()


class MonotonicAnchorSecurityLevel(Enum):
    TEST_ONLY="TEST_ONLY"
    HARDWARE_BACKED="HARDWARE_BACKED"
    REMOTE_ATOMIC="REMOTE_ATOMIC"


@dataclass(frozen=True)
class MonotonicFenceValue:
    resource_id:str
    controller_id:str
    fencing_token:int

    def __post_init__(self):
        if type(self.resource_id) is not str or not self.resource_id.strip():
            raise ValueError("resource_id must be a non-empty string")
        if type(self.controller_id) is not str or not self.controller_id.strip():
            raise ValueError("controller_id must be a non-empty string")
        if type(self.fencing_token) is not int or self.fencing_token<=0:
            raise ValueError("fencing_token must be a positive integer")


@runtime_checkable
class MonotonicFenceAnchor(Protocol):
    def read(self,resource_id:str)->Optional[MonotonicFenceValue]:
        ...

    def snapshot(self)->dict[str,MonotonicFenceValue]:
        ...

    def advance(self,resource_id:str,controller_id:str,fencing_token:int)->MonotonicAnchorDecision:
        ...


_PRODUCTION_SECURITY_LEVELS=frozenset((MonotonicAnchorSecurityLevel.HARDWARE_BACKED,MonotonicAnchorSecurityLevel.REMOTE_ATOMIC))


def require_production_monotonic_anchor(anchor):
    provider_id=getattr(anchor,"provider_id",None)
    security_level=getattr(anchor,"security_level",None)
    if not isinstance(anchor,ExternalAtomicMonotonicFenceAnchor) or not isinstance(anchor,MonotonicFenceAnchor) or type(provider_id) is not str or not provider_id.strip() or security_level not in _PRODUCTION_SECURITY_LEVELS:
        raise ValueError("production monotonic anchor required")
    return anchor


class ExternalAtomicMonotonicFenceAnchor:
    def __init__(self,backend,*,security_level):
        provider_id=getattr(backend,"provider_id",None)
        if type(provider_id) is not str or not provider_id.strip():
            raise ValueError("external monotonic backend provider_id required")
        if security_level not in _PRODUCTION_SECURITY_LEVELS:
            raise ValueError("production monotonic anchor security level required")
        if not callable(getattr(backend,"snapshot",None)) or not callable(getattr(backend,"advance",None)):
            raise ValueError("external atomic monotonic backend required")
        self._backend=backend
        self.provider_id=provider_id
        self.security_level=security_level
        self._lock=threading.RLock()

    def snapshot(self)->dict[str,MonotonicFenceValue]:
        with self._lock:
            values=self._backend.snapshot()
        if type(values) is not dict:
            raise ValueError("external monotonic anchor manifest invalid")
        result={}
        for resource_id,value in values.items():
            if type(resource_id) is not str or not resource_id.strip() or not isinstance(value,MonotonicFenceValue) or value.resource_id!=resource_id:
                raise ValueError("external monotonic anchor manifest invalid")
            result[resource_id]=value
        return result

    def read(self,resource_id:str)->Optional[MonotonicFenceValue]:
        if type(resource_id) is not str or not resource_id.strip():
            raise ValueError("resource_id must be a non-empty string")
        return self.snapshot().get(resource_id)

    def advance(self,resource_id:str,controller_id:str,fencing_token:int)->MonotonicAnchorDecision:
        if type(resource_id) is not str or not resource_id.strip() or type(controller_id) is not str or not controller_id.strip() or type(fencing_token) is not int or fencing_token<=0:
            return MonotonicAnchorDecision.MALFORMED
        with self._lock:
            decision=self._backend.advance(resource_id,controller_id,fencing_token)
        if not isinstance(decision,MonotonicAnchorDecision):
            raise ValueError("external monotonic anchor decision invalid")
        return decision


class InMemoryMonotonicFenceAnchor:
    provider_id="in-memory-test"
    security_level=MonotonicAnchorSecurityLevel.TEST_ONLY

    def __init__(self):
        self._values={}
        self._lock=threading.RLock()

    def read(self,resource_id:str)->Optional[MonotonicFenceValue]:
        if type(resource_id) is not str or not resource_id.strip():
            raise ValueError("resource_id must be a non-empty string")
        with self._lock:
            return self._values.get(resource_id)

    def snapshot(self)->dict[str,MonotonicFenceValue]:
        with self._lock:
            return dict(self._values)

    def advance(self,resource_id:str,controller_id:str,fencing_token:int)->MonotonicAnchorDecision:
        if type(resource_id) is not str or not resource_id.strip() or type(controller_id) is not str or not controller_id.strip() or type(fencing_token) is not int or fencing_token<=0:
            return MonotonicAnchorDecision.MALFORMED
        proposed=MonotonicFenceValue(resource_id=resource_id,controller_id=controller_id,fencing_token=fencing_token)
        with self._lock:
            current=self._values.get(resource_id)
            if current is None or fencing_token>current.fencing_token:
                self._values[resource_id]=proposed
                return MonotonicAnchorDecision.ADVANCED
            if fencing_token<current.fencing_token:
                return MonotonicAnchorDecision.STALE
            if controller_id!=current.controller_id:
                return MonotonicAnchorDecision.CONTROLLER_MISMATCH
            return MonotonicAnchorDecision.ALREADY_CURRENT
