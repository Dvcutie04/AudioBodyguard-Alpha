import os

def system_heartbeat():
    os.system("say tick")

def process_motion_event(d):
    v = d.get("velocity", 0)
    if v > 5.0:
        os.system("say heavy")
    elif 1.0 < v <= 5.0:
        os.system("say medium")
    else:
        system_heartbeat()

if __name__ == "__main__":
    print("AQSS-36-OMEGA Haptic Bridge Active...")
    system_heartbeat()