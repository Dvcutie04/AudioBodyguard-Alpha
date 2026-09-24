from math import isfinite
from struct import pack,unpack

from .endpoint_transaction_finality_protocol import EndpointFinalityAssertionClaims,EndpointFinalityDecision


_ENDPOINT_FINALITY_CLAIMS_DOMAIN="AQSS/endpoint-finality/claims"
_ENDPOINT_FINALITY_CODEC_VERSION=1
_MAX_ENDPOINT_FINALITY_CLAIMS_BYTES=8192
_MAX_ENDPOINT_FINALITY_TEXT_BYTES=256
_SIGNED_64_MIN=-(1<<63)
_SIGNED_64_MAX=(1<<63)-1


def _encode_head(major,value):
    if value<24:
        return bytes(((major<<5)|value,))
    if value<=0xff:
        return bytes(((major<<5)|24,value))
    if value<=0xffff:
        return bytes(((major<<5)|25,))+value.to_bytes(2,"big")
    if value<=0xffffffff:
        return bytes(((major<<5)|26,))+value.to_bytes(4,"big")
    if value<=0xffffffffffffffff:
        return bytes(((major<<5)|27,))+value.to_bytes(8,"big")
    raise ValueError("finality codec integer is out of range")


def _encode_integer(value):
    if type(value) is not int or not _SIGNED_64_MIN<=value<=_SIGNED_64_MAX:
        raise ValueError("finality codec integer is invalid")
    if value>=0:
        return _encode_head(0,value)
    return _encode_head(1,-1-value)


def _encode_text(value):
    if type(value) is not str:
        raise ValueError("finality codec text is invalid")
    if len(value)>_MAX_ENDPOINT_FINALITY_CLAIMS_BYTES:
        raise ValueError("finality claims encoding exceeds maximum size")
    if len(value)>_MAX_ENDPOINT_FINALITY_TEXT_BYTES:
        raise ValueError("finality codec text exceeds maximum size")
    try:
        encoded=value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("finality codec text is invalid") from error
    if len(encoded)>_MAX_ENDPOINT_FINALITY_TEXT_BYTES:
        raise ValueError("finality codec text exceeds maximum size")
    return _encode_head(3,len(encoded))+encoded


def _encode_float(value):
    if type(value) is not float or not isfinite(value):
        raise ValueError("finality codec float is invalid")
    for format_code,initial_byte in ((">e",0xf9),(">f",0xfa)):
        try:
            payload=pack(format_code,value)
        except OverflowError:
            continue
        if unpack(format_code,payload)[0].hex()==value.hex():
            return bytes((initial_byte,))+payload
    return bytes((0xfb,))+pack(">d",value)


def _encode_scalar(value):
    if type(value) is int:
        return _encode_integer(value)
    if type(value) is float:
        return _encode_float(value)
    if type(value) is str:
        return _encode_text(value)
    if value is None:
        return bytes((0xf6,))
    raise ValueError("finality codec scalar is unsupported")


def encode_endpoint_finality_assertion_claims(claims):
    if type(claims) is not EndpointFinalityAssertionClaims:
        raise ValueError("finality assertion claims are invalid")
    values=(claims.profile_version,claims.proof_id,claims.issuer_id,claims.audience,claims.device_id,claims.transaction_id,claims.intent_id,claims.capability_digest,claims.authorization_digest,claims.controller_id,claims.controller_fencing_token,claims.decision.value,claims.reason_code,claims.authority_epoch,claims.issued_at,claims.not_before,claims.expires_at,claims.previous_proof_digest)
    if claims.profile_version==2:
        values+=(claims.request_digest,)
    encoded=bytearray(_encode_head(4,3))
    encoded.extend(_encode_text(_ENDPOINT_FINALITY_CLAIMS_DOMAIN))
    encoded.extend(_encode_integer(claims.profile_version))
    encoded.extend(_encode_head(5,len(values)))
    for label,value in enumerate(values):
        encoded.extend(_encode_integer(label))
        encoded.extend(_encode_scalar(value))
        if len(encoded)>_MAX_ENDPOINT_FINALITY_CLAIMS_BYTES:
            raise ValueError("finality claims encoding exceeds maximum size")
    return bytes(encoded)


class _FinalityClaimsDecoder:
    def __init__(self,data):
        self.data=data
        self.offset=0

    def _take(self,length):
        end=self.offset+length
        if end>len(self.data):
            raise ValueError("finality claims encoding is truncated")
        value=self.data[self.offset:end]
        self.offset=end
        return value

    def _byte(self):
        return self._take(1)[0]

    def _argument(self,additional):
        if additional<24:
            return additional
        lengths={24:1,25:2,26:4,27:8}
        length=lengths.get(additional)
        if length is None:
            raise ValueError("finality claims encoding uses an unsupported length")
        return int.from_bytes(self._take(length),"big")

    def container_length(self,expected_major):
        initial=self._byte()
        if initial>>5!=expected_major:
            raise ValueError("finality claims encoding has an invalid container")
        return self._argument(initial&31)

    def integer(self):
        initial=self._byte()
        major=initial>>5
        if major not in (0,1):
            raise ValueError("finality claims encoding has an invalid integer")
        argument=self._argument(initial&31)
        return argument if major==0 else -1-argument

    def text(self):
        initial=self._byte()
        if initial>>5!=3:
            raise ValueError("finality claims encoding has invalid text")
        length=self._argument(initial&31)
        if length>_MAX_ENDPOINT_FINALITY_TEXT_BYTES:
            raise ValueError("finality claims encoding text exceeds maximum size")
        payload=self._take(length)
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("finality claims encoding has invalid text") from error

    def scalar(self):
        initial=self.data[self.offset] if self.offset<len(self.data) else None
        if initial is None:
            raise ValueError("finality claims encoding is truncated")
        major=initial>>5
        if major in (0,1):
            return self.integer()
        if major==3:
            return self.text()
        self.offset+=1
        if initial==0xf6:
            return None
        formats={0xf9:(">e",2),0xfa:(">f",4),0xfb:(">d",8)}
        format_and_length=formats.get(initial)
        if format_and_length is None:
            raise ValueError("finality claims encoding has an unsupported scalar")
        format_code,length=format_and_length
        return unpack(format_code,self._take(length))[0]


def decode_endpoint_finality_assertion_claims(data):
    if type(data) is not bytes:
        raise ValueError("finality claims encoding is invalid")
    if len(data)>_MAX_ENDPOINT_FINALITY_CLAIMS_BYTES:
        raise ValueError("finality claims encoding exceeds maximum size")
    decoder=_FinalityClaimsDecoder(data)
    if decoder.container_length(4)!=3:
        raise ValueError("finality claims encoding frame is invalid")
    if decoder.text()!=_ENDPOINT_FINALITY_CLAIMS_DOMAIN:
        raise ValueError("finality claims encoding domain is invalid")
    version=decoder.integer()
    if version not in (_ENDPOINT_FINALITY_CODEC_VERSION,2):
        raise ValueError("finality claims encoding version is invalid")
    field_count=18 if version==1 else 19
    if decoder.container_length(5)!=field_count:
        raise ValueError("finality claims encoding field count is invalid")
    values=[]
    for expected_label in range(field_count):
        if decoder.integer()!=expected_label:
            raise ValueError("finality claims encoding labels are invalid")
        values.append(decoder.scalar())
    if decoder.offset!=len(data):
        raise ValueError("finality claims encoding has trailing data")
    try:
        decision=EndpointFinalityDecision(values[11])
        claims=EndpointFinalityAssertionClaims(profile_version=values[0],proof_id=values[1],issuer_id=values[2],audience=values[3],device_id=values[4],transaction_id=values[5],intent_id=values[6],capability_digest=values[7],authorization_digest=values[8],controller_id=values[9],controller_fencing_token=values[10],decision=decision,reason_code=values[12],authority_epoch=values[13],issued_at=values[14],not_before=values[15],expires_at=values[16],previous_proof_digest=values[17],request_digest=values[18] if version==2 else None)
    except (TypeError,ValueError) as error:
        raise ValueError("finality claims encoding values are invalid") from error
    if claims.profile_version!=version:
        raise ValueError("finality claims encoding profile version mismatch")
    if encode_endpoint_finality_assertion_claims(claims)!=data:
        raise ValueError("finality claims encoding is not canonical")
    return claims
