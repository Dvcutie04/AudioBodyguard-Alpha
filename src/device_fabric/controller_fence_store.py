import fcntl
import json
import os
import tempfile
import threading
from pathlib import Path
from .monotonic_fence_anchor import MonotonicAnchorDecision,MonotonicFenceAnchor,MonotonicFenceValue,require_production_monotonic_anchor


class ControllerFenceStore:
    def __init__(self, filepath, *, monotonic_anchor=None):
        if monotonic_anchor is not None and not isinstance(monotonic_anchor,MonotonicFenceAnchor):
            raise ValueError("monotonic_anchor must implement MonotonicFenceAnchor")
        self.filepath=Path(filepath)
        self.lockpath=Path(str(self.filepath)+".lock")
        self.anchorpath=Path(str(self.filepath)+".anchor")
        self.monotonic_anchor=monotonic_anchor
        self._thread_lock=threading.RLock()

    def _parse_records(self,raw):
        if type(raw) is not dict:
            raise ValueError("controller fence store must contain an object")
        result={}
        for resource_id,record in raw.items():
            if type(resource_id) is not str or not resource_id.strip() or type(record) is not dict:
                raise ValueError("invalid controller fence record")
            token=record.get("token")
            controller_id=record.get("controller_id")
            if type(token) is not int or token<=0 or type(controller_id) is not str or not controller_id.strip():
                raise ValueError("invalid controller fence record")
            result[resource_id]=(token,controller_id)
        return result

    def _read_records(self,path):
        if not path.exists():
            return {}
        with path.open("r",encoding="utf-8") as handle:
            return self._parse_records(json.load(handle))

    def _read_primary(self):
        if not self.filepath.exists():
            return {},False,False
        with self.filepath.open("r",encoding="utf-8") as handle:
            raw=json.load(handle)
        if type(raw) is dict and set(raw)=={"version","anchor_required","resources"}:
            if type(raw.get("version")) is not int or raw.get("version")!=2 or raw.get("anchor_required") is not True:
                raise ValueError("invalid controller fence store envelope")
            return self._parse_records(raw.get("resources")),True,False
        if type(raw) is dict and set(raw)=={"version","anchor_required","monotonic_required","resources"}:
            if type(raw.get("version")) is not int or raw.get("version")!=3 or raw.get("anchor_required") is not True or raw.get("monotonic_required") is not True:
                raise ValueError("invalid controller fence store envelope")
            return self._parse_records(raw.get("resources")),True,True
        return self._parse_records(raw),False,False

    def _load_state(self):
        records,anchor_required,monotonic_required=self._read_primary()
        if monotonic_required and self.monotonic_anchor is None:
            raise ValueError("trusted anchor required")
        anchor_exists=self.anchorpath.exists()
        if anchor_required and not anchor_exists:
            raise ValueError("controller fence anchor missing")
        anchors=self._read_records(self.anchorpath)
        if (anchor_required or anchor_exists) and records!=anchors:
            raise ValueError("controller fence rollback detected")
        if self.monotonic_anchor is not None:
            try:
                trusted_values=self.monotonic_anchor.snapshot()
            except Exception as exc:
                raise ValueError("trusted anchor unavailable") from exc
            if type(trusted_values) is not dict:
                raise ValueError("trusted anchor manifest invalid")
            expected_values={resource_id:MonotonicFenceValue(resource_id=resource_id,controller_id=controller_id,fencing_token=token) for resource_id,(token,controller_id) in records.items()}
            if expected_values and not trusted_values:
                raise ValueError("trusted anchor missing")
            if trusted_values!=expected_values:
                raise ValueError("trusted anchor rollback detected")
        return records,not anchor_required

    def _load(self):
        records,_=self._load_state()
        return records

    def _encoded_records(self,records):
        return {key:{"token":value[0],"controller_id":value[1]} for key,value in records.items()}

    def _save_path(self,path,payload):
        path.parent.mkdir(parents=True,exist_ok=True)
        descriptor,temp_path=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=str(path.parent))
        try:
            with os.fdopen(descriptor,"w",encoding="utf-8") as handle:
                json.dump(payload,handle,sort_keys=True,separators=(",",":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path,path)
            directory_fd=os.open(str(path.parent),os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def _save(self,records):
        payload={"version":2,"anchor_required":True,"resources":self._encoded_records(records)}
        if self.monotonic_anchor is not None:
            payload={"version":3,"anchor_required":True,"monotonic_required":True,"resources":self._encoded_records(records)}
        self._save_path(self.filepath,payload)

    def _save_anchor(self,records):
        self._save_path(self.anchorpath,self._encoded_records(records))

    def accept(self,resource_id,controller_id,token):
        if type(resource_id) is not str or not resource_id.strip() or type(controller_id) is not str or not controller_id.strip() or type(token) is not int or token<=0:
            return False
        self.lockpath.parent.mkdir(parents=True,exist_ok=True)
        with self._thread_lock,self.lockpath.open("a+") as lock_handle:
            fcntl.flock(lock_handle.fileno(),fcntl.LOCK_EX)
            try:
                records,legacy=self._load_state()
                current=records.get(resource_id)
                if current is not None and (token<current[0] or (token==current[0] and controller_id!=current[1])):
                    return False
                changed=current is None or token>current[0]
                if self.monotonic_anchor is not None:
                    try:
                        trusted_decision=self.monotonic_anchor.advance(resource_id,controller_id,token)
                    except Exception as exc:
                        raise ValueError("trusted anchor advance failed") from exc
                    if trusted_decision not in (MonotonicAnchorDecision.ADVANCED,MonotonicAnchorDecision.ALREADY_CURRENT):
                        return False
                if changed:
                    records[resource_id]=(token,controller_id)
                if changed or legacy:
                    self._save_anchor(records)
                    self._save(records)
                return True
            finally:
                fcntl.flock(lock_handle.fileno(),fcntl.LOCK_UN)

    def snapshot(self):
        self.lockpath.parent.mkdir(parents=True,exist_ok=True)
        with self._thread_lock,self.lockpath.open("a+") as lock_handle:
            fcntl.flock(lock_handle.fileno(),fcntl.LOCK_SH)
            try:
                return dict(self._load())
            finally:
                fcntl.flock(lock_handle.fileno(),fcntl.LOCK_UN)


def build_production_controller_fence_store(filepath,*,monotonic_anchor):
    trusted_anchor=require_production_monotonic_anchor(monotonic_anchor)
    return ControllerFenceStore(filepath,monotonic_anchor=trusted_anchor)
