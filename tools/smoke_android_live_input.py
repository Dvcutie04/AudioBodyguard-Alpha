#!/usr/bin/env python3
"""Install and inspect the live-input test in an isolated emulator; no acoustic claim."""
from pathlib import Path
import argparse
import base64
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", default="native/android/app/build/outputs/apk/liveInput/app-liveInput.apk")
    parser.add_argument("--package", default="com.aqss.bodyguard.prototype.liveinput")
    parser.add_argument("--probe-apk", default="native/android/uiprobe/build/outputs/apk/debug/uiprobe-debug.apk")
    args = parser.parse_args()
    out = Path("artifacts/ui/android-live-input")
    out.mkdir(parents=True, exist_ok=True)
    package = args.package

    def adb(*command, timeout=45):
        return subprocess.check_output(["adb", *command], timeout=timeout, stdin=subprocess.DEVNULL)

    def screen(name, click=None):
        for attempt in range(4):
            try:
                command = ["am", "instrument", "-w"]
                if click is not None:
                    command += ["-e", "click", click]
                output = adb("shell", shlex.join([*command, "com.aqss.bodyguard.uiprobe/.HierarchyProbe"])).decode()
                (out / f"{name}-probe-{attempt}.txt").write_text(output)
                encoded = re.search(r"^INSTRUMENTATION_RESULT: hierarchy=(.+)$", output, re.MULTILINE)
                if encoded is None:
                    raise ValueError("No hierarchy returned by the live snapshot observer")
                data = base64.b64decode(encoded.group(1).strip(), validate=True)
                root = ET.fromstring(data)
                if root.tag == "hierarchy" and root.find("node") is not None:
                    (out / f"{name}.xml").write_bytes(data)
                    return root, "INSTRUMENTATION_RESULT: clicked=true" in output
            except (ValueError, ET.ParseError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass
            print(f"UI hierarchy unavailable for {name}; bounded retry {attempt + 1}/4", flush=True)
            time.sleep(2)
        screenshot(f"{name}-missing-hierarchy")
        raise AssertionError(f"No valid UI hierarchy for {name} after four attempts")

    def has(root, text):
        return any(text in node.get("text", "") for node in root.iter("node"))

    def wait_for_all(texts, name):
        # Native layout may briefly return a nonempty but partial hierarchy.
        # Observe all required labels together rather than comparing two frames.
        for _ in range(6):
            root, _ = screen(name)
            if all(has(root, text) for text in texts):
                return root
            time.sleep(1)
        raise AssertionError(f"Missing simultaneous labels: {texts}")

    def wait_for(text, name):
        return wait_for_all((text,), name)

    def tap(text, name, optional=False):
        # A successful prior click can still be replacing the active hierarchy.
        # Retry only a rejected action against a newly retrieved root.
        for attempt in range(6):
            _, clicked = screen(f"{name}-{attempt}", click=text)
            if clicked:
                return True
            time.sleep(0.3)
        if optional:
            return False
        raise AssertionError(f"Missing tap target: {text}")

    def screenshot(name):
        (out / f"{name}.png").write_bytes(adb("exec-out", "screencap", "-p"))

    def launch():
        adb("shell", "am", "start", "-W", "-f", "0x10200000", "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER", "-n", f"{package}/com.aqss.bodyguard.prototype.ReadOnlyHomeActivity")

    adb("install", "-t", "-r", args.probe_apk, timeout=120)
    adb("install", "-r", args.apk, timeout=120)
    adb("shell", "pm", "clear", package)
    adb("logcat", "-c")
    recording = subprocess.Popen(["adb", "shell", "screenrecord", "--time-limit", "12", "/sdcard/aqss-opening.mp4"],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(0.4)
    launch()
    try:
        record_output = recording.communicate(timeout=20)[0]
    except subprocess.TimeoutExpired:
        recording.kill()
        recording.communicate()
        raise AssertionError("Opening-screen recording did not finish")
    (out / "opening-recording.txt").write_bytes(record_output)
    assert recording.returncode == 0, record_output.decode(errors="replace")
    adb("pull", "/sdcard/aqss-opening.mp4", str(out / "opening.mp4"))
    screenshot("after_opening")
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
    wait_for_all(("Microphone permission denied", "No live input", "Start sound check"), "denied_has_no_input")
    adb("shell", "pm", "grant", package, "android.permission.RECORD_AUDIO")
    tap("Start sound check", "start_capture")
    wait_for("Microphone samples received", "receiving_samples")
    screenshot("receiving_samples")
    tap("Stop sound check", "manual_stop")
    wait_for("Microphone stopped", "stopped")
    wait_for_all(("Microphone stopped", "No live input", "Start sound check"), "stopped_no_input")
    screenshot("stopped")

    tap("Start sound check", "restart_before_notification_shade")
    wait_for("Microphone samples received", "before_notification_shade")
    adb("shell", "cmd", "statusbar", "expand-notifications")
    time.sleep(1)
    adb("shell", "cmd", "statusbar", "collapse")
    wait_for("Microphone stopped when you left", "shade_returned_stopped")
    wait_for_all(("Microphone stopped when you left", "No live input", "Start sound check"), "shade_no_input")
    shade_appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
    (out / "after-shade-appops.txt").write_text(shade_appops)
    assert "(running)" not in shade_appops, shade_appops
    screenshot("shade_stopped")

    tap("Start sound check", "restart_before_background")
    wait_for("Microphone samples received", "before_background")
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    time.sleep(1)
    launch()
    wait_for("Microphone stopped when you left", "returned_stopped")
    wait_for_all(("Microphone stopped when you left", "No live input", "Start sound check"), "returned_no_input")
    appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
    (out / "after-background-appops.txt").write_text(appops)
    assert "(running)" not in appops, appops

    tap("Start sound check", "restart_before_rotation")
    wait_for("Microphone samples received", "before_rotation")
    adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
    adb("shell", "settings", "put", "system", "user_rotation", "1")
    wait_for("Microphone off", "rotated_stopped")
    wait_for_all(("Microphone off", "No live input", "Start sound check"), "rotation_no_input")
    adb("shell", "settings", "put", "system", "user_rotation", "0")
    wait_for("Microphone off", "portrait_stopped")

    tap("Start sound check", "restart_for_timeout")
    started = time.monotonic()
    wait_for("Microphone samples received", "before_timeout")
    # Bound the wait and preserve regular output for callers.
    while time.monotonic() - started < 31:
        time.sleep(min(5, 31 - (time.monotonic() - started)))
        print("Waiting for the 30-second stop", flush=True)
    wait_for("30-second check finished", "time_limit")
    wait_for_all(("30-second check finished", "No live input", "Start sound check"), "time_limit_no_input")
    screenshot("time_limit")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Voice check", "back_to_sound")
    tap("Voice check. See microphone activity and recognized words", "open_voice_check")
    wait_for("Microphone off", "voice_starts_off")
    wait_for_all(("Microphone off", "No words recognized yet", "Start voice check"), "voice_no_words")
    screenshot("voice_starts_off")
    # This host may have no on-device speech model. Do not synthesize speech or
    # claim a service trial from a navigation result.
    tap("Start voice check", "attempt_voice_service")
    time.sleep(1)
    voice, _ = screen("voice_service_attempt")
    screenshot("voice_service_attempt")
    (out / "voice-service-observation.txt").write_text(
        "\n".join(n.get("text", "") for n in voice.iter("node") if n.get("text")))
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    time.sleep(1)
    launch()
    wait_for("Start voice check", "voice_background_requires_start")
    wait_for_all(("No words recognized yet", "Start voice check"), "voice_words_cleared")
    voice_appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
    (out / "after-voice-background-appops.txt").write_text(voice_appops)
    assert "(running)" not in voice_appops, voice_appops
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Live sound check", "voice_closed_back_to_sound")
    tap("Live sound check. Try the phone microphone for 30 seconds", "meter_after_voice")
    tap("Start sound check", "meter_start_after_voice")
    wait_for("Microphone samples received", "meter_usable_after_voice")
    tap("Stop sound check", "stop_meter_after_voice")
    wait_for("Microphone stopped", "meter_after_voice_stopped")
    screenshot("meter_usable_after_voice")
    crashes = adb("logcat", "-b", "crash", "-d").decode()
    (out / "crash-log.txt").write_text(crashes)
    assert "FATAL EXCEPTION" not in crashes, crashes
    print("LIVE_INPUT_EMULATOR_OBSERVED: permission denial, PCM samples, manual stop, notification-shade focus loss, background stop, rotation stop, no automatic restart, 30-second limit, voice navigation/service attempt, and meter reuse passed. No physical microphone or output qualification.", flush=True)


if __name__ == "__main__":
    main()
