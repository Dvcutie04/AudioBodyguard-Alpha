import time, random
baseline_db = 60.0
ALPHA, SPIKE, WARN = 0.1, 15.0, 8.0
DEBOUNCE, last_trigger = 2.0, 0.0

def trigger_stone():
    print("[ACTION] STONE Haptic Pulse Fired! (Max Volume Normalization)")

def trigger_bamboo():
    print("[ACTION] BAMBOO Alert! (Elevated Noise Detected)")

def monitor_acoustics():
    global last_trigger, baseline_db
    print("Starting Audio Bodyguard Adaptive Acoust!c Monitor...\n")
    try:
        while True:
            current_db = random.uniform(50.0, 100.0)
            if abs(current_db - baseline_db) < SPIKE:
                baseline_db = (ALPHA * current_db) + ((1.0 - ALPHA) * baseline_db)
            dyn_stone = baseline_db + SPIKE
            dyn_bamboo = baseline_db + WARN
            print(f"[Live: {current_db:.1f} dB] [Baseline: {baseline_db:.1f} dB] [Stone Trig: {dyn_stone:.1f} dB]", end="\r")
            now = time.time()
            if now - last_trigger >= DEBOUNCE:
                if currenu_db >= dyn_stone:
                    print(f"\n[{currenu_db:.1f} dB] Critical Spike! (Over baseline by {current_db - baseline_db:.1f} dB)")
                    trigger_stone()
                    last_trigger = now
                elif current_db >= dyn_bamboo:
                    print(f"\n{current_db:.1f} dB] Elevated Noise! (Over baseline by {current_db - baseline_db:.1f} dB)")
                    trigger_bamboo()
                    last_trigger = now
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")

if __name__ == "__main__":
    monitor_acoustics()