import time
from contextlib import closing
from dataclasses import dataclass
from enum import Enum
import sqlite3


class SwitchingMode(str,Enum):
    ASK="ask_before_switching"
    KEEP="keep_this_tv"
    FOLLOW="follow_nearest"


@dataclass(frozen=True)
class SelectionPreference:
    mode: SwitchingMode
    device_id: str | None = None


def _identifier(value):
    return type(value) is str and bool(value.strip()) and value==value.strip()


def _validate(preference):
    if not isinstance(preference,SelectionPreference) or not isinstance(preference.mode,SwitchingMode):
        raise ValueError("invalid selection preference")
    if preference.device_id is not None and not _identifier(preference.device_id):
        raise ValueError("invalid device identifier")
    if preference.mode is SwitchingMode.KEEP and preference.device_id is None:
        raise ValueError("keeping a TV requires a device identifier")


@dataclass(frozen=True)
class SelectionDecision:
    target_device_id: str | None
    suggested_device_id: str | None = None
    requires_confirmation: bool = False


class TVSelectionPreferences:
    """Durable user preferences; stored choices grant no device authority."""

    def __init__(self,path):
        self.path=str(path)
        if not self.path or self.path==":memory:":
            raise ValueError("a persistent database path is required")
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute("CREATE TABLE IF NOT EXISTS tv_selection_preferences (profile_id TEXT PRIMARY KEY NOT NULL, mode TEXT NOT NULL, device_id TEXT)")
                connection.execute("CREATE TABLE IF NOT EXISTS tv_selection_feedback (id INTEGER PRIMARY KEY, profile_id TEXT NOT NULL, device_id TEXT NOT NULL, approved INTEGER NOT NULL, reason TEXT NOT NULL, recorded_at REAL NOT NULL)")
                connection.execute("CREATE TABLE IF NOT EXISTS tv_selection_feedback_receipts (event_id TEXT PRIMARY KEY NOT NULL, profile_id TEXT NOT NULL, client_recorded_at TEXT NOT NULL, received_at REAL NOT NULL, payload_hash TEXT)")
                receipt_columns={row[1] for row in connection.execute("PRAGMA table_info(tv_selection_feedback_receipts)")}
                if "payload_hash" not in receipt_columns:
                    connection.execute("ALTER TABLE tv_selection_feedback_receipts ADD COLUMN payload_hash TEXT")

    def get(self,profile_id):
        if not _identifier(profile_id):
            raise ValueError("invalid profile identifier")
        with closing(sqlite3.connect(self.path)) as connection:
            row=connection.execute("SELECT mode, device_id FROM tv_selection_preferences WHERE profile_id = ?",(profile_id,)).fetchone()
        if row is None:
            return SelectionPreference(SwitchingMode.ASK,None)
        preference=SelectionPreference(SwitchingMode(row[0]),row[1])
        _validate(preference)
        return preference

    def save(self,profile_id,preference):
        if not _identifier(profile_id):
            raise ValueError("invalid profile identifier")
        _validate(preference)
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute("INSERT INTO tv_selection_preferences (profile_id, mode, device_id) VALUES (?, ?, ?) ON CONFLICT(profile_id) DO UPDATE SET mode=excluded.mode, device_id=excluded.device_id",(profile_id,preference.mode.value,preference.device_id))

    def decide(self,profile_id,*,nearest_device_id,eligible_device_ids):
        """Resolve saved user policy against a fresh candidate and trusted eligibility."""
        if nearest_device_id is not None and not _identifier(nearest_device_id):
            raise ValueError("invalid nearest device identifier")
        if isinstance(eligible_device_ids,(str,bytes)):
            raise ValueError("eligible devices must be a collection of identifiers")
        eligible=list(eligible_device_ids)
        if any(not _identifier(device_id) for device_id in eligible):
            raise ValueError("invalid eligible device identifier")
        eligible=set(eligible)
        preference=self.get(profile_id)
        retained=preference.device_id if preference.device_id in eligible else None
        candidate=nearest_device_id if nearest_device_id in eligible else None
        if preference.mode is SwitchingMode.KEEP:
            return SelectionDecision(retained)
        if preference.mode is SwitchingMode.FOLLOW:
            return SelectionDecision(candidate)
        if candidate is not None and candidate!=retained:
            return SelectionDecision(retained,candidate,True)
        return SelectionDecision(retained)

    def record_feedback(self,profile_id,*,device_id,approved,reason="rating"):
        if not _identifier(profile_id) or not _identifier(device_id):
            raise ValueError("invalid feedback identifier")
        if type(approved) is not bool or type(reason) is not str:
            raise ValueError("invalid feedback")
        if reason not in ("rating","keep_this_tv","never_switch_automatically"):
            raise ValueError("unsupported feedback reason")
        if (reason=="keep_this_tv" and not approved) or (reason=="never_switch_automatically" and approved):
            raise ValueError("feedback reason contradicts approval")
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                if reason=="keep_this_tv":
                    connection.execute("INSERT INTO tv_selection_preferences (profile_id, mode, device_id) VALUES (?, ?, ?) ON CONFLICT(profile_id) DO UPDATE SET mode=excluded.mode, device_id=excluded.device_id",(profile_id,SwitchingMode.KEEP.value,device_id))
                elif reason=="never_switch_automatically":
                    connection.execute("INSERT INTO tv_selection_preferences (profile_id, mode, device_id) VALUES (?, ?, NULL) ON CONFLICT(profile_id) DO UPDATE SET mode=excluded.mode",(profile_id,SwitchingMode.ASK.value))
                connection.execute("INSERT INTO tv_selection_feedback (profile_id, device_id, approved, reason, recorded_at) VALUES (?, ?, ?, ?, ?)",(profile_id,device_id,int(approved),reason,time.time()))
                connection.execute("DELETE FROM tv_selection_feedback WHERE profile_id = ? AND id NOT IN (SELECT id FROM tv_selection_feedback WHERE profile_id = ? ORDER BY id DESC LIMIT 100)",(profile_id,profile_id))

    def feedback_history(self,profile_id):
        if not _identifier(profile_id):
            raise ValueError("invalid profile identifier")
        with closing(sqlite3.connect(self.path)) as connection:
            rows=connection.execute("SELECT device_id, approved, reason, recorded_at FROM tv_selection_feedback WHERE profile_id = ? ORDER BY id",(profile_id,)).fetchall()
        return [dict(device_id=row[0],approved=bool(row[1]),reason=row[2],recorded_at=row[3]) for row in rows]

    def _record_feedback_on(self,connection,record,received_at):
        if type(record) is not tuple or len(record)!=7:
            raise ValueError("invalid feedback batch record")
        event_id,profile_id,device_id,approved,reason,client_recorded_at,payload_hash=record
        if not _identifier(event_id) or not _identifier(profile_id) or not _identifier(device_id) or not _identifier(client_recorded_at) or not _identifier(payload_hash):
            raise ValueError("invalid mobile feedback identifier")
        if type(approved) is not bool or reason not in ("rating","keep_this_tv","never_switch_automatically"):
            raise ValueError("invalid mobile feedback")
        if (reason=="keep_this_tv" and not approved) or (reason=="never_switch_automatically" and approved):
            raise ValueError("feedback reason contradicts approval")
        existing=connection.execute("SELECT payload_hash FROM tv_selection_feedback_receipts WHERE event_id = ?",(event_id,)).fetchone()
        if existing is not None:
            if existing[0]!=payload_hash:
                raise ValueError("mobile feedback event identifier collision")
            return False
        connection.execute("INSERT INTO tv_selection_feedback_receipts (event_id, profile_id, client_recorded_at, received_at, payload_hash) VALUES (?, ?, ?, ?, ?)",(event_id,profile_id,client_recorded_at,received_at,payload_hash))
        if reason=="keep_this_tv":
            connection.execute("INSERT INTO tv_selection_preferences (profile_id, mode, device_id) VALUES (?, ?, ?) ON CONFLICT(profile_id) DO UPDATE SET mode=excluded.mode, device_id=excluded.device_id",(profile_id,SwitchingMode.KEEP.value,device_id))
        elif reason=="never_switch_automatically":
            connection.execute("INSERT INTO tv_selection_preferences (profile_id, mode, device_id) VALUES (?, ?, NULL) ON CONFLICT(profile_id) DO UPDATE SET mode=excluded.mode",(profile_id,SwitchingMode.ASK.value))
        connection.execute("INSERT INTO tv_selection_feedback (profile_id, device_id, approved, reason, recorded_at) VALUES (?, ?, ?, ?, ?)",(profile_id,device_id,int(approved),reason,received_at))
        connection.execute("DELETE FROM tv_selection_feedback WHERE profile_id = ? AND id NOT IN (SELECT id FROM tv_selection_feedback WHERE profile_id = ? ORDER BY id DESC LIMIT 100)",(profile_id,profile_id))
        return True

    def _record_feedback_on(self,connection,record,received_at):
        if type(record) is not tuple or len(record)!=7:
            raise ValueError("invalid feedback batch record")
        event_id,profile_id,device_id,approved,reason,client_recorded_at,payload_hash=record
        if not _identifier(event_id) or not _identifier(profile_id) or not _identifier(device_id) or not _identifier(client_recorded_at) or not _identifier(payload_hash):
            raise ValueError("invalid mobile feedback identifier")
        if type(approved) is not bool or reason not in ("rating","keep_this_tv","never_switch_automatically"):
            raise ValueError("invalid mobile feedback")
        if (reason=="keep_this_tv" and not approved) or (reason=="never_switch_automatically" and approved):
            raise ValueError("feedback reason contradicts approval")
        existing=connection.execute("SELECT payload_hash FROM tv_selection_feedback_receipts WHERE event_id = ?",(event_id,)).fetchone()
        if existing is not None:
            if existing[0]!=payload_hash:
                raise ValueError("mobile feedback event identifier collision")
            return False
        connection.execute("INSERT INTO tv_selection_feedback_receipts (event_id, profile_id, client_recorded_at, received_at, payload_hash) VALUES (?, ?, ?, ?, ?)",(event_id,profile_id,client_recorded_at,received_at,payload_hash))
        if reason=="keep_this_tv":
            connection.execute("INSERT INTO tv_selection_preferences (profile_id, mode, device_id) VALUES (?, ?, ?) ON CONFLICT(profile_id) DO UPDATE SET mode=excluded.mode, device_id=excluded.device_id",(profile_id,SwitchingMode.KEEP.value,device_id))
        elif reason=="never_switch_automatically":
            connection.execute("INSERT INTO tv_selection_preferences (profile_id, mode, device_id) VALUES (?, ?, NULL) ON CONFLICT(profile_id) DO UPDATE SET mode=excluded.mode",(profile_id,SwitchingMode.ASK.value))
        connection.execute("INSERT INTO tv_selection_feedback (profile_id, device_id, approved, reason, recorded_at) VALUES (?, ?, ?, ?, ?)",(profile_id,device_id,int(approved),reason,received_at))
        connection.execute("DELETE FROM tv_selection_feedback WHERE profile_id = ? AND id NOT IN (SELECT id FROM tv_selection_feedback WHERE profile_id = ? ORDER BY id DESC LIMIT 100)",(profile_id,profile_id))
        return True

    def record_feedback_once(self,event_id,profile_id,*,device_id,approved,reason,client_recorded_at,payload_hash):
        record=(event_id,profile_id,device_id,approved,reason,client_recorded_at,payload_hash)
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                return self._record_feedback_on(connection,record,time.time())

    def record_feedback_batch(self,records):
        if type(records) is not list or not records or len(records)>100:
            raise ValueError("feedback batch must contain 1 to 100 records")
        results=[]
        received_at=time.time()
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                for record in records:
                    results.append(self._record_feedback_on(connection,record,received_at))
        return results
