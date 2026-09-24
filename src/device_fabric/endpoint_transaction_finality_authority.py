from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric import ec

from .endpoint_transaction_finality_envelope import SignatureVerifiedEndpointFinalityEnvelope, decode_endpoint_finality_cose_sign1, verify_endpoint_finality_cose_sign1


@dataclass(frozen=True, slots=True)
class EndpointFinalityTrustedKey:
    kid: bytes
    namespace: bytes
    issuer_id: str
    audience: str
    device_id: str
    authority_epoch: int
    public_key: ec.EllipticCurvePublicKey

    def __post_init__(self):
        for name in ("kid","namespace"):
            value=getattr(self,name)
            if type(value) is not bytes or not 0<len(value)<=64:
                raise ValueError("finality trusted key "+name+" is invalid")
        for name in ("issuer_id","audience","device_id"):
            value=getattr(self,name)
            if type(value) is not str or not value.strip() or value!=value.strip():
                raise ValueError("finality trusted key "+name+" is invalid")
        if type(self.authority_epoch) is not int or self.authority_epoch<=0:
            raise ValueError("finality trusted key authority_epoch is invalid")
        if not isinstance(self.public_key,ec.EllipticCurvePublicKey) or not isinstance(self.public_key.curve,ec.SECP256R1):
            raise ValueError("finality trusted public key is invalid")


@dataclass(frozen=True, slots=True)
class EndpointFinalityAuthoritySnapshot:
    active_authority_epoch: int
    keys: tuple[EndpointFinalityTrustedKey, ...]

    def __post_init__(self):
        if type(self.active_authority_epoch) is not int or self.active_authority_epoch<=0:
            raise ValueError("finality active authority epoch is invalid")
        if type(self.keys) is not tuple or not 0<len(self.keys)<=64:
            raise ValueError("finality trusted keys are invalid")
        identities=set()
        for key in self.keys:
            if type(key) is not EndpointFinalityTrustedKey:
                raise ValueError("finality trusted keys are invalid")
            identity=(key.issuer_id,key.audience,key.device_id,key.authority_epoch,key.kid)
            if identity in identities:
                raise ValueError("duplicate finality trusted key identity")
            identities.add(identity)


@dataclass(frozen=True, slots=True, init=False)
class AuthorityVerifiedEndpointFinalityEnvelope:
    signature_verified: SignatureVerifiedEndpointFinalityEnvelope
    trusted_key: EndpointFinalityTrustedKey
    active_authority_epoch: int

    def __init__(self, *args, **kwargs):
        raise TypeError("authority-verified finality envelope requires authority verification")

    @property
    def claims(self):
        return self.signature_verified.claims

    @property
    def kid(self):
        return self.signature_verified.kid

    @property
    def namespace(self):
        return self.signature_verified.namespace


def verify_endpoint_finality_with_authority(*,wire,trust,issuer_id,audience,device_id,authority_epoch):
    if type(trust) is not EndpointFinalityAuthoritySnapshot:
        raise ValueError("finality authority snapshot is invalid")
    for name,value in (("issuer_id",issuer_id),("audience",audience),("device_id",device_id)):
        if type(value) is not str or not value.strip() or value!=value.strip():
            raise ValueError("expected finality "+name+" is invalid")
    if type(authority_epoch) is not int or authority_epoch<=0 or trust.active_authority_epoch!=authority_epoch:
        raise ValueError("finality authority epoch is invalid")
    envelope=decode_endpoint_finality_cose_sign1(wire)
    claims=envelope.claims
    if (claims.issuer_id,claims.audience,claims.device_id,claims.authority_epoch)!=(issuer_id,audience,device_id,authority_epoch):
        raise ValueError("finality authority claims mismatch")
    matches=[key for key in trust.keys if (key.issuer_id,key.audience,key.device_id,key.authority_epoch,key.kid)==(issuer_id,audience,device_id,authority_epoch,envelope.kid)]
    if len(matches)!=1:
        raise ValueError("finality signing key is not trusted")
    key=matches[0]
    signature_verified=verify_endpoint_finality_cose_sign1(wire=wire,namespace=key.namespace,public_key=key.public_key)
    verified=object.__new__(AuthorityVerifiedEndpointFinalityEnvelope)
    object.__setattr__(verified,"signature_verified",signature_verified)
    object.__setattr__(verified,"trusted_key",key)
    object.__setattr__(verified,"active_authority_epoch",trust.active_authority_epoch)
    return verified
