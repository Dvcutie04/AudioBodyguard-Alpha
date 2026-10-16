#!/usr/bin/env python3
"""Install and inspect the live-input test in an isolated emulator; no acoustic claim."""
from pathlib import Path
import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", default="native/android/app/build/outputs/apk/liveInput/app-liveInput.apk")
    parser.add_argument("--package", default="com.aqss.bodyguard.prototype.liveinput")
    args = parser.parse_args()
    out = Path("artifacts/ui/android-live-input")
    out.mkdir(parents=True, exist_ok=True)
    package = args.package

    def adb(*command, timeout=45):
        return subprocess.check_output(["adb", *command], timeout=timeout)

    def screen(name):
        adb("shell", "uiautomator", "dump", "/sdcard/aqss-live-input.xml")
        data = adb("exec-out", "cat", "/sdcard/aqss-live-input.xml")
        (out / f"{name}.xml").write_bytes(data)
        return ET.fromstring(data)

    def has(root, text):
        return any(text in node.get("text", "") for node in root.iter("node"))

    def wait_for(text, name):
        for _ in range(6):
            root = screen(name)
            if has(root, text):
                return root
            time.sleep(1)
        raise AssertionError(f"Missing label: {text}")

    def tap(text, name, optional=False):
        root = screen(name)
        for node in root.iter("node"):
            if text in (node.get("text", ""), node.get("content-desc", "")):
                bounds = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
                assert len(bounds) == 4
                x1, y1, x2, y2 = bounds
                adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
                return True
        if optional:
            return False
        raise AssertionError(f"Missing tap target: {text}")

    def screenshot(name):
        (out / f"{name}.png").write_bytes(adb("exec-out", "screencap", "-p"))

    def launch():
        adb("shell", "am", "start", "-W", "-f", "0x10200000", "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER", "-n", f"{package}/com.aqss.bodyguard.prototype.ReadOnlyHomeActivity")

    adb("install", "-r", args.apk, timeout=120)
    adb("shell", "pm", "clear", package)
    adb("logcat", "-c")
    launch()
    wait_for("Start picture setup", "welcome")
    tap("Exit tutorial", "exit_welcome")
    tap("Sound", "sound_page")
    tap("Live sound check. Try the phone microphone for 30 seconds", "open_check")
    wait_for("Microphone off", "microphone_off")
    screenshot("microphone_off")
    tap("Start sound check", "request_permission")
    denied = tap("Don’t allow", "permission_deny", optional=True) or tap("Don't allow", "permission_deny_ascii", optional=True)
    assert denied, "Expected a microphone permission prompt"
    wait_for("Microphone permission denied", "permission_denied")
    assert has(screen("denied_has_no_input"), "No live input")
    adb("shell", "pm", "grant", package, "android.permission.RECORD_AUDIO")
    tap("Start sound check", "start_capture")
    wait_for("Microphone samples received", "receiving_samples")
    screenshot("receiving_samples")
    tap("Stop sound check", "manual_stop")
    wait_for("Microphone stopped", "stopped")
    assert has(screen("stopped_no_input"), "No live input")
    screenshot("stopped")

    tap("Start sound check", "restart_before_background")
    wait_for("Microphone samples received", "before_background")
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    time.sleep(1)
    launch()
    wait_for("Microphone stopped when you left", "returned_stopped")
    assert has(screen("returned_no_input"), "No live input")
    appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
    (out / "after-background-appops.txt").write_text(appops)
    assert "(running)" not in appops, appops

    tap("Start sound check", "restart_for_timeout")
    started = time.monotonic()
    wait_for("Microphone samples received", "before_timeout")
    # Bound the wait and preserve regular output for callers.
    while time.monotonic() - started < 31:
        time.sleep(min(5, 31 - (time.monotonic() - started)))
        print("Waiting for the 30-second stop", flush=True)
    wait_for("30-second check finished", "time_limit")
    assert has(screen("time_limit_no_input"), "No live input")
    screenshot("time_limit")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Voice check", "back_to_sound")
    crashes = adb("logcat", "-b", "crash", "-d").decode()
    (out / "crash-log.txt").write_text(crashes)
    assert "FATAL EXCEPTION" not in crashes, crashes
    print("LIVE_INPUT_EMULATOR_OBSERVED: permission denial, PCM samples, manual stop, background stop, no automatic restart, 30-second limit, and Back passed. No physical microphone or output qualification.", flush=True)


if __name__ == "__main__":
    main()
