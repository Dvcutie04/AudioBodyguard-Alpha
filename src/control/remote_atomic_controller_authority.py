import fcntl
import json
import math
import os
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import asdict,replace
from pathlib import Path

from .active_controller_lease import ActiveControllerLease,ActiveControllerLeaseAuthority,ControllerLeaseDecision
from .controller_lease_grant import ControllerLeaseGrantIssuer
from .remote_controller_protocol import AtomicControllerRequest,P256AuthorityKeyPair,SignedAtomicControllerResult
from ..device_fabric.endpoint_handoff_fence import SignedEndpointFenceDirective


class IdempotentRemoteControllerAuthority:
    def __init__(self,authority=None,*,state_path=None,signing_key=None,endpoint_device_bindings=None):
        if authority is None:
            authority=ActiveControllerLeaseAuthority()
        if not isinstance(authority,ActiveControllerLeaseAuthority):
            raise ValueError("ActiveControllerLeaseAuthority is required")
        if state_path is not None and authority._state_path is not None:
            raise ValueError("remote authority requires one persistence envelope")
        self._authority=authority
        self._signing_key=signing_key
        if endpoint_device_bindings is not None and (type(endpoint_device_bindings) is not dict or any(type(resource) is not str or not resource.strip() or type(device) is not str or not device.strip() for resource,device in endpoint_device_bindings.items())):
            raise ValueError("endpoint device bindings are invalid")
        self._endpoint_device_bindings=dict(endpoint_device_bindings or {})
        self._committed_requests={}
        self._grant_key_bindings={}
        self._protocol_results={}
        self._handoff_directives={}
        self._state_path=Path(state_path) if state_path is not None else None
        self._lock_path=Path(str(self._state_path)+".lock") if self._state_path is not None else None
        self._lock=threading.RLock()
        with self._state_guard(exclusive=False):
            pass

    @staticmethod
    def _lease_record(lease):
        return {"resource_id":lease.resource_id,"controller_id":lease.controller_id,"fencing_token":lease.fencing_token,"issued_at":lease.issued_at,"expires_at":lease.expires_at}

    @staticmethod
    def _parse_lease(raw):
        required={"resource_id","controller_id","fencing_token","issued_at","expires_at"}
        if type(raw) is not dict or set(raw)!=required:
            raise ValueError("invalid remote authority lease")
        resource_id=raw["resource_id"]
        controller_id=raw["controller_id"]
        fencing_token=raw["fencing_token"]
        issued_at=raw["issued_at"]
        expires_at=raw["expires_at"]
        if type(resource_id) is not str or not resource_id.strip() or type(controller_id) is not str or not controller_id.strip() or type(fencing_token) is not int or fencing_token<=0:
            raise ValueError("invalid remote authority lease")
        if isinstance(issued_at,bool) or not isinstance(issued_at,(int,float)) or not math.isfinite(issued_at) or isinstance(expires_at,bool) or not isinstance(expires_at,(int,float)) or not math.isfinite(expires_at) or float(expires_at)<=float(issued_at):
            raise ValueError("invalid remote authority lease")
        return ActiveControllerLease(resource_id,controller_id,fencing_token,float(issued_at),float(expires_at))

    def _load_state(self):
        if self._state_path is None or not self._state_path.exists():
            return
        with self._state_path.open("r",encoding="utf-8") as handle:
            raw=json.load(handle)
        if type(raw) is dict and set(raw)=={"version","resources","committed_requests"} and raw.get("version")==1 and type(raw["resources"]) is dict and type(raw["committed_requests"]) is dict:
            binding_records={}
            protocol_result_records={}
            directive_records={}
        elif type(raw) is dict and set(raw)=={"version","resources","committed_requests","grant_key_bindings"} and raw.get("version")==2 and type(raw["resources"]) is dict and type(raw["committed_requests"]) is dict and type(raw["grant_key_bindings"]) is dict:
            binding_records=raw["grant_key_bindings"]
            protocol_result_records={}
            directive_records={}
        elif type(raw) is dict and set(raw)=={"version","resources","committed_requests","grant_key_bindings","protocol_results"} and raw.get("version")==3 and type(raw["resources"]) is dict and type(raw["committed_requests"]) is dict and type(raw["grant_key_bindings"]) is dict and type(raw["protocol_results"]) is dict:
            binding_records=raw["grant_key_bindings"]
            protocol_result_records=raw["protocol_results"]
            directive_records={}
        elif type(raw) is dict and set(raw)=={"version","resources","committed_requests","grant_key_bindings","protocol_results","handoff_directives"} and raw.get("version")==4 and type(raw["resources"]) is dict and type(raw["committed_requests"]) is dict and type(raw["grant_key_bindings"]) is dict and type(raw["protocol_results"]) is dict and type(raw["handoff_directives"]) is dict:
            binding_records=raw["grant_key_bindings"]
            protocol_result_records=raw["protocol_results"]
            directive_records=raw["handoff_directives"]
        else:
            raise ValueError("invalid remote controller authority state")
        active={}
        highest={}
        for resource_id,record in raw["resources"].items():
            if type(resource_id) is not str or not resource_id.strip() or type(record) is not dict or set(record)!={"lease","highest_token"}:
                raise ValueError("invalid remote controller authority resource")
            lease=self._parse_lease(record["lease"])
            token=record["highest_token"]
            if lease.resource_id!=resource_id or type(token) is not int or token<lease.fencing_token:
                raise ValueError("invalid remote controller authority resource")
            active[resource_id]=lease
            highest[resource_id]=token
        committed={}
        for request_id,record in raw["committed_requests"].items():
            if type(request_id) is not str or not request_id.strip() or type(record) is not dict or set(record)!={"fingerprint","lease"}:
                raise ValueError("invalid remote authority request record")
            fingerprint=record["fingerprint"]
            lease=self._parse_lease(record["lease"])
            valid=False
            if type(fingerprint) is list and len(fingerprint)==5 and fingerprint[0]=="acquire":
                valid=fingerprint[1]==lease.resource_id and fingerprint[2]==lease.controller_id and fingerprint[3]==lease.issued_at and not isinstance(fingerprint[4],bool) and isinstance(fingerprint[4],(int,float)) and math.isfinite(fingerprint[4]) and fingerprint[4]>0 and lease.expires_at==lease.issued_at+float(fingerprint[4])
            elif type(fingerprint) is list and len(fingerprint)==9 and fingerprint[0]=="handoff":
                valid=fingerprint[1]==lease.resource_id and type(fingerprint[2]) is str and bool(fingerprint[2].strip()) and type(fingerprint[3]) is int and fingerprint[3]>0 and not isinstance(fingerprint[4],bool) and isinstance(fingerprint[4],(int,float)) and math.isfinite(fingerprint[4]) and not isinstance(fingerprint[5],bool) and isinstance(fingerprint[5],(int,float)) and math.isfinite(fingerprint[5]) and fingerprint[5]>fingerprint[4] and fingerprint[6]==lease.controller_id and fingerprint[7]==lease.issued_at and not isinstance(fingerprint[8],bool) and isinstance(fingerprint[8],(int,float)) and math.isfinite(fingerprint[8]) and fingerprint[8]>0 and lease.expires_at==lease.issued_at+float(fingerprint[8])
            if not valid or highest.get(lease.resource_id,0)<lease.fencing_token:
                raise ValueError("invalid remote authority request record")
            committed[request_id]=(fingerprint,lease)
        grant_key_bindings={}
        for request_id,controller_key_id in binding_records.items():
            if request_id not in committed or type(controller_key_id) is not str or not controller_key_id.strip():
                raise ValueError("invalid remote authority controller key binding")
            grant_key_bindings[request_id]=controller_key_id
        protocol_results={}
        required_result_fields=set(SignedAtomicControllerResult.__dataclass_fields__)
        for request_id,record in protocol_result_records.items():
            if request_id not in committed or type(record) is not dict or set(record)!=required_result_fields:
                raise ValueError("invalid persisted remote protocol result")
            try:
                result=SignedAtomicControllerResult(**record)
                _,lease=committed[request_id]
                verifier=getattr(self._signing_key,"public_verifier",None)
                valid=type(result.request_digest) is str and len(result.request_digest)==64 and all(character in "0123456789abcdef" for character in result.request_digest) and result.resource_id==lease.resource_id and result.controller_id==lease.controller_id and result.controller_key_id==grant_key_bindings.get(request_id) and result.fencing_token==lease.fencing_token and result.issued_at==lease.issued_at and result.expires_at==lease.expires_at and self._signing_key is not None and result.issuer_id==self._signing_key.key_id and result.algorithm==self._signing_key.algorithm and verifier is not None and verifier.verify(result.canonical_bytes,result.signature)
            except Exception:
                valid=False
            if not valid:
                raise ValueError("invalid persisted remote protocol result")
            protocol_results[request_id]=result
        handoff_directives={}
        required_directive_fields=set(SignedEndpointFenceDirective.__dataclass_fields__)
        for request_id,record in directive_records.items():
            if request_id not in committed or type(record) is not dict or set(record)!=required_directive_fields:
                raise ValueError("invalid persisted handoff directive")
            fingerprint,lease=committed[request_id]
            if fingerprint[0]!="handoff":
                raise ValueError("invalid persisted handoff directive")
            try:
                directive=SignedEndpointFenceDirective(**record)
                verifier=getattr(self._signing_key,"public_verifier",None)
                valid=(directive.request_id==request_id and type(directive.device_id) is str and bool(directive.device_id.strip()) and self._endpoint_device_bindings.get(lease.resource_id)==directive.device_id and directive.resource_id==lease.resource_id and directive.previous_controller_id==fingerprint[2] and type(directive.previous_fencing_token) is int and directive.previous_fencing_token==fingerprint[3] and directive.controller_id==lease.controller_id and type(directive.fencing_token) is int and directive.fencing_token==lease.fencing_token==directive.previous_fencing_token+1 and directive.issued_at==lease.issued_at and directive.expires_at==lease.expires_at and self._signing_key is not None and directive.issuer_id==self._signing_key.key_id and directive.algorithm=="ECDSA_P256_SHA256" and verifier is not None and verifier.verify(directive.canonical_bytes,directive.signature) is True)
            except Exception:
                valid=False
            if not valid:
                raise ValueError("invalid persisted handoff directive")
            handoff_directives[request_id]=directive
        self._authority._active=active
        self._authority._highest_tokens=highest
        self._committed_requests=committed
        self._grant_key_bindings=grant_key_bindings
        self._protocol_results=protocol_results
        self._handoff_directives=handoff_directives

    def _save_state(self,committed_requests):
        if self._state_path is None:
            return
        self._state_path.parent.mkdir(parents=True,exist_ok=True)
        resources={resource_id:{"lease":self._lease_record(lease),"highest_token":self._authority._highest_tokens[resource_id]} for resource_id,lease in self._authority._active.items()}
        requests={request_id:{"fingerprint":fingerprint,"lease":self._lease_record(lease)} for request_id,(fingerprint,lease) in committed_requests.items()}
        if self._handoff_directives:
            payload={"version":4,"resources":resources,"committed_requests":requests,"grant_key_bindings":dict(self._grant_key_bindings),"protocol_results":{request_id:asdict(result) for request_id,result in self._protocol_results.items()},"handoff_directives":{request_id:asdict(directive) for request_id,directive in self._handoff_directives.items()}}
        elif self._protocol_results:
            payload={"version":3,"resources":resources,"committed_requests":requests,"grant_key_bindings":dict(self._grant_key_bindings),"protocol_results":{request_id:asdict(result) for request_id,result in self._protocol_results.items()}}
        else:
            payload={"version":2,"resources":resources,"committed_requests":requests,"grant_key_bindings":dict(self._grant_key_bindings)}
        descriptor,temp_path=tempfile.mkstemp(prefix=self._state_path.name+".",suffix=".tmp",dir=str(self._state_path.parent))
        try:
            with os.fdopen(descriptor,"w",encoding="utf-8") as handle:
                json.dump(payload,handle,sort_keys=True,separators=(",",":"),allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path,self._state_path)
            directory_fd=os.open(str(self._state_path.parent),os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @contextmanager
    def _state_guard(self,*,exclusive):
        with self._lock:
            if self._state_path is None:
                yield
                return
            self._lock_path.parent.mkdir(parents=True,exist_ok=True)
            with self._lock_path.open("a+") as lock_handle:
                fcntl.flock(lock_handle.fileno(),fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                try:
                    self._load_state()
                    yield
                finally:
                    fcntl.flock(lock_handle.fileno(),fcntl.LOCK_UN)

    def acquire(self,*,request_id,resource_id,controller_id,now,ttl_seconds):
        if type(request_id) is not str or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        fingerprint=["acquire",resource_id,controller_id,now,ttl_seconds]
        with self._state_guard(exclusive=True):
            committed=self._committed_requests.get(request_id)
            if committed is not None:
                committed_fingerprint,lease=committed
                if committed_fingerprint!=fingerprint:
                    raise ValueError("request_id already committed with different payload")
                return lease
            old_active=dict(self._authority._active)
            old_highest=dict(self._authority._highest_tokens)
            lease=self._authority.acquire(resource_id=resource_id,controller_id=controller_id,now=now,ttl_seconds=ttl_seconds)
            candidate=dict(self._committed_requests)
            candidate[request_id]=(fingerprint,lease)
            try:
                self._save_state(candidate)
            except Exception:
                self._authority._active=old_active
                self._authority._highest_tokens=old_highest
                raise
            self._committed_requests=candidate
            return lease

    def handoff(self,*,request_id,current_lease,next_controller_id,now,ttl_seconds):
        if type(request_id) is not str or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        if not isinstance(current_lease,ActiveControllerLease):
            raise ValueError("current_lease must be an ActiveControllerLease")
        fingerprint=["handoff",current_lease.resource_id,current_lease.controller_id,current_lease.fencing_token,current_lease.issued_at,current_lease.expires_at,next_controller_id,now,ttl_seconds]
        with self._state_guard(exclusive=True):
            committed=self._committed_requests.get(request_id)
            if committed is not None:
                committed_fingerprint,lease=committed
                if committed_fingerprint!=fingerprint:
                    raise ValueError("request_id already committed with different payload")
                return lease
            old_active=dict(self._authority._active)
            old_highest=dict(self._authority._highest_tokens)
            lease=self._authority.handoff(current_lease=current_lease,next_controller_id=next_controller_id,now=now,ttl_seconds=ttl_seconds)
            candidate=dict(self._committed_requests)
            candidate[request_id]=(fingerprint,lease)
            try:
                self._save_state(candidate)
            except Exception:
                self._authority._active=old_active
                self._authority._highest_tokens=old_highest
                raise
            self._committed_requests=candidate
            return lease

    def issue_grant(self,*,request_id,controller_key_id,now):
        if type(request_id) is not str or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        if type(controller_key_id) is not str or not controller_key_id.strip():
            raise ValueError("controller_key_id must be a nonempty string")
        if self._signing_key is None:
            raise RuntimeError("remote authority signing key is not configured")
        with self._state_guard(exclusive=True):
            committed=self._committed_requests.get(request_id)
            if committed is None:
                raise RuntimeError("request_id has not been committed")
            bound_key=self._grant_key_bindings.get(request_id)
            if bound_key is not None and bound_key!=controller_key_id:
                raise ValueError("request_id already bound to a different controller key")
            fingerprint,lease=committed
            if fingerprint[0]=="handoff":
                raise RuntimeError("endpoint readiness is required before handoff grant")
            issuer=ControllerLeaseGrantIssuer(self._authority,self._signing_key)
            grant=issuer.issue(lease=lease,controller_key_id=controller_key_id,nonce=request_id,now=now)
            if bound_key is None:
                previous_bindings=dict(self._grant_key_bindings)
                candidate_bindings=dict(previous_bindings)
                candidate_bindings[request_id]=controller_key_id
                self._grant_key_bindings=candidate_bindings
                try:
                    self._save_state(self._committed_requests)
                except Exception:
                    self._grant_key_bindings=previous_bindings
                    raise
            return grant

    def issue_protocol_result(self,*,request):
        if not isinstance(request,AtomicControllerRequest):
            raise ValueError("AtomicControllerRequest is required")
        identifiers=(request.operation,request.request_id,request.resource_id,request.controller_id,request.controller_key_id,request.challenge)
        if any(type(value) is not str or not value.strip() for value in identifiers) or type(request.current_fencing_token) is not int or isinstance(request.requested_ttl_seconds,bool) or not isinstance(request.requested_ttl_seconds,(int,float)) or not math.isfinite(request.requested_ttl_seconds) or request.requested_ttl_seconds<=0:
            raise ValueError("invalid protocol request")
        if self._signing_key is None or getattr(self._signing_key,"algorithm",None)!="ECDSA_P256_SHA256":
            raise RuntimeError("P-256 remote authority signing key is not configured")
        with self._state_guard(exclusive=True):
            committed=self._committed_requests.get(request.request_id)
            if committed is None:
                raise RuntimeError("request_id has not been committed")
            fingerprint,lease=committed
            matches=False
            if len(fingerprint)==5 and fingerprint[0]=="acquire":
                matches=request.operation=="acquire" and request.resource_id==fingerprint[1] and request.controller_id==fingerprint[2] and request.current_fencing_token==0 and float(request.requested_ttl_seconds)==float(fingerprint[4]) and lease.issued_at==fingerprint[3]
            elif len(fingerprint)==9 and fingerprint[0]=="handoff":
                matches=request.operation=="handoff" and request.resource_id==fingerprint[1] and request.controller_id==fingerprint[6] and request.current_fencing_token==fingerprint[3] and float(request.requested_ttl_seconds)==float(fingerprint[8]) and lease.issued_at==fingerprint[7]
            if not matches:
                raise ValueError("request_id already committed with different protocol request")
            if fingerprint[0]=="handoff":
                raise RuntimeError("endpoint readiness is required before handoff result")
            existing=self._protocol_results.get(request.request_id)
            if existing is not None:
                if existing.request_digest!=request.digest:
                    raise ValueError("request_id already committed with different protocol request")
                return existing
            bound_key=self._grant_key_bindings.get(request.request_id)
            if bound_key is not None and bound_key!=request.controller_key_id:
                raise ValueError("request_id already committed with different protocol request")
            result=SignedAtomicControllerResult.issue(request=request,fencing_token=lease.fencing_token,issued_at=lease.issued_at,expires_at=lease.expires_at,signing_key=self._signing_key)
            previous_bindings=dict(self._grant_key_bindings)
            previous_results=dict(self._protocol_results)
            self._grant_key_bindings={**previous_bindings,request.request_id:request.controller_key_id}
            self._protocol_results={**previous_results,request.request_id:result}
            try:
                self._save_state(self._committed_requests)
            except Exception:
                self._grant_key_bindings=previous_bindings
                self._protocol_results=previous_results
                raise
            return result

    def issue_fence_directive(self,*,request_id,device_id,now):
        if type(request_id) is not str or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        if type(device_id) is not str or not device_id.strip():
            raise ValueError("endpoint device binding is required")
        if type(now) not in (int,float) or not math.isfinite(now):
            raise ValueError("directive time is invalid")
        if self._state_path is None:
            raise RuntimeError("durable remote authority is required for fence directive")
        if type(self._signing_key) is not P256AuthorityKeyPair:
            raise RuntimeError("P-256 handoff authority signing key is required")
        with self._state_guard(exclusive=True):
            committed=self._committed_requests.get(request_id)
            if committed is None or committed[0][0]!="handoff":
                raise RuntimeError("committed handoff is required")
            fingerprint,lease=committed
            if self._endpoint_device_bindings.get(lease.resource_id)!=device_id:
                raise ValueError("endpoint device binding mismatch")
            if fingerprint[2]==lease.controller_id or lease.fencing_token!=fingerprint[3]+1:
                raise RuntimeError("handoff fence transition is invalid")
            if self._authority.validate(lease,now=now) is not ControllerLeaseDecision.ALLOW:
                raise RuntimeError("handoff lease is not active")
            existing=self._handoff_directives.get(request_id)
            if existing is not None:
                return existing
            unsigned=SignedEndpointFenceDirective(request_id=request_id,device_id=device_id,resource_id=lease.resource_id,previous_controller_id=fingerprint[2],previous_fencing_token=fingerprint[3],controller_id=lease.controller_id,fencing_token=lease.fencing_token,issued_at=lease.issued_at,expires_at=lease.expires_at,issuer_id=self._signing_key.key_id)
            directive=replace(unsigned,signature=self._signing_key.sign(unsigned.canonical_bytes))
            previous=dict(self._handoff_directives)
            self._handoff_directives={**previous,request_id:directive}
            try:
                self._save_state(self._committed_requests)
            except Exception:
                self._handoff_directives=previous
                raise
            return directive

    def highest_token(self,resource_id):
        if type(resource_id) is not str or not resource_id.strip():
            raise ValueError("resource_id must be a non-empty string")
        with self._state_guard(exclusive=False):
            return self._authority._highest_tokens.get(resource_id,0)
