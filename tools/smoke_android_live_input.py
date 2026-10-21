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

    def scroll_meter(name, down):
        root, _ = screen(name)
        bounds = next(n.get("bounds") for n in root.iter("node") if n.get("bounds"))
        x0, y0, x1, y1 = map(int, re.findall(r"-?\d+", bounds))
        x = (x0 + x1) // 2
        high, low = int(y0 + (y1-y0)*0.35), int(y0 + (y1-y0)*0.75)
        adb("shell", "input", "swipe", str(x), str(low if down else high),
            str(x), str(high if down else low), "350")

    def open_recaps(name):
        for attempt in range(5):
            root, _ = screen(f"{name}-find-{attempt}")
            if has(root, "Recent sound checks"):
                tap("Recent sound checks", name)
                return
            scroll_meter(f"{name}-scroll-{attempt}", down=True)
        raise AssertionError("Recent sound checks is not reachable in the meter scroll view")

    def close_recaps(name):
        tap("Close", name)
        wait_for("Start sound check", name + "-back-in-meter")
        for attempt in range(3):
            scroll_meter(f"{name}-top-{attempt}", down=False)

    def screenshot(name):
        (out / f"{name}.png").write_bytes(adb("exec-out", "screencap", "-p"))

    def launch():
        adb("shell", "am", "start", "-W", "-f", "0x10200000", "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER", "-n", f"{package}/com.aqss.bodyguard.prototype.ReadOnlyHomeActivity")

    adb("install", "-t", "-r", args.probe_apk, timeout=120)
    # Establish a responsive system launcher before AQSS is installed/launched.
    # A boot-time OS ANR is not an AQSS observation. Preserve it, allow at most
    # two exact known-system-dialog actions, then require fresh launcher roots.
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    stable = 0
    recovered = 0
    for attempt in range(20):
        root, _ = screen(f"boot-preflight-{attempt}")
        nodes = list(root.iter("node"))
        titles = {n.get("text", "") for n in nodes if n.get("package") == "android"}
        known_launcher = bool(titles & {"Quickstep isn't responding", "Pixel Launcher isn't responding"})
        known_system = "System UI isn't responding" in titles
        if known_launcher or known_system:
            screenshot(f"boot-system-dialog-{recovered}")
            assert recovered < 2, "System boot dialogs persisted after two recorded recovery actions"
            action = "Close app" if known_launcher else "Wait"
            _, clicked = screen(f"boot-recovery-{recovered}", click=action)
            assert clicked, "Known system boot dialog has no inspectable recovery control"
            recovered += 1; stable = 0
            adb("shell", "input", "keyevent", "KEYCODE_HOME")
        elif len(nodes) > 3 and any(n.get("package") in
                {"com.android.launcher3", "com.google.android.apps.nexuslauncher"} for n in nodes):
            stable += 1
            if stable == 3:
                break
        else:
            stable = 0
        time.sleep(2)
    else:
        screenshot("boot-preflight-unavailable")
        raise AssertionError("No stable system launcher before installing AQSS")
    (out / "boot-preflight.txt").write_text(
        f"Three fresh launcher observations; known boot-dialog recovery actions: {recovered}. "
        "No app dialog or post-launch ANR is suppressed.\n")
    print("SYSTEM_LAUNCHER_READY: three fresh observations before app installation", flush=True)
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
    # A synthetic image in this isolated emulator goes through the real system
    # picker, image decoder, bundled ML Kit and app review screen. Never inject
    # OCR text or a result directly into the app.
    def photo_fixture_case(fixture_name, display_name, case_prefix, expected):
        tap("Devices", f"{case_prefix}_devices_page")
        tap("TV photo setup. Read a model label or Network settings photo", "open_photo_check")
        wait_for_all(("No photo selected", "Brand: Not identified"), f"{case_prefix}_starts_empty")
        fixture = Path("native/ios/Tests/AQSSNativeFeedbackTests/Fixtures") / fixture_name
        inserted = adb("shell", "content", "insert", "--uri", "content://media/external_primary/images/media",
                       "--bind", f"_display_name:s:{display_name}", "--bind", "mime_type:s:image/png",
                       "--bind", "relative_path:s:Pictures/", "--bind", "is_pending:i:1").decode()
        (out / f"{case_prefix}-fixture-insert.txt").write_text(inserted)
        # The AOSP content insert command discards its returned URI. Query the exact
        # test row; absence or ambiguity fails rather than guessing an item ID.
        pending_match = r"android\:query-arg-match-pending:i:1"
        query = adb("shell", shlex.join(["content", "query", "--uri", "content://media/external_primary/images/media",
                    "--projection", "_id:_display_name:is_pending", "--extra", pending_match, "--where",
                    f"_display_name='{display_name}' AND relative_path='Pictures/'"])).decode()
        (out / f"{case_prefix}-fixture-query.txt").write_text(query)
        rows = re.findall(rf"^Row: \d+ _id=(\d+), _display_name={re.escape(display_name)}, is_pending=1$", query, re.MULTILINE)
        assert len(rows) == 1, "Expected one identifiable pending fixture in MediaStore"
        image_uri = "content://media/external_primary/images/media/" + rows[0]
        try:
            written = subprocess.run(["adb", "shell", "content", "write", "--uri", image_uri],
                                     input=fixture.read_bytes(), capture_output=True, timeout=45, check=True)
            (out / f"{case_prefix}-fixture-write.txt").write_bytes(written.stdout + written.stderr)
            assert adb("shell", "content", "read", "--uri", image_uri) == fixture.read_bytes(), "Imported image bytes differ"
            adb("shell", shlex.join(["content", "update", "--uri", image_uri, "--bind", "is_pending:i:0",
                "--extra", pending_match]))
            published = adb("shell", "content", "query", "--uri", image_uri, "--projection", "_id:_display_name:is_pending").decode()
            (out / f"{case_prefix}-fixture-published.txt").write_text(published)
            assert f"_id={rows[0]}, _display_name={display_name}, is_pending=0" in published, "Fixture is not published to the picker"
            tap("Choose a photo", f"{case_prefix}_choose")
            chosen = False
            for attempt in range(6):
                picker, _ = screen(f"{case_prefix}_picker_{attempt}")
                labels = {n.get(field, "") for n in picker.iter("node") for field in ("text", "content-desc")}
                if display_name in labels:
                    tap(display_name, f"{case_prefix}_pick_fixture"); chosen = True; break
                browse = next((s for s in ("Browse", "Browse…", "Browse...", "Browse files") if s in labels), None)
                if browse:
                    tap(browse, f"{case_prefix}_browse_{attempt}"); continue
                # On the stock single-photo picker, media cells expose their capture
                # date instead of a filename. Accept only one visible photo cell.
                cells = {s for s in labels if s.startswith("Photo taken on ") or s.startswith("Image taken on ")}
                if len(cells) == 1:
                    tap(cells.pop(), f"{case_prefix}_pick_single_fixture"); chosen = True; break
                time.sleep(1)
            assert chosen, "No unambiguous synthetic image in the observed system picker"
            wait_for_all(expected,
                         f"{case_prefix}_native_ocr_result")
            screenshot(f"{case_prefix}_native_ocr_result")
            for attempt in range(5):
                current, _ = screen(f"{case_prefix}_clear_find_{attempt}")
                if has(current, "Clear photo details"):
                    tap("Clear photo details", f"{case_prefix}_clear"); break
                scroll_meter(f"{case_prefix}_scroll_{attempt}", down=True)
            else:
                raise AssertionError("Clear photo details is unreachable")
            for attempt in range(3):
                scroll_meter(f"{case_prefix}_after_clear_top_{attempt}", down=False)
            wait_for_all(("No photo selected", "Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified"),
                         f"{case_prefix}_clear_empty")
            screenshot(f"{case_prefix}_clear_empty")
            tap("Choose a photo", f"{case_prefix}_choose_to_cancel")
            screen(f"{case_prefix}_picker_before_cancel")
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            wait_for_all(("No photo selected", "Brand: Not identified"), f"{case_prefix}_cancel_stays_empty")
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            wait_for("TV photo setup", f"{case_prefix}_close_returns_devices")
            tap("Home", f"{case_prefix}_back_home")
            wait_for("Connection not verified", f"{case_prefix}_did_not_connect")
        except Exception:
            screenshot(f"{case_prefix}_failure")
            raise
        finally:
            adb("shell", shlex.join(["content", "delete", "--uri", image_uri, "--extra", pending_match]))

    photo_fixture_case("tv-photo-labels.png", "aqss-tv-labels.png", "photo",
                       ("Brand: VIZIO", "Model: V505M-K09", "TV IP hint: 10.20.30.40", "Nothing is connected."))
    photo_fixture_case("tv-photo-text-limit.png", "aqss-tv-text-limit.png", "photo_limit",
                       ("Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified",
                        "Photo text could not be reviewed. Choose a closer photo of the model or IP address row."))

    tap("Sound", "sound_page")
    tap("Live sound check. Try the phone microphone for 30 seconds", "open_check")
    wait_for("Microphone off", "microphone_off")
    screenshot("microphone_off")
    tap("Start sound check", "request_permission")
    denied = tap("Don’t allow", "permission_deny", optional=True) or tap("Don't allow", "permission_deny_ascii", optional=True)
    assert denied, "Expected a microphone permission prompt"
    wait_for("Microphone permission denied", "permission_denied")
    wait_for_all(("Microphone permission denied", "No live input", "Start sound check"), "denied_has_no_input")
    open_recaps("denied_recaps")
    wait_for("No completed sound checks in this app session.", "denied_no_recap")
    screenshot("recaps_empty_after_denial")
    close_recaps("close_denied_recaps")
    adb("shell", "pm", "grant", package, "android.permission.RECORD_AUDIO")
    tap("Start sound check", "start_capture")
    wait_for("Microphone samples received", "receiving_samples")
    screenshot("receiving_samples")
    tap("Stop sound check", "manual_stop")
    wait_for("Microphone stopped", "stopped")
    wait_for_all(("Microphone stopped", "No live input", "Start sound check"), "stopped_no_input")
    screenshot("stopped")
    open_recaps("manual_recaps")
    wait_for_all(("Input samples observed", "Stopped by you"), "manual_recap_observed")
    screenshot("recaps_manual_stop")
    tap("Clear recaps", "clear_manual_recaps")
    wait_for("No completed sound checks in this app session.", "recaps_cleared")
    screenshot("recaps_cleared")
    close_recaps("close_cleared_recaps")


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
    screenshot("landscape_stopped")
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
    open_recaps("time_limit_recaps")
    wait_for_all(("Input samples observed", "30-second limit reached", "Stopped when the app lost focus"), "time_limit_and_left_recaps")
    screenshot("recaps_time_limit_and_focus")
    close_recaps("close_time_limit_recaps")

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
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Voice check", "back_before_recap_reopen")
    tap("Live sound check. Try the phone microphone for 30 seconds", "reopen_meter_for_recaps")
    open_recaps("recaps_after_reopen")
    wait_for_all(("Input samples observed", "Stopped by you"), "recaps_survive_navigation")
    screenshot("recaps_survive_navigation")
    close_recaps("close_before_process_stop")
    adb("shell", "am", "force-stop", package)
    launch()
    wait_for("Sound", "new_process_navigation")
    tap("Sound", "new_process_sound_tab")
    wait_for("Voice check", "new_process_sound_page")
    tap("Live sound check. Try the phone microphone for 30 seconds", "meter_new_process")
    open_recaps("recaps_new_process")
    wait_for("No completed sound checks in this app session.", "recaps_not_persisted")
    screenshot("recaps_new_process_empty")

    crashes = adb("logcat", "-b", "crash", "-d").decode()
    (out / "crash-log.txt").write_text(crashes)
    assert "FATAL EXCEPTION" not in crashes, crashes
    print("LIVE_INPUT_EMULATOR_OBSERVED: permission denial, PCM samples, manual stop, notification-shade focus loss, background stop, rotation stop, no automatic restart, 30-second limit, voice navigation/service attempt, meter reuse, bounded input recaps, Clear, navigation retention, empty recaps after process restart, synthetic-photo picker/ML Kit review, over-budget photo rejection, photo Clear/cancel and unverified connection passed. No physical microphone, real-photo accuracy or output qualification.", flush=True)


if __name__ == "__main__":
    main()
