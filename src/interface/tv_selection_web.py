import argparse
from html import escape
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs,urlparse

from src.edge.tv_selection_feedback_menu import TVSelectionFeedbackMenu
from src.edge.tv_selection_preferences import TVSelectionPreferences
from src.interface.tv_selection_mobile_feedback import TVSelectionMobileFeedbackIngestor


class TVSelectionWebUI:
    def __init__(self,store,*,authorized_profile_id=None):
        self.store=store
        self.mobile_feedback=TVSelectionMobileFeedbackIngestor(store,authorized_profile_id=authorized_profile_id)

    def submit(self,payload):
        if type(payload) is not dict or set(payload)!={"profile_id","device_id","approved","choice"}:
            raise ValueError("invalid feedback payload")
        menu=TVSelectionFeedbackMenu(self.store,payload["profile_id"],payload["device_id"],approved=payload["approved"])
        menu.select(payload["choice"])
        return {"ok":True}

    def sync(self,payload):
        if type(payload) is not dict or set(payload)!={"events"}:
            raise ValueError("invalid mobile synchronization payload")
        return self.mobile_feedback.ingest_batch(payload["events"])

    def render(self,profile_id,device_id):
        profile=escape(profile_id,quote=True)
        device=escape(device_id,quote=True)
        return f"""<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\"><title>TV selection feedback</title><style>:root{{color-scheme:dark}}body{{font-family:-apple-system,BlinkMacSystemFont,Roboto,sans-serif;margin:0;background:#09111f;color:#f6f8ff;min-height:100vh;display:grid;place-items:center}}main{{width:min(92vw,34rem);background:#14213a;border:1px solid #304568;border-radius:24px;padding:24px;box-sizing:border-box;box-shadow:0 18px 50px #0008}}h1{{font-size:1.35rem;margin:0 0 8px}}.device{{font-size:1.1rem;color:#a9c7ff;margin-bottom:22px}}.actions{{display:flex;gap:16px}}button{{min-width:64px;min-height:56px;border:0;border-radius:16px;padding:12px 18px;font:inherit;font-weight:700;touch-action:manipulation}}.thumb{{flex:1;font-size:1.5rem;background:#263b60;color:white}}.more{{width:100%;margin-top:14px;background:#dce8ff;color:#10203b}}dialog{{border:0;border-radius:20px;background:#14213a;color:white;padding:20px;width:min(80vw,24rem)}}dialog button{{display:block;width:100%;margin:10px 0;background:#dce8ff;color:#10203b}}#status{{min-height:1.5em;margin-top:16px;color:#b9f6ca}}</style></head><body><main><h1>Was this the right TV?</h1><div class=\"device\">{device}</div><div class=\"actions\"><button class=\"thumb\" id=\"thumbs-up\" aria-label=\"Good TV choice\" data-approved=\"true\">👍</button><button class=\"thumb\" id=\"thumbs-down\" aria-label=\"Bad TV choice\" data-approved=\"false\">👎</button></div><button class=\"more\" id=\"more-feedback\" aria-label=\"More feedback options\">More feedback options</button><p id=\"status\" role=\"status\" aria-live=\"polite\"></p></main><dialog id=\"feedback-menu\" aria-labelledby=\"menu-title\"><h2 id=\"menu-title\">Feedback options</h2><div id=\"menu-options\"></div><button id=\"cancel\">Cancel</button></dialog><script>const profile={json.dumps(profile_id)},device={json.dumps(device_id)},dialog=document.querySelector("dialog"),options=document.querySelector("#menu-options"),status=document.querySelector("#status");let timer,longPress=false,approved=true;const outboxKey="tv_selection_feedback_outbox_v1";function eventId(){{return crypto.randomUUID?crypto.randomUUID():Date.now().toString(36)+"-"+Math.random().toString(36).slice(2)}}function queueFeedback(payload){{try{{let pending=JSON.parse(localStorage.getItem(outboxKey)||"[]");if(!Array.isArray(pending))pending=[];pending.push({{...payload,schema_version:1,event_id:eventId(),recorded_at:new Date().toISOString()}});localStorage.setItem(outboxKey,JSON.stringify(pending));status.textContent="Saved on this device"}}catch(error){{status.textContent="Feedback could not be saved";throw error}}}}async function send(choice){{const payload={{profile_id:profile,device_id:device,approved,choice}};if(location.protocol==="file:"){{queueFeedback(payload);return}}try{{const response=await fetch("/feedback",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(payload)}});if(!response.ok)throw new Error("Feedback was not saved");status.textContent="Preference saved"}}catch(error){{queueFeedback(payload)}}}}function openMenu(value){{approved=value;options.replaceChildren();const rows=value?[["rating","Good choice"],["keep_this_tv","Keep this TV"]]:[["rating","Bad choice"],["never_switch_automatically","Never switch automatically"]];for(const [choice,label] of rows){{const button=document.createElement("button");button.textContent=label;button.onclick=async()=>{{await send(choice);dialog.close()}};options.append(button)}}dialog.showModal()}}for(const button of document.querySelectorAll(".thumb")){{button.addEventListener("pointerdown",()=>{{longPress=false;timer=setTimeout(()=>{{longPress=true;openMenu(button.dataset.approved==="true")}},600)}});button.addEventListener("pointerup",async()=>{{clearTimeout(timer);if(!longPress){{approved=button.dataset.approved==="true";await send("rating")}}}});button.addEventListener("pointercancel",()=>clearTimeout(timer));button.addEventListener("contextmenu",event=>event.preventDefault())}}document.querySelector("#more-feedback").onclick=()=>openMenu(true);document.querySelector("#cancel").onclick=()=>dialog.close();async function flushOutbox(){{if(location.protocol==="file:")return;let pending;try{{pending=JSON.parse(localStorage.getItem(outboxKey)||"[]")}}catch(error){{return}}if(!Array.isArray(pending)||pending.length===0)return;try{{const response=await fetch("/feedback/sync",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{events:pending}})}});if(!response.ok)return;const result=await response.json();const acknowledged=new Set([...(result.applied||[]),...(result.duplicates||[])]);const remaining=pending.filter(event=>!acknowledged.has(event.event_id));if(remaining.length){{localStorage.setItem(outboxKey,JSON.stringify(remaining))}}else{{localStorage.removeItem(outboxKey)}}}}catch(error){{return}}}}window.addEventListener("online",flushOutbox);flushOutbox();</script></body></html>"""


def make_handler(ui):
    class Handler(BaseHTTPRequestHandler):
        def _json(self,status,payload):
            body=json.dumps(payload).encode()
            self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path!="/": return self._json(404,{"ok":False})
            query=parse_qs(parsed.query)
            try: body=ui.render(query.get("profile",["profile_1"])[0],query.get("device",["living-room-tv"])[0]).encode()
            except Exception: return self._json(400,{"ok":False})
            self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if self.path not in ("/feedback","/feedback/sync"): return self._json(404,{"ok":False})
            try:
                length=int(self.headers.get("Content-Length","0"))
                if length<=0 or length>4096: raise ValueError("invalid body size")
                payload=json.loads(self.rfile.read(length))
                result=ui.sync(payload) if self.path=="/feedback/sync" else ui.submit(payload)
            except Exception: return self._json(400,{"ok":False})
            self._json(200,result)
        def log_message(self,format,*args):
            return
    return Handler


def build_ui(db_path,authorized_profile_id):
    return TVSelectionWebUI(TVSelectionPreferences(db_path),authorized_profile_id=authorized_profile_id)


def serve(db_path,authorized_profile_id,host="127.0.0.1",port=8765):
    ui=build_ui(db_path,authorized_profile_id)
    ThreadingHTTPServer((host,port),make_handler(ui)).serve_forever()


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--db",default=str(Path("tv_selection_preferences.sqlite3")));parser.add_argument("--profile",required=True);parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8765);args=parser.parse_args();serve(args.db,args.profile,args.host,args.port)
