import json
import math
from dataclasses import dataclass

from src.control.remote_controller_protocol import P256AuthorityPublicVerifier
from .controller_fence_store import ControllerFenceStore


@dataclass(frozen=True)
class SignedEndpointFenceDirective:
    request_id: str
    device_id: str
    resource_id: str
    previous_controller_id: str
    previous_fencing_token: int
    controller_id: str
    fencing_token: int
    issued_at: float
    expires_at: float
    issuer_id: str
    algorithm: str = "ECDSA_P256_SHA256"
    signature: str = ""

    @property
    def canonical_bytes(self):
        fields={"purpose":"AQSS/endpoint-fence-install/v1","request_id":self.request_id,"device_id":self.device_id,"resource_id":self.resource_id,"previous_controller_id":self.previous_controller_id,"previous_fencing_token":self.previous_fencing_token,"controller_id":self.controller_id,"fencing_token":self.fencing_token,"issued_at":self.issued_at,"expires_at":self.expires_at,"issuer_id":self.issuer_id,"algorithm":self.algorithm}
        return json.dumps(fields,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


class VerifiedEndpointFenceInstaller:
    def __init__(self,*,device_id,fence_store,trusted_verifiers):
        if type(device_id) is not str or not device_id.strip():
            raise ValueError("endpoint device identity is required")
        if not isinstance(fence_store,ControllerFenceStore):
            raise ValueError("endpoint controller fence store is required")
        if type(trusted_verifiers) is not dict or not trusted_verifiers or any(type(key) is not str or not key.strip() or type(value) is not P256AuthorityPublicVerifier or value.key_id!=key for key,value in trusted_verifiers.items()):
            raise ValueError("trusted handoff authority verifiers are required")
        self._device_id=device_id
        self._fence_store=fence_store
        self._trusted_verifiers=dict(trusted_verifiers)

    def validate(self,directive,*,now):
        if type(directive) is not SignedEndpointFenceDirective:
            return False
        identifiers=(directive.request_id,directive.device_id,directive.resource_id,directive.previous_controller_id,directive.controller_id,directive.issuer_id,directive.signature)
        if any(type(value) is not str or not value.strip() for value in identifiers):
            return False
        if directive.device_id!=self._device_id or directive.previous_controller_id==directive.controller_id or directive.algorithm!="ECDSA_P256_SHA256":
            return False
        if type(directive.previous_fencing_token) is not int or directive.previous_fencing_token<=0 or type(directive.fencing_token) is not int or directive.fencing_token!=directive.previous_fencing_token+1:
            return False
        times=(directive.issued_at,directive.expires_at,now)
        if any(type(value) not in (int,float) or not math.isfinite(value) for value in times) or not directive.issued_at<=now<directive.expires_at:
            return False
        verifier=self._trusted_verifiers.get(directive.issuer_id)
        if verifier is None:
            return False
        try:
            if verifier.verify(directive.canonical_bytes,directive.signature) is not True:
                return False
            return self._fence_store.snapshot().get(directive.resource_id)==(directive.previous_fencing_token,directive.previous_controller_id)
        except Exception:
            return False

    def install(self,directive,*,now):
        if self.validate(directive,now=now) is not True:
            return False
        try:
            if self._fence_store.accept(directive.resource_id,directive.controller_id,directive.fencing_token) is not True:
                return False
            return self._fence_store.snapshot().get(directive.resource_id)==(directive.fencing_token,directive.controller_id)
        except Exception:
            return False
