from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

from .endpoint_transaction_finality_codec import _FinalityClaimsDecoder, decode_endpoint_finality_assertion_claims
from .endpoint_transaction_finality_commitment import encode_endpoint_finality_cose_sign1, encode_endpoint_finality_protected_headers, encode_endpoint_finality_signing_input
from .endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims


@dataclass(frozen=True)
class EndpointFinalityCoseSign1Envelope:
    claims: EndpointFinalityAssertionClaims
    kid: bytes
    signature: bytes
    protected: bytes
    payload: bytes


class _EnvelopeDecoder(_FinalityClaimsDecoder):
    def byte_string(self, maximum, *, exact=None):
        initial=self._byte()
        if initial>>5!=2:
            raise ValueError("finality COSE envelope has an invalid byte string")
        length=self._argument(initial&31)
        if length>maximum or (exact is not None and length!=exact):
            raise ValueError("finality COSE envelope has an invalid byte string size")
        return self._take(length)


def decode_endpoint_finality_cose_sign1(data):
    if type(data) is not bytes or len(data)>9216:
        raise ValueError("finality COSE envelope is invalid")
    decoder=_EnvelopeDecoder(data)
    if decoder.container_length(6)!=18 or decoder.container_length(4)!=4:
        raise ValueError("finality COSE envelope framing is invalid")
    protected=decoder.byte_string(256)
    if decoder.container_length(5)!=0:
        raise ValueError("finality COSE unprotected headers are invalid")
    payload=decoder.byte_string(8192)
    signature=decoder.byte_string(64,exact=64)
    if decoder.offset!=len(data):
        raise ValueError("finality COSE envelope has trailing data")
    header=_EnvelopeDecoder(protected)
    if header.container_length(5)!=2 or header.integer()!=1 or header.integer()!=-9 or header.integer()!=4:
        raise ValueError("finality COSE protected headers are invalid")
    kid=header.byte_string(64)
    if not kid or header.offset!=len(protected) or encode_endpoint_finality_protected_headers(kid=kid)!=protected:
        raise ValueError("finality COSE protected headers are invalid")
    claims=decode_endpoint_finality_assertion_claims(payload)
    if encode_endpoint_finality_cose_sign1(claims=claims,kid=kid,signature=signature)!=data:
        raise ValueError("finality COSE envelope is not canonical")
    return EndpointFinalityCoseSign1Envelope(claims=claims,kid=kid,signature=signature,protected=protected,payload=payload)


@dataclass(frozen=True, slots=True, init=False)
class SignatureVerifiedEndpointFinalityEnvelope:
    envelope: EndpointFinalityCoseSign1Envelope
    namespace: bytes
    public_key: ec.EllipticCurvePublicKey

    def __init__(self, *args, **kwargs):
        raise TypeError("signature-verified finality envelope requires verification")

    @property
    def claims(self):
        return self.envelope.claims

    @property
    def kid(self):
        return self.envelope.kid


def verify_endpoint_finality_cose_sign1(*, wire, namespace, public_key):
    envelope=decode_endpoint_finality_cose_sign1(wire)
    if not isinstance(public_key,ec.EllipticCurvePublicKey) or not isinstance(public_key.curve,ec.SECP256R1):
        raise ValueError("finality verification key is invalid")
    signing_input=encode_endpoint_finality_signing_input(claims=envelope.claims,kid=envelope.kid,namespace=namespace)
    r=int.from_bytes(envelope.signature[:32],"big")
    s=int.from_bytes(envelope.signature[32:],"big")
    der_signature=utils.encode_dss_signature(r,s)
    try:
        public_key.verify(der_signature,signing_input,ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as error:
        raise ValueError("finality COSE signature verification failed") from error
    verified=object.__new__(SignatureVerifiedEndpointFinalityEnvelope)
    object.__setattr__(verified,"envelope",envelope)
    object.__setattr__(verified,"namespace",namespace)
    object.__setattr__(verified,"public_key",public_key)
    return verified
