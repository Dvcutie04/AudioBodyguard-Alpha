import time
import random
from send_home import dispatch_trigger

def listen_and_process():
    print("[DSP LISTENER] Audio Bodyguard monitoring active... Press Ctrl+C to stop.")
    try:
        while True:
            # Simulate live sampling from mic array around target 18kHz band
            simulated_pulse = [random.uniform(17950.0, 18050.0) for _ in range(4)]
            print(f"\n[AUDIO CAPTURE] Captured Frame: {[round(x,1) for x in simulated_pulse]}")
            dispatch_trigger(simulated_pulse)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[DSP LISTENER] Monitoring stopped.")

if __name__ == "__main__":
    listen_and_process()
