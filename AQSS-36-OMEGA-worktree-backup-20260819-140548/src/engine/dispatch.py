import queue, threading, sqlite3
from src.engine.tv_drivers import TVDriver

cmd_queue = queue.Queue()
evt_queue = queue.Queue()

def init_db():
    conn = sqlite3.connect("events.db")
    conn.execute("CREATE TABLE IF NOT EXISTS event_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, trigger_type TEXT, action TEXT, protocol TEXT, target_ip TEXT)")
    conn.commit()
    conn.close()

init_db()

def cmd_worker():
    while True:
        item = cmd_queue.get()
        if item is None: break
        action, proto, ip, trigger = item
        TVDriver.dispatch(proto, ip, action)
        print(f"[DISPATCH OK] {action} -> {proto.upper()} ({ip})", flush=True)
        evt_queue.put((trigger, action, proto, ip))
        cmd_queue.task_done()

def evt_worker():
    conn = sqlite3.connect("events.db", timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    while True:
        item = evt_queue.get()
        if item is None: break
        trigger, action, proto, ip = item
        try:
            conn.execute("INSERT INTO event_log (trigger_type, action, protocol, target_ip) VALUES (?, ?, ?, ?)", (trigger, action, proto, ip))
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] {e}", flush=True)
        print(f"[DB LOGGED] {trigger} | {action} | {proto}", flush=True)
        evt_queue.task_done()

t1 = threading.Thread(target=cmd_worker, daemon=True)
t2 = threading.Thread(target=evt_worker, daemon=True)
t1.start()
t2.start()

def enqueue(action, proto, ip, trigger):
    cmd_queue.put((action, proto, ip, trigger))
