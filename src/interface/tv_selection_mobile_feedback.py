from datetime import datetime
import hashlib
import json


_REQUIRED={"schema_version","event_id","profile_id","device_id","approved","choice","recorded_at"}
_CHOICES={"rating","keep_this_tv","never_switch_automatically"}


def _identifier(value):
    return type(value) is str and bool(value.strip()) and value==value.strip()


class TVSelectionMobileFeedbackIngestor:
    """Validates untrusted mobile feedback before durable, idempotent collection."""

    def __init__(self,store,*,authorized_profile_id=None):
        if authorized_profile_id is not None and not _identifier(authorized_profile_id):
            raise ValueError("invalid authorized profile identifier")
        self.store=store
        self.authorized_profile_id=authorized_profile_id

    def validate(self,payload):
        if type(payload) is not dict or set(payload)!=_REQUIRED:
            raise ValueError("invalid mobile feedback envelope")
        if type(payload["schema_version"]) is not int or payload["schema_version"]!=1:
            raise ValueError("unsupported mobile feedback schema")
        if any(not _identifier(payload[key]) for key in ("event_id","profile_id","device_id","recorded_at")):
            raise ValueError("invalid mobile feedback identifier")
        if self.authorized_profile_id is not None and payload["profile_id"]!=self.authorized_profile_id:
            raise ValueError("mobile feedback profile is not authorized")
        if type(payload["approved"]) is not bool or type(payload["choice"]) is not str or payload["choice"] not in _CHOICES:
            raise ValueError("invalid mobile feedback choice")
        if (payload["choice"]=="keep_this_tv" and not payload["approved"]) or (payload["choice"]=="never_switch_automatically" and payload["approved"]):
            raise ValueError("feedback choice contradicts approval")
        try:
            recorded=datetime.fromisoformat(payload["recorded_at"].replace("Z","+00:00"))
        except ValueError as error:
            raise ValueError("invalid mobile feedback timestamp") from error
        if recorded.tzinfo is None:
            raise ValueError("mobile feedback timestamp requires timezone")
        return payload

    def ingest(self,payload):
        self.validate(payload)
        payload_hash=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
        return self.store.record_feedback_once(payload["event_id"],payload["profile_id"],device_id=payload["device_id"],approved=payload["approved"],reason=payload["choice"],client_recorded_at=payload["recorded_at"],payload_hash=payload_hash)

    def ingest_batch(self,payloads):
        if type(payloads) is not list or not payloads or len(payloads)>100:
            raise ValueError("mobile feedback batch must contain 1 to 100 events")
        for payload in payloads:
            self.validate(payload)
        records=[]
        for payload in payloads:
            payload_hash=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
            records.append((payload["event_id"],payload["profile_id"],payload["device_id"],payload["approved"],payload["choice"],payload["recorded_at"],payload_hash))
        accepted=self.store.record_feedback_batch(records)
        applied=[payload["event_id"] for payload,was_applied in zip(payloads,accepted) if was_applied]
        duplicates=[payload["event_id"] for payload,was_applied in zip(payloads,accepted) if not was_applied]
        return {"applied":applied,"duplicates":duplicates}
