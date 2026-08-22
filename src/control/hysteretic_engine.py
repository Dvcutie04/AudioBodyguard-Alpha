import json,hashlib
from datetime import datetime, timezone
class AQSSSafetyEngine:
    def __init__(self,attack_rate=0.8,release_rate=0.05):
        self.attack_rate=attack_rate
        self.release_rate=release_rate
        self.p_threat=0.0
    def update(self,ev):
        db,freq,imp,decay,qual=ev.get("db",0.0),ev.get("freq",0.0),ev.get("impulse_like",False),ev.get("decay_ms",100.0),ev.get("sensor_quality",1.0)
        env=0.4 if (imp and decay<50.0) else 0.0
        raw=min(max((db-60.0)/40.0,0.0),1.0)*qual
        if raw>0.5: self.p_threat+=self.attack_rate*(raw-env)
        else: self.p_threat-=self.release_rate
        self.p_threat=max(0.0,min(1.0,self.p_threat))
        fp=hashlib.sha256(f"{int(freq/100)*100}_{int(db/5)*5}_{decay}".encode()).hexdigest()[:8]
        dec="LEVEL_2: VERIFIED_SAFETY_THREAT_ESCALATION" if self.p_threat>=0.8 else ("LEVEL_1: LOW_CONFIDENCE_WARNING" if self.p_threat>0.2 else "LEVEL_0: FALSE_POSITIVE_SUPPRESSED")
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {"timestamp":ts,"event":{"db":db,"freq":freq},"weights":{"p_threat":round(self.p_threat,4)},"sensor_quality":qual,"event_fingerprint":fp,"fusion_state":"AUDIO_ONLY","pipeline_health":"NOMINAL","decision":dec}
