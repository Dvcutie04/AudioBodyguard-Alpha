import base64
import hashlib
import json
import math
from dataclasses import dataclass,replace
from enum import Enum

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec


@dataclass(frozen=True)
class AtomicControllerRequest:
    operation:str
    request_id:str
    resource_id:str
    controller_id:str
    controller_key_id:str
    current_fencing_token:int
    requested_ttl_seconds:float
    challenge:str

    @property
    def canonical_bytes(self):
        payload={"challenge":self.challenge,"controller_id":self.controller_id,"controller_key_id":self.controller_key_id,"current_fencing_token":self.current_fencing_token,"operation":self.operation,"request_id":self.request_id,"requested_ttl_seconds":self.requested_ttl_seconds,"resource_id":self.resource_id}
        return json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

    @property
    def digest(self):
        return hashlib.sha256(self.canonical_bytes).hexdigest()


class P256AuthorityPublicVerifier:
    algorithm="ECDSA_P256_SHA256"

    def __init__(self,key_id,public_key):
        self.key_id=key_id
        self._public_key=public_key

    def export_spki_base64(self):
        encoded=self._public_key.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
        return base64.b64encode(encoded).decode("ascii")

    @classmethod
    def from_spki_base64(cls,key_id,encoded):
        try:
            if type(key_id) is not str or not key_id.strip() or type(encoded) is not str or not encoded:
                raise ValueError
            decoded=base64.b64decode(encoded.encode("ascii"),validate=True)
            public_key=serialization.load_der_public_key(decoded)
            if not isinstance(public_key,ec.EllipticCurvePublicKey) or not isinstance(public_key.curve,ec.SECP256R1):
                raise ValueError
            return cls(key_id,public_key)
        except (ValueError,TypeError):
            raise ValueError("invalid P-256 public verifier") from None

    def verify(self,data,signature):
        if type(data) is not bytes or type(signature) is not str or not signature:
            return False
        try:
            decoded=base64.b64decode(signature.encode("ascii"),validate=True)
            self._public_key.verify(decoded,data,ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature,ValueError,TypeError):
            return False


class P256AuthorityKeyPair:
    algorithm="ECDSA_P256_SHA256"

    def __init__(self,key_id,private_key):
        if type(key_id) is not str or not key_id.strip():
            raise ValueError("key_id must be a nonempty string")
        self.key_id=key_id
        self._private_key=private_key
        self.public_verifier=P256AuthorityPublicVerifier(key_id,private_key.public_key())

    @classmethod
    def generate(cls,key_id):
        return cls(key_id,ec.generate_private_key(ec.SECP256R1()))

    def sign(self,data):
        signature=self._private_key.sign(data,ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(signature).decode("ascii")


@dataclass(frozen=True)
class SignedAtomicControllerResult:
    request_digest:str
    resource_id:str
    controller_id:str
    controller_key_id:str
    fencing_token:int
    issued_at:float
    expires_at:float
    issuer_id:str
    algorithm:str="ECDSA_P256_SHA256"
    signature:str=""

    @property
    def canonical_bytes(self):
        payload={"algorithm":self.algorithm,"controller_id":self.controller_id,"controller_key_id":self.controller_key_id,"expires_at":self.expires_at,"fencing_token":self.fencing_token,"issued_at":self.issued_at,"issuer_id":self.issuer_id,"request_digest":self.request_digest,"resource_id":self.resource_id}
        return json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

    @classmethod
    def issue(cls,*,request,fencing_token,issued_at,expires_at,signing_key):
        unsigned=cls(request_digest=request.digest,resource_id=request.resource_id,controller_id=request.controller_id,controller_key_id=request.controller_key_id,fencing_token=fencing_token,issued_at=float(issued_at),expires_at=float(expires_at),issuer_id=signing_key.key_id,algorithm=signing_key.algorithm)
        return replace(unsigned,signature=signing_key.sign(unsigned.canonical_bytes))


class RemoteControllerResultDecision(Enum):
    ALLOW="ALLOW"
    MALFORMED="MALFORMED"
    REQUEST_DIGEST_MISMATCH="REQUEST_DIGEST_MISMATCH"
    UNKNOWN_ISSUER="UNKNOWN_ISSUER"
    INVALID_SIGNATURE="INVALID_SIGNATURE"
    NOT_YET_VALID="NOT_YET_VALID"
    EXPIRED="EXPIRED"


class RemoteControllerResultVerifier:
    def __init__(self,trusted_verifiers):
        self._trusted_verifiers=dict(trusted_verifiers)

    def validate(self,result,*,request,now):
        if not isinstance(result,SignedAtomicControllerResult) or not isinstance(request,AtomicControllerRequest):
            return RemoteControllerResultDecision.MALFORMED
        if isinstance(now,bool) or not isinstance(now,(int,float)) or not math.isfinite(now):
            return RemoteControllerResultDecision.MALFORMED
        identifiers=(request.operation,request.request_id,request.resource_id,request.controller_id,request.controller_key_id,request.challenge,result.request_digest,result.resource_id,result.controller_id,result.controller_key_id,result.issuer_id,result.algorithm,result.signature)
        if any(type(value) is not str or not value.strip() for value in identifiers):
            return RemoteControllerResultDecision.MALFORMED
        if type(request.current_fencing_token) is not int or request.current_fencing_token<0 or isinstance(request.requested_ttl_seconds,bool) or not isinstance(request.requested_ttl_seconds,(int,float)) or not math.isfinite(request.requested_ttl_seconds) or request.requested_ttl_seconds<=0:
            return RemoteControllerResultDecision.MALFORMED
        if type(result.fencing_token) is not int or result.fencing_token<=0 or any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) for value in (result.issued_at,result.expires_at)) or result.issued_at>=result.expires_at:
            return RemoteControllerResultDecision.MALFORMED
        if result.request_digest!=request.digest or (result.resource_id,result.controller_id,result.controller_key_id)!=(request.resource_id,request.controller_id,request.controller_key_id):
            return RemoteControllerResultDecision.REQUEST_DIGEST_MISMATCH
        if request.operation not in ("acquire","handoff"):
            return RemoteControllerResultDecision.MALFORMED
        if request.operation=="acquire" and request.current_fencing_token!=0:
            return RemoteControllerResultDecision.MALFORMED
        if request.operation=="handoff" and request.current_fencing_token<=0:
            return RemoteControllerResultDecision.MALFORMED
        verifier=self._trusted_verifiers.get(result.issuer_id)
        if verifier is None:
            return RemoteControllerResultDecision.UNKNOWN_ISSUER
        if result.algorithm!=verifier.algorithm or not verifier.verify(result.canonical_bytes,result.signature):
            return RemoteControllerResultDecision.INVALID_SIGNATURE
        if result.fencing_token<=request.current_fencing_token:
            return RemoteControllerResultDecision.MALFORMED
        if result.expires_at>result.issued_at+request.requested_ttl_seconds:
            return RemoteControllerResultDecision.MALFORMED
        if now<result.issued_at:
            return RemoteControllerResultDecision.NOT_YET_VALID
        if now>=result.expires_at:
            return RemoteControllerResultDecision.EXPIRED
        return RemoteControllerResultDecision.ALLOW
