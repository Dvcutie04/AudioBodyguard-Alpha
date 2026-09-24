from hashlib import sha256

from .endpoint_transaction_finality_codec import _encode_head,_encode_text,encode_endpoint_finality_assertion_claims


def encode_endpoint_finality_protected_headers(*,kid):
    if type(kid) is not bytes or not 0<len(kid)<=64:
        raise ValueError("finality protected kid is invalid")
    return bytes.fromhex("a2012804")+_encode_head(2,len(kid))+kid


_ENDPOINT_FINALITY_CONTEXT_DOMAIN="AQSS/endpoint-finality/context"


def encode_endpoint_finality_external_aad(*,namespace):
    if type(namespace) is not bytes or not 0<len(namespace)<=64:
        raise ValueError("finality namespace is invalid")
    return _encode_head(4,3)+_encode_text(_ENDPOINT_FINALITY_CONTEXT_DOMAIN)+bytes((1,))+_encode_head(2,len(namespace))+namespace


def encode_endpoint_finality_signing_input(*,claims,kid,namespace):
    protected=encode_endpoint_finality_protected_headers(kid=kid)
    aad=encode_endpoint_finality_external_aad(namespace=namespace)
    payload=encode_endpoint_finality_assertion_claims(claims)
    return (_encode_head(4,4)+_encode_text("Signature1")
            +_encode_head(2,len(protected))+protected
            +_encode_head(2,len(aad))+aad
            +_encode_head(2,len(payload))+payload)


_ENDPOINT_FINALITY_PROOF_DIGEST_DOMAIN="AQSS/endpoint-finality/proof-digest"


def compute_endpoint_finality_proof_digest(*,claims,kid,namespace):
    signing_input=encode_endpoint_finality_signing_input(claims=claims,kid=kid,namespace=namespace)
    commitment=(_encode_head(4,3)+_encode_text(_ENDPOINT_FINALITY_PROOF_DIGEST_DOMAIN)
                +bytes((1,))+_encode_head(2,len(signing_input))+signing_input)
    return sha256(commitment).hexdigest()


def encode_endpoint_finality_cose_sign1(*,claims,kid,signature):
    if type(signature) is not bytes or len(signature)!=64:
        raise ValueError("finality COSE signature is invalid")
    protected=encode_endpoint_finality_protected_headers(kid=kid)
    payload=encode_endpoint_finality_assertion_claims(claims)
    encoded=(_encode_head(6,18)+_encode_head(4,4)
             +_encode_head(2,len(protected))+protected
             +_encode_head(5,0)
             +_encode_head(2,len(payload))+payload
             +_encode_head(2,len(signature))+signature)
    if len(encoded)>9216:
        raise ValueError("finality COSE envelope exceeds maximum size")
    return encoded
