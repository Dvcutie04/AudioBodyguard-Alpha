import json
from datetime import datetime

with open("aqss_trials.json","r",encoding="utf-8") as f:
    data=json.load(f)

if not isinstance(data,list):
    raise ValueError("aqss_trials.json must contain a JSON array")

data.sort(key=lambda x:x.get("timestamp",""))
total=len(data)
counts={}
lines=[]

def fmt_ts(ts):
    if not ts:
        return "UNKNOWN"
    try:
        return datetime.fromisoformat(ts.replace("Z","+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError,TypeError):
        return str(ts)

for i,x in enumerate(data,1):
    event=x.get("event") or {}
    weights=x.get("weights") or {}
    ts=fmt_ts(x.get("timestamp"))
    db=event.get("db",0.0)
    freq=event.get("freq",0.0)
    p_threat=weights.get("p_threat",0.0)
    decision=x.get("decision","UNRESOLVED")
    counts[decision]=counts.get(decision,0)+1
    lines.append(f"| {i} | {ts} | {db} dB | {freq} Hz | {p_threat} | {decision} |")

if total:
    metrics="\\n".join(f"- **{k}**: {v} ({v/total*100:.1f}%)" for k,v in sorted(counts.items()))
else:
    metrics="- No trials found."

table_header="| # | Timestamp | DB | Freq | Threat P | Decision |\\n|:---:|:---|---:|---:|---:|:---|\\n"
table_body="\\n".join(lines) if lines else "| - | No trials | - | - | - | - |"
report=("# Project AQSS-36-OMEGA: Instructor Evaluation Report\\n\\n"
"**Project Title:** Audio Bodyguard\\n"
"**Author:** David Cobbold\\n"
 f"**Total Trials:** {total}\\n\\n"
"## Metrics\\n"
 f"{metrics}\\n\\n"
"## Chronological Log\\n"
+table_header+table_body+"\\n")

with open("aqss_instructor_report.md","w",encoding="utf-8") as f:
    f.write(report)

print(f"Report generated: {total} trials -> aqss_instructor_report.md")
