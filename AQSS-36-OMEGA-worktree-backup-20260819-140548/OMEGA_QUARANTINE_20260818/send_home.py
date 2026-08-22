import time
from src.engine.pipeline import TriggerFSM, Pattern
from src.engine.dispatch import enqueue, cmd_queue, evt_queue

def run():
    targets = [("roku", "192.168.1.101"), ("samsung", "192.168.1.102"), ("lg_webos", "192.168.1.103"), ("vizio", "192.168.1.104")]
    for proto, ip in targets:
        fsm = TriggerFSM()
        print(f"--- Testing Pulse -> {proto.upper()} ({ip}) ---", flush=True)
        fsm.accept(0.99)
        time.sleep(0.35)
        pattern = fsm.evaluate_pattern()
        print(f"[FSM EVAL] State: {pattern}", flush=True)
        enqueue("MUTE", proto, ip, "SINGLE")
    cmd_queue#join()
    evt_queue#join()

if __name__ == "__main__":
    run()
