#!/usr/bin/env python3
"""Install and inspect the live-input test in an isolated emulator; no acoustic claim."""
from pathlib import Path
import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import os
import re
import shlex
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from android_frame_evidence import compare_frames


@contextmanager
def _loopback_tv_service():
    fixture = Path(__file__).resolve().parents[1] / "native/android/src/test/resources/tv-loopback-fixture.p12.fixture"
    with tempfile.TemporaryDirectory() as temporary:
        bundle = Path(temporary) / "fixture.pem"
        subprocess.run(["openssl", "pkcs12", "-in", str(fixture), "-passin", "pass:fixture-only",
                        "-noenc", "-out", str(bundle)], check=True, timeout=15, capture_output=True)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(bundle)
        certificate = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                                bundle.read_text(), re.DOTALL)
        assert certificate is not None
        expected = hashlib.sha256(ssl.PEM_cert_to_DER_cert(certificate.group())).hexdigest()
        with socket.socket() as unused_port, socket.socket() as server:
            unused_port.bind(("127.0.0.1", 7345))
            server.bind(("127.0.0.1", 9000))
            server.listen(2)
            server.settimeout(0.2)
            done = threading.Event()
            handshakes = []

            def serve():
                while not done.is_set():
                    try:
                        peer, _ = server.accept()
                    except TimeoutError:
                        continue
                    with peer:
                        peer.settimeout(4)
                        try:
                            with context.wrap_socket(peer, server_side=True):
                                handshakes.append("accepted")
                        except OSError:
                            handshakes.append("ended")

            worker = threading.Thread(target=serve, name="tv-loopback-fixture", daemon=True)
            worker.start()
            try:
                yield expected
            finally:
                done.set()
                worker.join(timeout=5)
            assert not worker.is_alive()
            assert handshakes == ["ended", "ended"], handshakes


def _visible_share_target(root):
    targets = []

    def visit(node, clip=None):
        values = re.findall(r"-?\d+", node.get("bounds", ""))
        if len(values) != 4:
            return
        bounds = tuple(map(int, values))
        visible = bounds if clip is None else (max(bounds[0], clip[0]), max(bounds[1], clip[1]),
                                               min(bounds[2], clip[2]), min(bounds[3], clip[3]))
        if node.get("text") == "Build details test" and node.get("package") == "com.android.intentresolver":
            targets.append(bounds if visible == bounds and bounds[0] < bounds[2] and bounds[1] < bounds[3] else None)
        for child in node:
            visit(child, visible)

    for node in root:
        visit(node)
    return targets[0] if len(targets) == 1 else None


def _support_report_anchor(root):
    anchors = [node.get("bounds") for node in root.iter("node")
               if node.get("content-desc") == "About Private support report"]
    return anchors[0] if len(anchors) == 1 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samsung-setup-only", action="store_true")
    parser.add_argument("--output-inventory-only", action="store_true")
    parser.add_argument("--output-report-only", action="store_true")
    parser.add_argument("--test-setup-only", action="store_true")
    parser.add_argument("--setup-output-report-only", action="store_true")
    parser.add_argument("--tv-guides-only", action="store_true")
    parser.add_argument("--style-only", action="store_true")
    parser.add_argument("--voice-fixture-only", action="store_true")
    parser.add_argument("--tv-certificate-fixture", action="store_true")
    parser.add_argument("--apk", default="native/android/app/build/outputs/apk/liveInput/app-liveInput.apk")
    parser.add_argument("--package", default="com.aqss.bodyguard.prototype.liveinput")
    parser.add_argument("--probe-apk", default="native/android/uiprobe/build/outputs/apk/debug/uiprobe-debug.apk")
    parser.add_argument("--share-receiver-apk", default="native/android/sharereceiver/build/outputs/apk/debug/sharereceiver-debug.apk")
    args = parser.parse_args()
    if args.tv_certificate_fixture and not args.style_only:
        parser.error("--tv-certificate-fixture requires --style-only")
    out = Path("artifacts/ui/android-live-input")
    out.mkdir(parents=True, exist_ok=True)
    package = args.package

    def adb(*command, timeout=45):
        return subprocess.check_output(["adb", *command], timeout=timeout, stdin=subprocess.DEVNULL)

    def frame_snapshot(name):
        try:
            data = adb("shell", "dumpsys", "gfxinfo", package, "framestats", timeout=10)
            if len(data) > 2_097_152:
                data = b"FRAME_SNAPSHOT_UNAVAILABLE: output exceeded the 2 MiB capture limit\n"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            data = f"FRAME_SNAPSHOT_UNAVAILABLE: {type(error).__name__}\n".encode()
        (out / (name + ".txt")).write_bytes(data)
        return data.decode(errors="replace")

    def complete_frame_evidence(name, before):
        after = frame_snapshot(name + "_after")
        report = compare_frames(before, after)
        report.update({
            "transition": name,
            "source_commit": os.environ.get("GITHUB_SHA", "Unavailable"),
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID", "Unavailable"),
            "workflow_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "Unavailable"),
            "installed_build": {"application_id": package, "version": version, "build": build},
            "collection_timeout_s": 10,
            "maximum_snapshot_bytes": 2_097_152,
        })
        (out / (name + ".json")).write_text(json.dumps(report, sort_keys=True))
        print(f"RECAP_RENDERER_EVIDENCE: {name}; {report['frame_count']} attributed frames; "
              f"timing qualified={report['timing_qualified']}; hosted renderer only", flush=True)

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

    def wait_for_all(texts, name, attempts=6):
        # Native layout may briefly return a nonempty but partial hierarchy.
        # Observe all required labels together rather than comparing two frames.
        for _ in range(attempts):
            root, _ = screen(name)
            if all(has(root, text) for text in texts):
                return root
            time.sleep(1)
        raise AssertionError(f"Missing simultaneous labels: {texts}")

    def wait_for(text, name):
        return wait_for_all((text,), name)

    def wait_for_voice_permission_idle(permission_text, name):
        texts = (permission_text, "No live microphone samples", "No words recognized yet", "Start voice check")
        for _ in range(6):
            root, _ = screen(name)
            if all(has(root, text) for text in texts):
                return root
            scroller = next((n for n in root.iter("node") if n.get("class") == "android.widget.ScrollView"), None)
            if scroller is not None and (not has(root, "No words recognized yet") or not has(root, permission_text)):
                x0, y0, x1, y1 = map(int, re.findall(r"-?\d+", scroller.get("bounds")))
                down = not has(root, "No words recognized yet")
                x = (x0 + x1) // 2
                y = int(y0 + (y1-y0) * (0.65 if down else 0.35))
                distance = max(1, min(240, (y1-y0) // 6))
                adb("shell", "input", "swipe", str(x), str(y), str(x), str(y-distance if down else y+distance), "2000")
            else:
                time.sleep(1)
        raise AssertionError(f"Missing simultaneous Voice permission labels after bounded scrolling: {texts}")

    def tap_direct(text, name, optional=False):
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

    def tap(text, name, optional=False):
        # Secondary destinations now live in the same contextual help menus
        # users open. Exercise those controls before reaching the real screen.
        routes = {
            "Build details": ("? More settings", "Build details"),
            "Advanced Settings": ("? More settings", "Jump to Advanced Settings"),
            "Test setup. Record the two-phone test arrangement": ("? More sound tools", "Jump to Test setup"),
            "Output inventory. Check this phone’s available audio outputs": ("? More sound tools", "Jump to Output inventory"),
            "TV photo setup. Read a model label or Network settings photo": ("? Device help", "TV photo setup. Read a model label or settings photo"),
            "Show photo details": ("? Photo help", "Show photo details"),
        }
        if text not in routes:
            return tap_direct(text, name, optional)
        menu, choice = routes[text]
        if tap_direct(choice, name + "_choice", optional=True):
            return True
        if not tap_direct(menu, name + "_help", optional=optional):
            return False
        return tap_direct(choice, name, optional)

    def wait_photo_fields(texts, name, attempts=6):
        # Unknown brand rows are intentionally hidden; model/IP details require
        # Photo help. Still reject a stale identified brand after replacement.
        visible = tuple(text for text in texts if text != "Brand: Not identified")
        root = wait_for_all(visible, name, attempts)
        if "Brand: Not identified" in texts:
            assert not any(n.get("text", "").startswith("Brand:") for n in root.iter("node")), "Unknown photo must not retain a visible brand"
        return root

    def select_share_receiver(name):
        previous = None
        for attempt in range(6):
            root, _ = screen(f"{name}_settle_{attempt}")
            bounds = _visible_share_target(root)
            if bounds is not None and bounds == previous:
                # Exercise the actual native tile. An accepted accessibility
                # ancestor action did not launch the receiver in retained 0.32
                # evidence; keep the exact receiver/receipt assertions below.
                x0, y0, x1, y1 = bounds
                adb("shell", "input", "tap", str((x0 + x1) // 2), str((y0 + y1) // 2))
                return
            previous = bounds
            time.sleep(1)
        screenshot(name + "_unsettled")
        raise AssertionError("Native share receiver target did not settle fully inside its ancestor viewports")

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
            if tap_direct("[?] What does this show?", f"{name}_help_{attempt}", optional=True):
                tap_direct("Jump to recent sound checks", name)
                return
            scroll_meter(f"{name}_find_help_{attempt}", down=True)
        raise AssertionError("Recent sound checks is not reachable through sound-check help")

    def close_recaps(name):
        tap("Close", name)
        wait_for("Start sound check", name + "-back-in-meter")
        for attempt in range(3):
            scroll_meter(f"{name}-top-{attempt}", down=False)

    def review_insights_recaps(name, expected, clear=False, return_sound=True, report=False):
        tap("Insights", name + "_tab")
        wait_for("Audio trends", name + "_page")
        tap("Recent sound checks", name + "_open")
        root = wait_for_all((*expected, "Kept in memory; cleared when this app process ends."), name)
        assert not has(root, "Start sound check") and not has(root, "Stop sound check"), "Insights must not open the microphone tool"
        screenshot(name)
        activities = adb("shell", "dumpsys", "activity", "activities").decode()
        (out / (name + "-activities.txt")).write_text(activities)
        foreground = re.search(r"topResumedActivity=[^\n]*", activities)
        assert foreground and "ReadOnlyHomeActivity" in foreground.group(), "Insights must stay in the home Activity"
        appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
        (out / (name + "-appops.txt")).write_text(appops)
        assert "(running)" not in appops, appops
        if report:
            opening_frames = name + "_report_open_frames"
            before_open = frame_snapshot(opening_frames + "_before")
            tap("Review support report", name + "_review_report")
            metadata = f"Audio Bodyguard\nPlatform: Android\nVersion: {version}\nBuild: {build}"
            checks = ("Check 1: Input samples observed\nStopped by you"
                      if "Input samples observed" in expected else "No completed sound checks in this app session.")
            reviewed = metadata + "\n\nRecent sound checks (this app session)\n" + checks + "\n\nInput observations only; not proof of sound safety, protection or TV control."
            root = wait_for_all((reviewed, "Private support report", "Include recent sound checks", "Share support report"), name + "_report_preview")
            assert not has(root, "Build details test"), "Review must not open native sharing"
            complete_frame_evidence(opening_frames, before_open)
            tap("Include recent sound checks", name + "_report_exclude")
            root = wait_for(metadata, name + "_report_build_only")
            assert not has(root, "Recent sound checks (this app session)"), "Excluded recaps must leave the shared preview"
            tap("Include recent sound checks", name + "_report_restore")
            wait_for(reviewed, name + "_report_restored")
            screenshot(name + "_report_preview")
            if "Input samples observed" in expected:
                previous = adb("shell", "run-as", receiver, "cat", receiver_file)
                tap("Share support report", name + "_report_share")
                chooser = wait_for("Build details test", name + "_report_chooser")
                assert any(n.get("package") == "com.android.intentresolver" for n in chooser.iter("node"))
                adb("shell", "input", "keyevent", "KEYCODE_BACK")
                wait_for_all((reviewed, "Share support report"), name + "_report_cancel_return")
                assert adb("shell", "run-as", receiver, "cat", receiver_file) == previous
                tap("Share support report", name + "_report_reshare")
                select_share_receiver(name + "_report_receiver")
                received = wait_for_all((reviewed, "Return to Build details"), name + "_report_received")
                assert any(n.get("package") == receiver for n in received.iter("node"))
                raw = adb("shell", "run-as", receiver, "cat", receiver_file)
                item = json.loads(raw.decode())
                assert item["action"] == "android.intent.action.SEND" and item["type"] == "text/plain", item
                assert item["text"] == reviewed and item["data"] is None and item["has_stream"] is False, item
                assert all(c["text"] == reviewed and c["uri"] is None and c["has_intent"] is False for c in item["clips"]), item
                (out / (name + "_report_receipt.json")).write_text(json.dumps(item, sort_keys=True))
                tap("Return to Build details", name + "_report_receiver_return")
                wait_for_all((reviewed, "Share support report"), name + "_report_returned_preview")
            tap("Include recent sound checks", name + "_report_leave_excluded")
            wait_for(metadata, name + "_report_excluded_before_back")
            returning_frames = name + "_report_back_frames"
            before_back = frame_snapshot(returning_frames + "_before")
            tap("Back", name + "_report_back")
            wait_for_all((*expected, "Review support report"), name + "_report_returned_recaps")
            complete_frame_evidence(returning_frames, before_back)
            tap("Review support report", name + "_report_reopen")
            wait_for(reviewed, name + "_report_fresh_snapshot")
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            wait_for_all((*expected, "Review support report"), name + "_report_system_back_recaps")
            appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
            (out / (name + "_report-appops.txt")).write_text(appops)
            assert "(running)" not in appops, appops
        if clear:
            tap("Clear recaps", name + "_clear")
            wait_for("No completed sound checks in this app session.", name + "_cleared")
            screenshot(name + "_cleared")
        tap("Close", name + "_close")
        wait_for_all(("Audio trends", "Recent sound checks", "No measurements yet"), name + "_returned")
        screenshot(name + "_returned")
        if return_sound:
            tap("Sound", name + "_sound")
            wait_for("Voice check", name + "_back_in_sound")

    def screenshot(name):
        (out / f"{name}.png").write_bytes(adb("exec-out", "screencap", "-p"))

    def launch():
        adb("shell", "am", "start", "-W", "-f", "0x10200000", "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER", "-n", f"{package}/com.aqss.bodyguard.prototype.ReadOnlyHomeActivity")

    adb("install", "-t", "-r", args.probe_apk, timeout=120)
    adb("install", "-t", "-r", args.share_receiver_apk, timeout=120)
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
    # Test APK reads actual Android on-device service availability without
    # opening a microphone, starting recognition or injecting a transcript.
    if args.voice_fixture_only:
        probe = adb("shell", "am", "instrument", "-w", "-r",
                    "com.aqss.bodyguard.uiprobe/.SpeechServiceAvailabilityProbe",
                    timeout=60).decode(errors="replace")
        (out / "voice-os-recognizer-service.txt").write_text(probe)
        for service_line in probe.splitlines():
            if "AQSS_V2_SERVICE_PROBE=" in service_line:
                print(service_line.strip(), flush=True)
        assert "AQSS_V2_SERVICE_PROBE=" in probe and "INSTRUMENTATION_CODE: -1" in probe, (
            "Android service query failed; do not classify missing evidence as available", probe)
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
    installed = adb("shell", "dumpsys", "package", package).decode()
    versions = re.findall(r"^\s*versionName=(.+)$", installed, re.MULTILINE)
    builds = re.findall(r"^\s*versionCode=(\d+)\b", installed, re.MULTILINE)
    assert len(versions) == len(builds) == 1, "Require unambiguous installed package metadata"
    version, build = versions[0].strip(), builds[0]
    (out / "installed-build-identity.json").write_text(
        json.dumps({"application_id": package, "version": version, "build": build}, sort_keys=True))
    if args.voice_fixture_only:
        # Exercise the two real native buttons, not a fake recognizer response.
        wait_for("Connection not verified", "voice_fixture_home")
        tap("Sound", "voice_fixture_open_sound")
        tap("Voice check. See microphone activity and recognized words", "voice_fixture_open")
        wait_for_all(("Microphone off", "No words recognized yet", "Start voice check"),
                     "voice_fixture_no_capture")
        instructions = wait_for("Tap Start, then say “Audio Bodyguard, skip intro” or “Audio Bodyguard, skip recap.”", "voice_fixture_new_commands")
        assert not has(instructions, "Make the TV quieter"), "Voice setup must not suggest unsupported TV volume control"

        def move_voice_view(name, up):
            # Android's accessibility hierarchy contains only visible children.
            root, _ = screen(name)
            scroller = next((n for n in root.iter("node")
                             if n.get("class") == "android.widget.ScrollView"), None)
            if scroller is None:
                time.sleep(0.3)
                return
            values = re.findall(r"-?\d+", scroller.get("bounds", ""))
            assert len(values) == 4, "Voice viewport must have four screen bounds"
            x0, y0, x1, y1 = map(int, values)
            assert x1 > x0 and y1-y0 >= 100, "Voice viewport must be scrollable"
            x = (x0 + x1) // 2
            start = int(y0 + (y1-y0) * (0.3 if up else 0.72))
            end = int(y0 + (y1-y0) * (0.72 if up else 0.3))
            adb("shell", "input", "swipe", str(x), str(start), str(x), str(end), "350")

        def voice_tap(text, name, up=False):
            # Search both scroll directions, but never repeat an action after a
            # successful click. The local video section expands the same view.
            for direction in (up, not up):
                for attempt in range(8):
                    _, clicked = screen(f"{name}-{direction}-{attempt}", click=text)
                    if clicked:
                        return
                    move_voice_view(f"{name}_{direction}_scroll_{attempt}", direction)
            raise AssertionError("Owned test-player button is not reachable: " + text)

        def voice_find(text, name, up=False):
            for direction in (up, not up):
                for attempt in range(8):
                    root, _ = screen(f"{name}-{direction}-{attempt}")
                    if has(root, text):
                        return root
                    move_voice_view(f"{name}_{direction}_scroll_{attempt}", direction)
            raise AssertionError("Owned test-player text missing after bounded scroll: " + text)

        def check_visible_button(root, text, expected_enabled):
            matches = [n for n in root.iter("node")
                       if n.get("class") == "android.widget.Button" and
                       n.get("text", "").casefold() == text.casefold()]
            assert len(matches) == 1, (text, "expected one VISIBLE authored button", len(matches))
            actual = matches[0].get("enabled")
            assert actual == str(expected_enabled).lower(), (text, expected_enabled, actual)

        # One real Intro button click must disable only that authored control.
        voice_tap("Skip Intro", "voice_fixture_press_intro")
        root = voice_find("Test player: Skip Intro button activated", "voice_fixture_intro_state", up=True)
        check_visible_button(root, "Skip Intro", False)
        screenshot("voice_fixture_intro_activated")

        # The still-available Recap button lives BELOW the narrow viewport;
        # search via real bounded scrolling, rather than treating absence from
        # a single visible accessibility root as a disabled/missing control.
        voice_tap("Skip Recap", "voice_fixture_press_recap")
        root = voice_find("Skip Recap", "voice_fixture_recap_button")
        check_visible_button(root, "Skip Recap", False)
        root = voice_find("Test player: Skip Recap button activated",
                          "voice_fixture_recap_state", up=True)
        screenshot("voice_fixture_recap_activated")

        # Reset should re-enable BOTH independent authored buttons.
        voice_tap("Reset test player", "voice_fixture_reset_buttons")
        root = voice_find("Test player ready — nothing connected",
                          "voice_fixture_reset_status", up=True)
        root = voice_find("Skip Intro", "voice_fixture_intro_restored")
        check_visible_button(root, "Skip Intro", True)
        root = voice_find("Skip Recap", "voice_fixture_recap_restored")
        check_visible_button(root, "Skip Recap", True)
        screenshot("voice_fixture_both_restored")

        # Exercise the actual bundled video decoder/player and observe its
        # independently read currentPosition after each section-specific seek.
        # No fake transcript, microphone, or third-party playback is involved.
        voice_tap("? Local video trial", "local_video_open")
        voice_tap("Prepare intro video", "local_video_prepare_intro")
        voice_find("Local video: intro ready at 0s", "local_video_intro_staged", up=True)
        voice_tap("Skip Intro", "local_video_intro_seek", up=True)
        voice_find("Local video observed: intro ends at 2s",
                   "local_video_intro_readback", up=True)
        screenshot("local_video_intro_observed")
        voice_tap("Reset test player", "local_video_reset", up=True)
        voice_find("Local video not prepared", "local_video_reset_confirm", up=True)
        voice_tap("Prepare recap video", "local_video_prepare_recap")
        voice_find("Local video: recap ready at 4s", "local_video_recap_staged", up=True)
        voice_tap("Skip Recap", "local_video_recap_seek", up=True)
        voice_find("Local video observed: recap ends at 6s",
                   "local_video_recap_readback", up=True)
        screenshot("local_video_recap_observed")

        # Emulator/debug-only final TEXT goes through OwnedVoiceSkipGate and the
        # same MediaPlayer handler as the real controls. No recognizer or mic.
        voice_tap("Reset test player", "text_fixture_intro_reset", up=True)
        voice_tap("Prepare intro video", "text_fixture_intro_prepare")
        voice_find("Local video: intro ready at 0s", "text_fixture_intro_ready", up=True)
        voice_tap("Fixture final Recap text (no audio)", "text_fixture_wrong_recap")
        voice_find("Fixture final text refused; no additional player action",
                   "text_fixture_wrong_recap_refusal", up=True)
        intro_available = voice_find("Skip Intro", "text_fixture_intro_still_available")
        check_visible_button(intro_available, "Skip Intro", True)
        voice_tap("Fixture final Intro text (no audio)", "text_fixture_intro_request")
        voice_find("Local video observed: intro ends at 2s",
                   "text_fixture_intro_observed", up=True)
        voice_tap("Fixture final Intro text (no audio)", "text_fixture_intro_duplicate")
        voice_find("Fixture final text refused; no additional player action",
                   "text_fixture_intro_duplicate_refused", up=True)
        voice_find("Local video observed: intro ends at 2s",
                   "text_fixture_intro_readback_retained", up=True)
        screenshot("text_fixture_intro_once_observed")

        voice_tap("Reset test player", "text_fixture_recap_reset", up=True)
        voice_tap("Prepare recap video", "text_fixture_recap_prepare")
        voice_find("Local video: recap ready at 4s", "text_fixture_recap_ready", up=True)
        voice_tap("Fixture final Intro text (no audio)", "text_fixture_wrong_intro")
        voice_find("Fixture final text refused; no additional player action",
                   "text_fixture_wrong_intro_refusal", up=True)
        recap_available = voice_find("Skip Recap", "text_fixture_recap_still_available")
        check_visible_button(recap_available, "Skip Recap", True)
        voice_tap("Fixture final Recap text (no audio)", "text_fixture_recap_request")
        voice_find("Local video observed: recap ends at 6s",
                   "text_fixture_recap_observed", up=True)
        voice_tap("Fixture final Recap text (no audio)", "text_fixture_recap_duplicate")
        voice_find("Fixture final text refused; no additional player action",
                   "text_fixture_recap_duplicate_refused", up=True)
        voice_find("Local video observed: recap ends at 6s",
                   "text_fixture_recap_readback_retained", up=True)
        screenshot("text_fixture_recap_once_observed")
        print("VOICE_OWNED_FINAL_TEXT_FIXTURE_PASS: emulator supplied text -> gate -> MediaPlayer readback; OS audio NONE", flush=True)

        # A canceled synthetic final-text run cannot seek an already prepared
        # real MediaPlayer. Keep the current playhead and control enabled.
        for segment, ready, phrase in (
            ("intro", "Local video: intro ready at 0s", "Intro"),
            ("recap", "Local video: recap ready at 4s", "Recap"),
        ):
            voice_tap("Reset test player", f"cancel_{segment}_reset", up=True)
            voice_find("Local video not prepared", f"cancel_{segment}_off", up=True)
            voice_tap(f"Prepare {segment} video", f"cancel_{segment}_prepare")
            voice_find(ready, f"cancel_{segment}_ready", up=True)
            voice_tap("Fixture cancel final text (no audio)", f"cancel_{segment}_run")
            voice_find("Fixture final text canceled; no audio", f"cancel_{segment}_status", up=True)
            voice_tap(f"Fixture final {phrase} text (no audio)", f"cancel_{segment}_late")
            voice_find(ready, f"cancel_{segment}_position_unchanged", up=True)
            voice_find("Fixture final text canceled; no audio", f"cancel_{segment}_still_canceled", up=True)
            allowed = voice_find(f"Skip {phrase}", f"cancel_{segment}_control_retained")
            check_visible_button(allowed, f"Skip {phrase}", True)
        print("VOICE_OWNED_CANCELED_FINAL_TEXT_FIXTURE_PASS: late synthetic results cannot seek; OS audio NONE", flush=True)

        # A competing seek by the local player's user invalidates the selected
        # segment. The old final phrase must not seek to the Skip target.
        for segment, ready, moved, phrase in (
            ("intro", "Local video: intro ready at 0s",
             "Local video moved: intro playhead now 1s", "Intro"),
            ("recap", "Local video: recap ready at 4s",
             "Local video moved: recap playhead now 5s", "Recap"),
        ):
            voice_tap("Reset test player", f"text_fixture_{segment}_manual_reset", up=True)
            voice_find("Local video not prepared", f"text_fixture_{segment}_manual_off", up=True)
            voice_tap(f"Prepare {segment} video", f"text_fixture_{segment}_manual_prepare")
            voice_find(ready, f"text_fixture_{segment}_manual_ready", up=True)
            voice_tap("Fixture move playhead (no audio)", f"text_fixture_{segment}_manual_seek")
            voice_find(moved, f"text_fixture_{segment}_manual_observed", up=True)
            voice_tap(f"Fixture final {phrase} text (no audio)",
                      f"text_fixture_{segment}_manual_stale_request")
            voice_find("Local video unavailable: selected section changed",
                       f"text_fixture_{segment}_manual_refused", up=True)
            voice_find("Fixture final text refused; no additional player action",
                       f"text_fixture_{segment}_manual_policy_refused", up=True)
            intro_off = voice_find("Skip Intro", f"text_fixture_{segment}_manual_intro_off")
            check_visible_button(intro_off, "Skip Intro", False)
            recap_off = voice_find("Skip Recap", f"text_fixture_{segment}_manual_recap_off")
            check_visible_button(recap_off, "Skip Recap", False)
        print("VOICE_OWNED_STALE_PLAYHEAD_FIXTURE_PASS: manual playhead readback rejects old intro/recap final text; OS audio NONE", flush=True)

        # Prepare a fresh Intro immediately before leaving the app.
        # A resumed session must not retain the old local-video entitlement.
        voice_tap("Reset test player", "local_video_before_background_reset", up=True)
        voice_find("Local video not prepared", "local_video_before_background_off", up=True)
        voice_tap("Prepare intro video", "local_video_prepare_before_background", up=True)
        voice_find("Local video: intro ready at 0s", "local_video_ready_before_background", up=True)
        # No speech event was injected, no microphone Start was pressed.
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
        time.sleep(0.4)
        launch()
        wait_for("Start voice check", "voice_fixture_return_off")
        voice_find("Local video not prepared", "voice_fixture_background_abandons_video", up=True)
        intro_off = voice_find("Skip Intro", "voice_fixture_background_intro_disabled")
        check_visible_button(intro_off, "Skip Intro", False)
        recap_off = voice_find("Skip Recap", "voice_fixture_background_recap_disabled")
        check_visible_button(recap_off, "Skip Recap", False)
        screenshot("voice_fixture_background_off")

        # A late supplied final TEXT after Home/resume must not seek or restore
        # the abandoned local-player run. This is NOT an OS recognizer callback.
        for phrase in ("Intro", "Recap"):
            voice_tap(f"Fixture final {phrase} text (no audio)",
                      f"voice_fixture_background_late_{phrase.lower()}", up=True)
            voice_find("Local video not prepared",
                       f"voice_fixture_background_{phrase.lower()}_still_off", up=True)
            voice_find("Test player paused — reset to prepare video again",
                       f"voice_fixture_background_{phrase.lower()}_still_retired", up=True)
            intro_off = voice_find("Skip Intro", f"voice_fixture_background_{phrase.lower()}_intro_off")
            check_visible_button(intro_off, "Skip Intro", False)
            recap_off = voice_find("Skip Recap", f"voice_fixture_background_{phrase.lower()}_recap_off")
            check_visible_button(recap_off, "Skip Recap", False)
        # Preparing a new clip without explicit Reset must not bypass the
        # background retirement barrier or revive Skip eligibility.
        voice_tap("Prepare intro video", "voice_fixture_background_reprepare_denied", up=True)
        voice_find("Local video unavailable: reset required before preparing again",
                   "voice_fixture_background_reprepare_status", up=True)
        intro_off = voice_find("Skip Intro", "voice_fixture_background_reprepare_intro_off")
        check_visible_button(intro_off, "Skip Intro", False)
        recap_off = voice_find("Skip Recap", "voice_fixture_background_reprepare_recap_off")
        check_visible_button(recap_off, "Skip Recap", False)
        print("VOICE_OWNED_BACKGROUND_FINAL_TEXT_FIXTURE_PASS: no stale player seek or reprepare after Home; OS audio NONE", flush=True)

        # A new Activity object after process death must also fail closed.
        # The only persistent datum is an owned-fixture reset marker, not audio.
        adb("shell", "am", "force-stop", package)
        launch()
        wait_for("Connection not verified", "voice_fixture_process_restart_home")
        tap("Sound", "voice_fixture_process_restart_sound")
        tap("Voice check. See microphone activity and recognized words",
            "voice_fixture_process_restart_voice")
        voice_find("Test player paused — reset to prepare video again",
                   "voice_fixture_process_restart_requires_reset", up=True)
        intro_off = voice_find("Skip Intro", "voice_fixture_process_intro_disabled")
        check_visible_button(intro_off, "Skip Intro", False)
        recap_off = voice_find("Skip Recap", "voice_fixture_process_recap_disabled")
        check_visible_button(recap_off, "Skip Recap", False)
        voice_tap("? Local video trial", "voice_fixture_process_open_video", up=True)
        voice_tap("Prepare recap video", "voice_fixture_process_reprepare_denied", up=True)
        voice_find("Local video unavailable: reset required before preparing again",
                   "voice_fixture_process_reprepare_status", up=True)
        intro_off = voice_find("Skip Intro", "voice_fixture_process_reprepare_intro_off")
        check_visible_button(intro_off, "Skip Intro", False)
        recap_off = voice_find("Skip Recap", "voice_fixture_process_reprepare_recap_off")
        check_visible_button(recap_off, "Skip Recap", False)
        voice_tap("Reset test player", "voice_fixture_process_explicit_reset", up=True)
        intro_on = voice_find("Skip Intro", "voice_fixture_process_intro_restored")
        check_visible_button(intro_on, "Skip Intro", True)
        recap_on = voice_find("Skip Recap", "voice_fixture_process_recap_restored")
        check_visible_button(recap_on, "Skip Recap", True)
        screenshot("voice_fixture_process_reset")
        print("VOICE_OWNED_BUTTON_FIXTURE_PASS: real Intro/Recap buttons; no speech or TV claim", flush=True)
        return

    if args.style_only:
        def reveal(label, name):
            for attempt in range(10):
                root, clicked = screen(f"{name}_{attempt}", click=label)
                if clicked:
                    return
                viewport = next((n for n in root.iter("node") if n.get("class") == "android.widget.ScrollView"), None)
                if viewport is None:
                    # A single empty FrameLayout can be published during a native transition.
                    time.sleep(.5)
                    continue
                x0, y0, x1, y1 = map(int, re.findall(r"-?\d+", viewport.get("bounds")))
                x = (x0 + x1) // 2
                adb("shell", "input", "swipe", str(x), str(int(y0 + (y1-y0)*.8)), str(x), str(int(y0 + (y1-y0)*.2)), "300")
            raise AssertionError("Unreachable control: " + label)
        for scale in ("1.0", "1.5"):
            adb("shell", "settings", "put", "system", "font_scale", scale)
            adb("shell", "settings", "put", "global", "animator_duration_scale", "0" if scale == "1.5" else "1")
            adb("shell", "am", "force-stop", package)
            adb("shell", "pm", "clear", package)
            launch()
            wait_for("Start picture setup", "fresh_welcome_" + scale)
            tap("Exit tutorial", "fresh_exit_" + scale)
            prefix = "simple_" + scale.replace(".", "_")
            wait_for("Connection not verified", prefix + "_home")
            reveal("TV & smart-home guide", prefix + "_open")
            root = wait_for("Step 1 of 5", prefix + "_welcome")
            assert not has(root, "More features")
            if scale == "1.5":
                assert any(n.get("text") == "Exit" for n in root.iter("node")), "Large text must keep a visible Exit label"
            screenshot(prefix + "_welcome")
            tap("Start picture setup", prefix + "_start")
            root = wait_for_all(("Which TV do you use?", "Choose TV brand"), prefix + "_brands")
            assert not has(root, "Samsung") and not has(root, "Use a home app?")
            screenshot(prefix + "_brands")
            reveal("Identify TV from a photo", prefix + "_brand_photo")
            wait_for_all(("No photo selected", "Choose a photo"), prefix + "_photo")
            screenshot(prefix + "_photo")
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            wait_for("Step 2 of 5", prefix + "_cancel_restores_brands")
            reveal("Choose TV brand", prefix + "_picker")
            tap("Samsung", prefix + "_select")
            root = wait_for_all(("Step 3 of 5", "Show Samsung steps"), prefix + "_plan")
            assert not has(root, "Use a home app?") and not has(root, "Amazon Alexa")
            assert not has(root, "Next"), "Picture setup must have one primary action"
            assert has(root, "Samsung  ·  "), "Keep the selected TV and phone visible"
            screenshot(prefix + "_plan")
            reveal("? Setup help", prefix + "_context_help")
            tap("Choose home app (optional)", prefix + "_optional_home")
            tap("Google Home", prefix + "_google")
            reveal("? Setup help", prefix + "_home_help")
            wait_for("Jump to Google Home pictures", prefix + "_chosen_home")
            tap("Jump to phone Wi-Fi pictures", prefix + "_wifi_help")
            root = wait_for("connect to your home Wi-Fi", prefix + "_wifi_intro")
            if has(root, "Phone Wi-Fi setup") and has(root, "Google Pixel — connect to your home Wi-Fi"):
                reveal("Google Pixel — connect to your home Wi-Fi", prefix + "_wifi_virtual_phone_choice")
            wait_for("Start guide", prefix + "_wifi_ready")
            tap("Start guide", prefix + "_wifi_start")
            for n in range(7):
                wait_for(f"Step {n + 1} of 7", prefix + f"_wifi_{n}")
                tap("Next" if n < 6 else "Finish guide", prefix + f"_wifi_next_{n}")
            wait_for_all(("Step 3 of 5", "Show Samsung steps"), prefix + "_wifi_returns_same_tv_step")
            reveal("Show Samsung steps", prefix + "_pictures")
            wait_for("Start guide", prefix + "_intro")
            tap("Start guide", prefix + "_first_picture")
            root = wait_for("Step 1 of 17", prefix + "_picture")
            if scale == "1.5":
                assert any(n.get("text") == "Setup" for n in root.iter("node")), "Returning to setup must have a distinct visible label"
                assert sum(n.get("text") == "Back" for n in root.iter("node")) == 1, "Only the previous-picture action should say Back"
            screenshot(prefix + "_picture")
            reveal("? Step help", prefix + "_picture_help")
            reveal("Jump to a picture", prefix + "_picture_jumps")
            tap("Cancel", prefix + "_jump_cancel")
            tap("Next", prefix + "_picture_next")
            wait_for("Step 2 of 17", prefix + "_picture_two")
            tap("Back", prefix + "_picture_back")
            wait_for("Step 1 of 17", prefix + "_picture_one_back")
            tap("Back to Tutorial", prefix + "_return_guide")
            wait_for("Step 3 of 5", prefix + "_return_plan")
            tap("Back", prefix + "_back_brand")
            wait_for("Step 2 of 5", prefix + "_brand_return")
            reveal("Choose TV brand", prefix + "_picker_again")
            tap("Samsung", prefix + "_select_again")
            reveal("? Setup help", prefix + "_skip_tv_help")
            tap("Continue without pictures", prefix + "_skip_tv")
            wait_for("Step 4 of 5", prefix + "_phone_section")
            reveal("? Setup help", prefix + "_skip_phone_help")
            tap("Continue without pictures", prefix + "_skip_phone")
            wait_for("Step 5 of 5", prefix + "_complete")
            reveal("? Setup help", prefix + "_finish_help")
            tap("Jump to voice check", prefix + "_voice_jump")
            wait_for_all(("Microphone off", "Start voice check"), prefix + "_voice_off")
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            wait_for("Step 5 of 5", prefix + "_voice_back")
            reveal("? Setup help", prefix + "_sound_jump_help")
            tap("Jump to sound check", prefix + "_sound_jump")
            wait_for_all(("Microphone off", "Start sound check"), prefix + "_sound_off")
            reveal("[?] What does this show?", prefix + "_sound_about")
            root = wait_for("About the sound check", prefix + "_sound_shortcut")
            assert any(n.get("text", "").casefold() == "jump to recent sound checks" for n in root.iter("node"))
            tap("Close", prefix + "_sound_help_close")
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            wait_for("Step 5 of 5", prefix + "_sound_back")
            tap("Go to Home", prefix + "_done")
            wait_for("Connection not verified", prefix + "_unverified")
            appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
            assert "(running)" not in appops, appops
            def page(label, name):
                if tap(label, name, optional=True):
                    return
                # A native transition can briefly publish only a FrameLayout.
                # Require the compact navigation control before reading its label.
                root = wait_for("Pages ·", name + "_navigation")
                picker = next(n.get("text") for n in root.iter("node") if n.get("text", "").startswith("Pages ·"))
                tap(picker, name + "_pages"); tap(label, name + "_pick")
            page("Sound", prefix + "_sound_page")
            root = wait_for_all(("Live sound check", "Voice check", "? More sound tools"), prefix + "_sound_simple")
            assert not has(root, "Test setup") and not has(root, "Output inventory")
            reveal("? More sound tools", prefix + "_sound_help")
            wait_for("Jump to Test setup", prefix + "_sound_tools")
            tap("Cancel", prefix + "_sound_help_close")
            page("Devices", prefix + "_devices_page")
            reveal("? Device help", prefix + "_device_help")
            reveal("VIZIO network check. Check one TV address on home Wi-Fi", prefix + "_network_open")
            root = wait_for("TV IP address", prefix + "_network_idle")
            assert not has(root, "Read service certificate")
            tap("TV IP address", prefix + "_network_address")
            adb("shell", "input", "text", "8.8.8.8")
            reveal("Find my TV’s IP address", prefix + "_address_guide_open")
            wait_for_all(("VIZIO V505M-K09 · Android", "My TV matches"), prefix + "_address_guide_model")
            reveal("My screen looks different", prefix + "_address_guide_mismatch")
            wait_for("Find the right screen", prefix + "_address_guide_recovery")
            tap("Back", prefix + "_address_guide_model_back")
            tap("My TV matches", prefix + "_address_guide_start")
            targets = ("Menu (gear)", "Network", "Network Information", "IP Address", "TV IP address")
            for step, target in enumerate(targets, 1):
                name = prefix + f"_address_guide_picture_{step}"
                root = wait_for(f"Step {step} of {len(targets)}", name)
                assert any(f"Highlighted: {target}." in node.get("content-desc", "") for node in root.iter("node")), target
                if step == 2:
                    adb("shell", "input", "keyevent", "KEYCODE_BACK")
                    wait_for("Step 1 of 5", name + "_back")
                    tap("Next", name + "_again")
                    wait_for("Step 2 of 5", name + "_restored")
                if step in (3, 5):
                    screenshot(name)
                tap("Back to address field" if step == len(targets) else "Next", name + "_next")
            wait_for_all(("8.8.8.8", "Ready to check the address you enter."), prefix + "_address_guide_return")
            reveal("Check this address", prefix + "_network_rejected")
            root = wait_for_all(("Enter the private IPv4 address", "TV identity, pairing and audio protection are not verified."), prefix + "_network_boundary")
            assert not has(root, "Read service certificate")
            screenshot(prefix + "_network_public_address_rejected")
            reveal("? Help with this check", prefix + "_network_help")
            tap("Check phone Wi-Fi", prefix + "_wifi_guide_open")
            maker = adb("shell", "getprop", "ro.product.manufacturer").decode().strip().casefold()
            route = {
                "google": ("Google Pixel", "Open Pixel Settings", "Network & internet"),
                "samsung": ("Samsung Galaxy", "Open Galaxy Settings", "Connections"),
            }.get(maker)
            if route:
                phone, settings_title, second_target = route
                wait_for(f"{phone} — connect to your home Wi-Fi", prefix + "_wifi_guide_intro")
                tap("Start Wi-Fi steps", prefix + "_wifi_guide_start")
                wait_for_all(("Step 1 of 7", settings_title), prefix + "_wifi_guide_settings")
                tap("Next", prefix + "_wifi_guide_second")
                root = wait_for("Step 2 of 7", prefix + "_wifi_guide_picture")
                assert any(f"Highlighted: {second_target}." in n.get("content-desc", "") for n in root.iter("node")), second_target
                screenshot(prefix + "_wifi_guide_picture")
                adb("shell", "input", "keyevent", "KEYCODE_BACK")
                wait_for_all(("Step 1 of 7", settings_title), prefix + "_wifi_guide_back_one")
                tap("Next", prefix + "_wifi_guide_resume")
                for step in range(2, 8):
                    name = prefix + f"_wifi_guide_{step}"
                    wait_for(f"Step {step} of 7", name)
                    tap("Back to network check" if step == 7 else "Next", name + "_next")
            else:
                root = wait_for_all(("1. Open Settings.", "2. Search for Wi-Fi."), prefix + "_wifi_guide_unmatched")
                assert not has(root, "Google Pixel") and not has(root, "Samsung Galaxy")
                tap("Back to network check", prefix + "_wifi_guide_return")
            root = wait_for("VIZIO network check", prefix + "_wifi_guide_caller")
            for attempt in range(6):
                if has(root, "8.8.8.8"):
                    break
                scroll = next(n for n in root.iter("node") if n.get("class") == "android.widget.ScrollView")
                x0, y0, x1, y1 = map(int, re.findall(r"-?\d+", scroll.get("bounds")))
                x = str((x0 + x1) // 2)
                adb("shell", "input", "swipe", x, str(y0 + (y1-y0)//5), x, str(y1 - (y1-y0)//5), "300")
                root, _ = screen(prefix + f"_wifi_guide_preserved_{attempt}")
            assert has(root, "8.8.8.8"), "Wi-Fi help must preserve the address in the same visit"
            reveal("Review test result", prefix + "_network_review")
            root = wait_for_all(("Audio Bodyguard connection trial (v1)", "Outcome: ADDRESS_REJECTED", "No native check started"), prefix + "_network_review_private")
            assert not any("8.8.8.8" in n.get("text", "") for n in root.iter("node")), "Entered address leaked into the reviewed result"
            screenshot(prefix + "_network_review_private")
            tap("Back", prefix + "_network_review_back")
            wait_for("Ready to check the address you enter.", prefix + "_network_review_cleared")
            if args.tv_certificate_fixture and scale == "1.0":
                # Android Emulator's host loopback alias reaches only this owned test service.
                with _loopback_tv_service() as expected:
                    tap("TV IP address", prefix + "_certificate_address")
                    adb("shell", "input", "text", "10.0.2.2")
                    reveal("Check this address", prefix + "_certificate_check")
                    wait_for("A network service answered", prefix + "_certificate_reply")
                    reveal("Read service certificate", prefix + "_certificate_read")
                    wait_for_all(("Certificate fingerprint read. TV identity is still unverified.", expected),
                                 prefix + "_certificate_observed")
                    screenshot(prefix + "_certificate_observed")
                print("ANDROID_TV_CERTIFICATE_VERIFIED: exact loopback leaf fingerprint, TLS ended before acceptance")
            tap("Back", prefix + "_network_back")
            reveal("Illustrated setup guides. Jump to a TV or home app", prefix + "_guides")
            reveal("Sony", prefix + "_google_tv")
            wait_for_all(("Google TV / Android TV — pair a phone remote", "Start guide"), prefix + "_google_intro")
            tap("Start guide", prefix + "_google_start")
            tap("Next", prefix + "_google_store")
            root = wait_for("Google Play", prefix + "_google_phone_store")
            assert not has(root, "App Store"), "Android must show its actual store"
            tap("Next", prefix + "_google_open")
            tap("Next", prefix + "_google_nearby")
            wait_for_all(("Step 4 of 9", "bottom right", "TVs nearby"), prefix + "_google_target")
            screenshot(prefix + "_google_bottom_right")
            tap("Close", prefix + "_google_close")
            page("Settings", prefix + "_settings_page")
            root = wait_for("? More settings", prefix + "_settings_simple")
            assert not has(root, "Advanced Settings")
            reveal("? More settings", prefix + "_settings_help")
            tap("Jump to Advanced Settings", prefix + "_advanced")
            wait_for("Advanced Settings", prefix + "_advanced_page")
            screenshot(prefix + "_advanced")
            tap("Back to previous page", prefix + "_settings_back")
            wait_for("? More settings", prefix + "_settings_returned")
        adb("shell", "settings", "put", "system", "font_scale", "1.0")
        adb("shell", "settings", "put", "global", "animator_duration_scale", "1")
        print("SIMPLIFIED_SETUP_VERIFIED: default route, optional home app, photo cancellation, picture jumps, back, voice jump, normal/large text and reduced motion")
        return
    def check_test_setup():
        answers = (("Playback phone", "Android 16 test phone"), ("Intended output", "Phone speaker"),
                   ("Second phone", "iPhone iOS 26"), ("Recording app and mode", "Voice Memos mode unknown"),
                   ("Phone placement", "Two phones on table"), ("Setup constraints", "No calibration"))
        def setup_tap(label, name):
            for attempt in range(10):
                root, clicked = screen(name + f"_{attempt}", click=label)
                if clicked:
                    return
                scroller = next((n for n in root.iter("node") if n.get("class") == "android.widget.ScrollView"), None)
                assert scroller is not None, "Worksheet content viewport unavailable"
                x0, y0, x1, y1 = map(int, re.findall(r"-?\d+", scroller.get("bounds")))
                x = (x0 + x1) // 2
                adb("shell", "input", "swipe", str(x), str(int(y0 + (y1-y0)*.8)), str(x), str(int(y0 + (y1-y0)*.2)), "350")
            raise AssertionError("Worksheet field unreachable: " + label)
        def preview(root):
            rows = [n.get("text", "") for n in root.iter("node") if n.get("text", "").startswith("Audio Bodyguard test setup (v1)\n")]
            assert len(rows) == 1, "Require one complete worksheet preview"
            return rows[0]
        def button(root, label):
            return next(n for n in root.iter("node") if n.get("text") == label)
        tap("Sound", "test_setup_sound")
        tap("? More sound tools", "test_setup_sound_help")
        wait_for("Jump to Test setup", "test_setup_sound_entry")
        tap("Test setup. Record the two-phone test arrangement", "test_setup_open")
        form = wait_for("Review setup report", "test_setup_empty")
        assert button(form, "Clear notes").get("enabled") == "false"
        tap("Review setup report", "test_setup_blank_review")
        blank = preview(wait_for("Share setup report", "test_setup_blank_preview"))
        assert "Playback phone: Unknown" in blank and "Independent capture: Not recorded" in blank
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        wait_for("Clear notes", "test_setup_system_back_to_form")
        for index, (label, value) in enumerate(answers):
            setup_tap(label, f"test_setup_field_{index}")
            adb("shell", "input", "text", value.replace(" ", "%s"))
            adb("shell", "input", "keyevent", "KEYCODE_ENTER")
        adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
        adb("shell", "settings", "put", "system", "user_rotation", "1")
        wait_for("Review setup report", "test_setup_form_rotated")
        adb("shell", "settings", "put", "system", "user_rotation", "0")
        tap("Review setup report", "test_setup_filled_review")
        root = wait_for("Share setup report", "test_setup_filled_preview")
        reviewed = preview(root)
        assert f"Audio Bodyguard\nPlatform: Android\nVersion: {version}\nBuild: {build}" in reviewed
        for _, value in answers:
            assert '"' + value + '"' in reviewed, value
        for value in ("Actual playback route: Unknown", "Negotiated format: Unknown", "Playback/capture consent: Not collected", "Physical output and protection: Not verified"):
            assert value in reviewed, value
        assert len(reviewed) <= 4096 and len(reviewed.encode()) <= 8192
        (out / "test-setup-reviewed.txt").write_text(reviewed)
        screenshot("test_setup_review")
        assert not has(root, "Build details test")
        receiver = "com.aqss.bodyguard.sharetest"
        receipt = "files/shared-build-details.json"
        before = None
        try:
            before = adb("shell", "run-as", receiver, "cat", receipt)
        except subprocess.CalledProcessError:
            pass
        tap("Share setup report", "test_setup_share_cancel")
        wait_for("Build details test", "test_setup_chooser_cancel")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        returned = wait_for("Share setup report", "test_setup_cancel_return")
        assert preview(returned) == reviewed and button(returned, "Share setup report").get("enabled") == "true"
        if before is None:
            adb("shell", shlex.join(["run-as", receiver, "sh", "-c", "test ! -e " + receipt]))
        else:
            assert adb("shell", "run-as", receiver, "cat", receipt) == before
        tap("Share setup report", "test_setup_share_receiver")
        wait_for("Build details test", "test_setup_chooser_receiver")
        select_share_receiver("test_setup_select_receiver")
        wait_for("Build details received for test", "test_setup_received")
        received = json.loads(adb("shell", "run-as", receiver, "cat", receipt))
        assert received["text"] == reviewed and received["type"] == "text/plain"
        assert received["action"] == "android.intent.action.SEND" and received["extra_keys"] == ["android.intent.extra.TEXT"]
        assert received["data"] is None and not received["has_stream"]
        assert all(c["text"] == reviewed and c["uri"] is None and not c["has_intent"] for c in received["clips"])
        (out / "test-setup-share-receipt.json").write_text(json.dumps(received, sort_keys=True))
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        assert preview(wait_for("Share setup report", "test_setup_receiver_return")) == reviewed
        adb("shell", "input", "keyevent", "KEYCODE_HOME"); launch()
        assert preview(wait_for("Share setup report", "test_setup_background_return")) == reviewed
        adb("shell", "settings", "put", "system", "font_scale", "1.5")
        assert preview(wait_for("Share setup report", "test_setup_large_review")) == reviewed
        screenshot("test_setup_large_font")
        adb("shell", "settings", "put", "system", "font_scale", "1.0")
        tap("Back", "test_setup_edit_return")
        form = wait_for("Clear notes", "test_setup_notes_retained")
        assert button(form, "Clear notes").get("enabled") == "true"
        tap("Clear notes", "test_setup_clear")
        form = wait_for("Review setup report", "test_setup_cleared")
        assert button(form, "Clear notes").get("enabled") == "false"
        tap("Review setup report", "test_setup_cleared_review")
        cleared = preview(wait_for("Share setup report", "test_setup_cleared_preview"))
        assert "Playback phone: Unknown" in cleared and "Android 16 test phone" not in cleared
        tap("Back", "test_setup_back_to_form"); tap("Back", "test_setup_close")
        tap("Test setup. Record the two-phone test arrangement", "test_setup_reopen")
        assert button(wait_for("Clear notes", "test_setup_reopened_empty"), "Clear notes").get("enabled") == "false"
        setup_tap("Playback phone", "test_setup_before_process")
        adb("shell", "input", "text", "Temporary%snotes"); adb("shell", "input", "keyevent", "KEYCODE_ENTER")
        tap("Review setup report", "test_setup_before_process_review")
        assert "Temporary notes" in preview(wait_for("Share setup report", "test_setup_before_process_preview"))
        adb("shell", "am", "force-stop", package); launch()
        wait_for("Connection not verified", "test_setup_new_process_home")
        tap("Sound", "test_setup_new_process_sound")
        tap("Test setup. Record the two-phone test arrangement", "test_setup_new_process_open")
        assert button(wait_for("Clear notes", "test_setup_new_process_empty"), "Clear notes").get("enabled") == "false"
        tap("Back", "test_setup_new_process_close"); tap("Home", "test_setup_home")
        wait_for("Connection not verified", "test_setup_still_unverified")
        assert "android.permission.RECORD_AUDIO: granted=false" in adb("shell", "dumpsys", "package", package).decode()
        print("TEST_SETUP_OBSERVED: six optional bounded notes, Unknowns, immutable review, native Cancel and exact text-only receiver handoff, rotation/background/large text, Back/Clear/Close/process clearing; no microphone or physical qualification", flush=True)

    def check_setup_output_report():
        receiver = "com.aqss.bodyguard.sharetest"
        receipt_path = "files/shared-build-details.json"

        def text_copy(root, prefix):
            rows = [n.get("text", "") for n in root.iter("node") if n.get("text", "").startswith(prefix)]
            assert len(rows) == 1, "Require one complete report preview"
            return rows[0]

        def open_attachment(name):
            tap("Output inventory. Check this phone’s available audio outputs", name + "_inventory")
            wait_for("Not read yet. Tap Refresh outputs.", name + "_idle")
            tap("Refresh outputs", name + "_refresh")
            wait_for("Connection not verified • No TV command sent", name + "_read")
            tap("Review output report", name + "_review")
            root = wait_for("Share output report", name + "_output_preview")
            original = text_copy(root, "Audio Bodyguard output inventory (v1)\n")
            assert "Advertised sample rates:" in original
            assert has(root, "Add setup notes"), "Reviewed output has no Add setup notes action"
            tap("Add setup notes", name + "_add_notes")
            form = wait_for("Review setup report", name + "_form")
            assert has(form, "Output snapshot included. Outputs may have changed.")
            assert has(form, "Remove output details")
            return original

        tap("Sound", "combined_sound")
        original = open_attachment("combined")
        (out / "combined-output-original.txt").write_text(original)
        # The attachment is a typed in-memory copy, not a new inventory query.
        tap("Playback phone", "combined_phone_note")
        adb("shell", "input", "text", "My%stest%sphone")
        adb("shell", "input", "keyevent", "KEYCODE_ENTER")
        tap("Review setup report", "combined_review")
        root = wait_for("Share setup report", "combined_preview")
        reviewed = text_copy(root, "Audio Bodyguard test setup (v1)\n")
        assert reviewed.endswith("\n\nAttached output snapshot\nSnapshot only. Outputs may have changed.\n\n" + original)
        assert 'Playback phone: "My test phone"' in reviewed
        assert "Actual playback route: Unknown" in reviewed and "Selected playback route: Unknown" in reviewed
        assert "Physical output and protection: Not verified" in reviewed
        assert not has(root, "Build details test"), "Review must not open sharing"
        assert len(reviewed) <= 32 * 1024 and len(reviewed.encode()) <= 64 * 1024
        (out / "combined-setup-reviewed.txt").write_text(reviewed)
        screenshot("combined_setup_review")
        before = None
        try:
            before = adb("shell", "run-as", receiver, "cat", receipt_path)
        except subprocess.CalledProcessError:
            pass
        tap("Share setup report", "combined_cancel_share")
        wait_for("Build details test", "combined_cancel_chooser")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        assert text_copy(wait_for("Share setup report", "combined_cancel_return"), "Audio Bodyguard test setup (v1)\n") == reviewed
        if before is None:
            adb("shell", shlex.join(["run-as", receiver, "sh", "-c", "test ! -e " + receipt_path]))
        else:
            assert adb("shell", "run-as", receiver, "cat", receipt_path) == before
        tap("Share setup report", "combined_receiver_share")
        wait_for("Build details test", "combined_receiver_chooser")
        select_share_receiver("combined_receiver_select")
        wait_for("Build details received for test", "combined_received")
        received = json.loads(adb("shell", "run-as", receiver, "cat", receipt_path))
        assert received["text"] == reviewed and received["type"] == "text/plain"
        assert received["action"] == "android.intent.action.SEND" and received["extra_keys"] == ["android.intent.extra.TEXT"]
        assert received["data"] is None and not received["has_stream"]
        assert all(c["text"] == reviewed and c["uri"] is None and not c["has_intent"] for c in received["clips"])
        (out / "combined-setup-share-receipt.json").write_text(json.dumps(received, sort_keys=True))
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        assert text_copy(wait_for("Share setup report", "combined_receiver_return"), "Audio Bodyguard test setup (v1)\n") == reviewed
        adb("shell", "input", "keyevent", "KEYCODE_HOME"); launch()
        assert text_copy(wait_for("Share setup report", "combined_background_return"), "Audio Bodyguard test setup (v1)\n") == reviewed
        adb("shell", "settings", "put", "system", "user_rotation", "1")
        assert text_copy(wait_for("Share setup report", "combined_rotation"), "Audio Bodyguard test setup (v1)\n") == reviewed
        adb("shell", "settings", "put", "system", "user_rotation", "0")
        wait_for("Share setup report", "combined_portrait")
        adb("shell", "settings", "put", "system", "font_scale", "1.5")
        assert text_copy(wait_for("Share setup report", "combined_large_text"), "Audio Bodyguard test setup (v1)\n") == reviewed
        screenshot("combined_setup_large_font")
        adb("shell", "settings", "put", "system", "font_scale", "1.0")
        wait_for("Share setup report", "combined_normal_text")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        form = wait_for("Remove output details", "combined_back_to_notes")
        assert has(form, "Output snapshot included. Outputs may have changed.")
        tap("Clear notes", "combined_clear_notes")
        tap("Review setup report", "combined_clear_review")
        cleared = text_copy(wait_for("Share setup report", "combined_cleared"), "Audio Bodyguard test setup (v1)\n")
        assert "Playback phone: Unknown" in cleared and cleared.endswith(original)
        tap("Back", "combined_remove_back")
        tap("Remove output details", "combined_remove_attachment")
        tap("Review setup report", "combined_notes_only_review")
        detached = text_copy(wait_for("Share setup report", "combined_notes_only"), "Audio Bodyguard test setup (v1)\n")
        assert "Attached output snapshot" not in detached and original not in detached
        tap("Back", "combined_notes_only_back"); tap("Back", "combined_close_notes")
        # Rotation may have recreated the parent inventory; never infer a fresh
        # read from the surviving attachment. Return to Sound either way.
        root, _ = screen("combined_parent")
        if has(root, "Share output report"):
            assert text_copy(root, "Audio Bodyguard output inventory (v1)\n") == original
            tap("Back", "combined_parent_preview_back")
        root = wait_for("Refresh outputs", "combined_parent_inventory")
        assert next(n for n in root.iter("node") if n.get("text") == "Review output report").get("enabled") == "false"
        tap("Back", "combined_return_sound")
        tap("Test setup. Record the two-phone test arrangement", "combined_direct_open")
        form = wait_for("Review setup report", "combined_direct_empty")
        assert not has(form, "Remove output details")
        tap("Review setup report", "combined_direct_review")
        assert "Attached output snapshot" not in text_copy(wait_for("Share setup report", "combined_direct_preview"), "Audio Bodyguard test setup (v1)\n")
        tap("Back", "combined_direct_back"); tap("Back", "combined_direct_close")
        open_attachment("combined_before_process")
        adb("shell", "am", "force-stop", package); launch()
        wait_for("Connection not verified", "combined_new_process")
        tap("Sound", "combined_new_process_sound")
        tap("Test setup. Record the two-phone test arrangement", "combined_new_process_notes")
        form = wait_for("Review setup report", "combined_new_process_empty")
        assert not has(form, "Remove output details")
        tap("Back", "combined_final_close"); tap("Home", "combined_home")
        wait_for("Connection not verified", "combined_still_unverified")
        assert "android.permission.RECORD_AUDIO: granted=false" in adb("shell", "dumpsys", "package", package).decode()
        print("SETUP_OUTPUT_REPORT_OBSERVED: original dated output text, separate notes review, exact text-only sharing, Cancel, lifecycle/rotation/large text, independent Clear/remove, Close/process discard; no new output read or physical qualification", flush=True)

    def check_output_report():
        receiver = "com.aqss.bodyguard.sharetest"
        receipt_path = "files/shared-build-details.json"

        def review_button(root):
            return next((n for n in root.iter("node") if n.get("text") == "Review output report"), None)

        def preview_text(root):
            rows = [n.get("text", "") for n in root.iter("node")
                    if n.get("text", "").startswith("Audio Bodyguard output inventory (v1)\n")]
            assert len(rows) == 1, "Require one complete native report preview"
            return rows[0]

        def wait_inventory_idle(name):
            # Rotation/large text can put the idle message below the fold.
            # Scroll the actual content viewport, retaining the fixed disabled
            # Review/no-dialog assertions rather than inferring from a timeout.
            wait_for_all(("Output inventory", "Refresh outputs"), name + "_inventory")
            for attempt in range(6):
                root, _ = screen(name + f"_scroll_{attempt}")
                button = review_button(root)
                assert button is not None and button.get("enabled") == "false"
                assert not has(root, "Share output report")
                if has(root, "Not read yet. Tap Refresh outputs."):
                    return root
                scroller = next(n for n in root.iter("node") if n.get("class") == "android.widget.ScrollView")
                x0, y0, x1, y1 = map(int, re.findall(r"-?\d+", scroller.get("bounds")))
                x = (x0 + x1) // 2
                adb("shell", "input", "swipe", str(x), str(int(y0 + (y1-y0) * .8)),
                    str(x), str(int(y0 + (y1-y0) * .2)), "350")
            raise AssertionError("Cleared inventory message not reachable by bounded content scrolling")

        tap("Sound", "output_report_sound")
        tap("Output inventory. Check this phone’s available audio outputs", "output_report_open")
        idle = wait_for("Not read yet. Tap Refresh outputs.", "output_report_idle")
        button = review_button(idle)
        assert button is not None, "Output inventory has no Review output report control"
        assert button.get("enabled") == "false", "Review must be disabled without a successful read"
        tap("Refresh outputs", "output_report_refresh")
        actual = wait_for("Connection not verified • No TV command sent", "output_report_snapshot")
        button = review_button(actual)
        assert button is not None and button.get("enabled") == "true"
        assert not has(actual, "Advertised sample rates:"), "Advanced capabilities must stay behind Review"
        opening_before = frame_snapshot("output-report-open-frames_before")
        tap("Review output report", "output_report_review")
        root = wait_for_all(("Review output report", "Share output report",
                            "Snapshot only. Outputs may have changed."), "output_report_preview")
        assert not has(root, "Build details test"), "Review alone must not launch sharing"
        reviewed = preview_text(root)
        metadata = f"Audio Bodyguard\nPlatform: Android\nVersion: {version}\nBuild: {build}"
        assert metadata in reviewed
        for text in ("Phone:", "Android:", "Selected playback route: Unknown", "Negotiated format: Unknown",
                     "Independent output capture: Not recorded", "Physical output and protection: Not verified"):
            assert text in reviewed, text
        assert len(reviewed) <= 24 * 1024 and len(reviewed.encode()) <= 48 * 1024
        assert "Recent sound checks" not in reviewed and "Recognized words" not in reviewed
        (out / "output-report-reviewed.txt").write_text(reviewed)
        screenshot("output_report_preview")
        complete_frame_evidence("output-report-open-frames", opening_before)
        back_before = frame_snapshot("output-report-back-frames_before")
        tap("Back", "output_report_preview_back")
        back = wait_for_all(("Output inventory", "Snapshot only."), "output_report_back_to_inventory")
        assert review_button(back).get("enabled") == "true", "Closing review must preserve an unchanged live inventory"
        complete_frame_evidence("output-report-back-frames", back_before)
        tap("Review output report", "output_report_review_again")
        assert preview_text(wait_for("Share output report", "output_report_same_review")) == reviewed

        # The native chooser must require a user choice and preserve the exact
        # reviewed payload through Cancel and an isolated receiver handoff.
        before = None
        try:
            before = adb("shell", "run-as", receiver, "cat", receipt_path)
        except subprocess.CalledProcessError:
            pass
        tap("Share output report", "output_report_share_cancel")
        chooser = wait_for("Build details test", "output_report_chooser_cancel")
        assert any(n.get("package") == "com.android.intentresolver" for n in chooser.iter("node"))
        screenshot("output_report_native_chooser")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        returned = wait_for("Share output report", "output_report_cancel_return")
        assert preview_text(returned) == reviewed
        share = next(n for n in returned.iter("node") if n.get("text") == "Share output report")
        assert share.get("enabled") == "true", "Cancel must leave a fresh explicit Share available"
        if before is not None:
            assert adb("shell", "run-as", receiver, "cat", receipt_path) == before, "Cancel must not deliver a new payload"
        else:
            adb("shell", shlex.join(["run-as", receiver, "sh", "-c", "test ! -e " + receipt_path]))
        tap("Share output report", "output_report_share_receiver")
        wait_for("Build details test", "output_report_chooser_receiver")
        select_share_receiver("output_report_select_receiver")
        wait_for("Build details received for test", "output_report_received")
        raw = adb("shell", "run-as", receiver, "cat", receipt_path)
        received = json.loads(raw.decode())
        assert received["action"] == "android.intent.action.SEND" and received["type"] == "text/plain"
        assert received["text"] == reviewed and received["data"] is None and received["has_stream"] is False
        assert received["extra_keys"] == ["android.intent.extra.TEXT"], received["extra_keys"]
        assert all(c["text"] == reviewed and c["uri"] is None and c["has_intent"] is False for c in received["clips"])
        (out / "output-report-share-receipt.json").write_text(json.dumps(received, sort_keys=True))
        # The test receiver is a ScrollView; its Return control can be below a
        # long payload. Native Back returns to the same reviewed report.
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        root = wait_for("Share output report", "output_report_receiver_return")
        assert preview_text(root) == reviewed
        screenshot("output_report_receiver_return")
        tap("Back", "output_report_close_review")
        idle = wait_for("Not read yet. Tap Refresh outputs.", "output_report_after_share")
        assert review_button(idle).get("enabled") == "false"
        tap("Refresh outputs", "output_report_fresh_read")
        wait_for("Snapshot only.", "output_report_refreshed")
        tap("Review output report", "output_report_background_review")
        wait_for("Share output report", "output_report_before_background")
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
        launch()
        root = wait_for("Share output report", "output_report_background_return")
        # An open review remains a labelled historical copy. It is not a new
        # inventory read, active route or negotiated-format observation.
        assert "Snapshot only. Outputs may have changed." in preview_text(root)
        tap("Back", "output_report_background_close")
        idle = wait_for("Not read yet. Tap Refresh outputs.", "output_report_background_inventory_cleared")
        assert review_button(idle).get("enabled") == "false"
        tap("Refresh outputs", "output_report_before_rotation_read")
        wait_for("Snapshot only.", "output_report_rotation_snapshot")
        tap("Review output report", "output_report_rotation_review")
        wait_for("Share output report", "output_report_rotate_open")
        adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
        adb("shell", "settings", "put", "system", "user_rotation", "1")
        idle = wait_inventory_idle("output_report_rotation_cleared")
        assert review_button(idle).get("enabled") == "false" and not has(idle, "Share output report")
        adb("shell", "settings", "put", "system", "user_rotation", "0")
        wait_inventory_idle("output_report_portrait_cleared")
        adb("shell", "settings", "put", "system", "font_scale", "1.5")
        wait_inventory_idle("output_report_large_font_idle")
        tap("Refresh outputs", "output_report_large_font_read")
        wait_for("Snapshot only.", "output_report_large_font_snapshot")
        tap("Review output report", "output_report_large_font_review")
        large = wait_for("Share output report", "output_report_large_font_preview")
        share = next(n for n in large.iter("node") if n.get("text") == "Share output report")
        assert share.get("enabled") == "true"
        screenshot("output_report_large_font")
        adb("shell", "am", "force-stop", package)
        adb("shell", "settings", "put", "system", "font_scale", "1.0")
        launch()
        home = wait_for("Connection not verified", "output_report_new_process")
        assert not has(home, "Share output report")
        tap("Sound", "output_report_new_process_sound")
        tap("Output inventory. Check this phone’s available audio outputs", "output_report_new_process_inventory")
        idle = wait_for("Not read yet. Tap Refresh outputs.", "output_report_new_process_empty")
        assert review_button(idle).get("enabled") == "false"
        tap("Back", "output_report_inventory_back")
        wait_for("Live sound check", "output_report_back_in_sound")
        permission = adb("shell", "dumpsys", "package", package).decode()
        assert "android.permission.RECORD_AUDIO: granted=false" in permission, "Report must not request microphone permission"
        tap("Home", "output_report_home")
        wait_for("Connection not verified", "output_report_still_unverified")
        print("OUTPUT_REPORT_OBSERVED: disabled-before-read, explicit immutable preview, Back preserves unchanged inventory, native Cancel and exact text-only receiver handoff, review return and background clearing; no microphone, playback or physical qualification", flush=True)

    def check_output_freshness():
        observation = adb("shell", "am", "instrument", "-w",
                          "com.aqss.bodyguard.uiprobe/.OutputInventoryProbe", timeout=90).decode()
        (out / "output-inventory-callbacks.txt").write_text(observation)
        if "INSTRUMENTATION_RESULT: output_inventory=passed:" not in observation:
            try:
                (out / "output-freshness-failure.png").write_bytes(adb("exec-out", "run-as", package, "cat", "files/output-freshness-failure.png"))
            except subprocess.CalledProcessError:
                pass
        assert "INSTRUMENTATION_RESULT: output_inventory=passed:" in observation, observation
        for name in ("output-freshness-read", "output-freshness-removed",
                     "output-freshness-added", "output-freshness-resumed", "output-freshness-report-cleared"):
            (out / f"{name}.png").write_bytes(adb("exec-out", "run-as", package, "cat", f"files/{name}.png"))
            adb("shell", "run-as", package, "rm", f"files/{name}.png")
        permission = adb("shell", "dumpsys", "package", package).decode()
        assert "android.permission.RECORD_AUDIO: granted=false" in permission, "Inventory must not request microphone access"
        print("OUTPUT_FRESHNESS_OBSERVED: synthetic callback invalidation and native lifecycle passed; no physical disconnect or routing claim", flush=True)

    if args.setup_output_report_only:
        check_setup_output_report()
        return
    if args.test_setup_only:
        check_test_setup()
        return
    if args.output_report_only:
        check_output_report()
        check_output_freshness()
        return
    if args.tv_guides_only:
        def guide_tap(label, name):
            # Reopening a brand chooser can retain a previous lower scroll
            # offset. A valid brand may be above the viewport, so scan both
            # directions rather than repeatedly scrolling away from it.
            # Every successful path still requires a real observed tap.
            for down in (True, False):
                direction = "down" if down else "up"
                for attempt in range(8):
                    root, clicked = screen(f"{name}-{direction}-{attempt}", click=label)
                    if clicked:
                        return
                    scroll_meter(f"{name}-scroll-{direction}-{attempt}", down=down)
            raise AssertionError(f"TV guide target unavailable: {label}")

        tap("Devices", "tv_guides_devices")
        tap("? Device help", "tv_guides_expand_device_help")
        guide_tap("Illustrated setup guides. Jump to a TV or home app", "tv_guides_open")
        guide_tap("Philips", "tv_guides_philips")
        guide_tap("Google TV / Android TV", "tv_guides_philips_platform")
        guide_tap("? Help", "tv_guides_philips_help")
        guide_tap("Try another way", "tv_guides_philips_options")
        guide_tap("Philips Google TV — pair the voice remote", "tv_guides_philips_remote")
        tap("Start guide", "tv_guides_philips_start")
        for number in range(4):
            tap("Next", f"tv_guides_philips_prefix_{number}")
        wait_for_all(("Step 5 of 10", "Check whether the remote is already paired"), "tv_guides_philips_decision")
        guide_tap("? Step help", "tv_guides_philips_remote_help")
        guide_tap("Remote already connected", "tv_guides_philips_connected")
        wait_for_all(("Step 10 of 10", "Check the real status"), "tv_guides_philips_skipped")
        screenshot("tv_guides_philips_skipped")
        tap("Back", "tv_guides_philips_decision_back")
        wait_for("Step 5 of 10", "tv_guides_philips_back_at_decision")
        tap("Pair this remote", "tv_guides_philips_pair")
        wait_for_all(("Step 6 of 10", "On your TV remote"), "tv_guides_philips_remote_buttons")
        screenshot("tv_guides_philips_remote_buttons")
        tap("Light is blinking", "tv_guides_philips_blinking")
        wait_for("Step 8 of 10", "tv_guides_philips_skips_reset")
        tap("Back", "tv_guides_philips_blinking_back")
        wait_for("Step 6 of 10", "tv_guides_philips_pair_back")
        guide_tap("? Step help", "tv_guides_philips_blinking_help")
        guide_tap("Light is not blinking", "tv_guides_philips_not_blinking")
        wait_for("Step 7 of 10", "tv_guides_philips_reset_only_when_needed")
        screenshot("tv_guides_philips_reset_only_when_needed")
        tap("Close", "tv_guides_philips_close")

        def open_brand(brand, name, platform=None):
            guide_tap("Illustrated setup guides. Jump to a TV or home app", name + "_guides")
            guide_tap(brand, name + "_brand")
            if platform:
                guide_tap(platform, name + "_platform")

        def start_picture(name, phone=False):
            # A new Activity may expose a partial or empty accessibility tree
            # immediately after the platform picker. Shared Roku-family routes
            # can also legitimately retain progress from another TV brand.
            # Settle on the actual intro action before choosing Start or Resume.
            # Never replace resume with a blind tap or accept the wrong route.
            intro_actions = ("Resume guide", "Start part two" if phone else "Start guide")
            for attempt in range(8):
                root, _ = screen(f"{name}_intro_{attempt}")
                if any(has(root, label) for label in intro_actions):
                    break
                time.sleep(0.5)
            else:
                screenshot(name + "_missing_intro")
                raise AssertionError(f"TV guide intro not ready: {name}")
            if has(root, "Resume guide"):
                guide_tap("? Step help", name + "_restart_help")
                guide_tap("Start from the beginning", name + "_restart")
            else:
                tap("Start part two" if phone else "Start guide", name + "_start")
            wait_for("Step 1 of", name + "_first_picture")

        open_brand("Sony", "tv_guides_google")
        start_picture("tv_guides_google")
        for number in range(5): tap("Next", f"tv_guides_google_prefix_{number}")
        wait_for_all(("Step 6 of 9", "Read your TV code", "On your TV"), "tv_guides_google_tv_code")
        screenshot("tv_guides_google_tv_code")
        tap("Next", "tv_guides_google_enter")
        wait_for_all(("Step 7 of 9", "Enter the TV code", "On your phone"), "tv_guides_google_phone_code")
        screenshot("tv_guides_google_phone_code")
        adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
        adb("shell", "settings", "put", "system", "user_rotation", "1")
        wait_for_all(("Step 7 of 9", "Enter the TV code"), "tv_guides_google_rotated")
        adb("shell", "settings", "put", "system", "user_rotation", "0")
        wait_for("Step 7 of 9", "tv_guides_google_portrait")
        tap("Back", "tv_guides_google_back")
        wait_for("Step 6 of 9", "tv_guides_google_back_on_tv")
        tap("Close", "tv_guides_google_close")
        open_brand("Sony", "tv_guides_google_reopen")
        wait_for("Continue at picture 6.", "tv_guides_google_resume_intro")
        tap("Resume guide", "tv_guides_google_resume")
        wait_for("Read your TV code", "tv_guides_google_resumed_tv")
        tap("Close", "tv_guides_google_close_resume")

        open_brand("LG", "tv_guides_lg")
        start_picture("tv_guides_lg")
        for number in range(10): tap("Next", f"tv_guides_lg_prefix_{number}")
        wait_for_all(("Step 11 of 13", "Decide whether to link accounts"), "tv_guides_lg_optional")
        scroll_meter("tv_guides_lg_choice_scroll", down=True)
        root = wait_for_all(("Link", "Skip", "Choose one"), "tv_guides_lg_neutral_choice")
        assert any("neither is selected" in n.get("content-desc", "") for n in root.iter("node")), "Optional linking must not select an account approval"
        screenshot("tv_guides_lg_neutral_choice")
        adb("shell", "settings", "put", "system", "font_scale", "1.5")
        wait_for("Step 11 of 13", "tv_guides_lg_large_text")
        screenshot("tv_guides_lg_large_text")
        tap("Back", "tv_guides_lg_large_back")
        wait_for("Step 10 of 13", "tv_guides_lg_large_back_restored")
        adb("shell", "settings", "put", "system", "font_scale", "1.0")
        wait_for("Step 10 of 13", "tv_guides_lg_normal_text")
        tap("Close", "tv_guides_lg_close")

        open_brand("LG", "tv_guides_lg_phone")
        guide_tap("? Help", "tv_guides_lg_phone_help")
        guide_tap("Try another way", "tv_guides_lg_phone_options")
        guide_tap("2. Check LG ThinQ on your phone", "tv_guides_lg_phone_select")
        # Pairing is an optional action behind Step help, not a primary intro
        # button. Exercise the real help disclosure and one-step Back history.
        guide_tap("? Step help", "tv_guides_lg_phone_pairing_disclosure")
        guide_tap("Open pairing pictures", "tv_guides_lg_phone_pairing_jump")
        wait_for("Connect your LG TV", "tv_guides_lg_pairing_intro")
        tap("Back", "tv_guides_lg_pairing_back_to_phone")
        wait_for("2. Check LG ThinQ on your phone", "tv_guides_lg_phone_restored")
        start_picture("tv_guides_lg_phone", phone=True)
        for number in range(4): tap("Next", f"tv_guides_lg_phone_{number}")
        wait_for_all(("Check the phone controls", "Finish part two"), "tv_guides_lg_phone_final")
        screenshot("tv_guides_lg_phone_final")
        tap("Finish part two", "tv_guides_lg_phone_finish")
        wait_for_all(("DEVICES", "Connection not verified"), "tv_guides_lg_phone_no_connection")

        # Vizio exposes two primary routes; its brand screen has a visible
        # `? Other setup options` disclosure, not a route-intro step-help button.
        open_brand("Vizio", "tv_guides_vizio")
        guide_tap("? Help", "tv_guides_vizio_options")
        guide_tap("Vizio — link the TV account (6-digit code)", "tv_guides_vizio_account")
        start_picture("tv_guides_vizio")
        for number in range(2, 12):
            tap("Next", f"tv_guides_vizio_step_{number}")
            wait_for(f"Step {number} of 11", f"tv_guides_vizio_position_{number}")
            if number in (5, 6, 7, 8, 9, 10): screenshot(f"tv_guides_vizio_menu_{number}")
            if number == 9: wait_for_all(("Read the account code on your TV", "On your TV"), "tv_guides_vizio_tv_code")
            if number == 10: wait_for_all(("Enter the account code on your phone", "On your phone"), "tv_guides_vizio_phone_code")
        tap("Close", "tv_guides_vizio_close")

        for name, brand, platform, title, selection in (
            ("tcl_roku", "TCL", "Roku TV", "Find my IP address", "Network"),
            ("sharp", "Sharp — Roku TV models", None, "Find my exact model", "System"),
            ("roku", "Roku-branded TV", None, "Find my IP address", "Network"),
            ("philips_roku", "Philips", "Roku TV", "Find my IP address", "Network"),
        ):
            open_brand(brand, "tv_guides_" + name, platform)
            wait_for(title, "tv_guides_" + name + "_title")
            start_picture("tv_guides_" + name)
            tap("Next", "tv_guides_" + name + "_settings")
            tap("Next", "tv_guides_" + name + "_menu")
            wait_for_all(("Step 3 of 5", "3 → " + selection), "tv_guides_" + name + "_correct_menu")
            screenshot("tv_guides_" + name + "_correct_menu")
            tap("Close", "tv_guides_" + name + "_close")

        open_brand("Hisense", "tv_guides_hisense", "VIDAA")
        wait_for("43A6GV / VIDAA U5", "tv_guides_hisense_model_scope")
        screenshot("tv_guides_hisense_model_scope")
        tap("Close", "tv_guides_hisense_close")
        open_brand("Insignia — match Roku TV or Fire TV", "tv_guides_insignia", "Fire TV")
        start_picture("tv_guides_insignia")
        for number in range(4): tap("Next", f"tv_guides_insignia_prefix_{number}")
        wait_for("Step 5 of 8", "tv_guides_fire_choice")
        screenshot("tv_guides_fire_choice")
        tap("Next", "tv_guides_fire_account")
        wait_for_all(("Step 6 of 8", "Read the account approval screen"), "tv_guides_fire_tv_account")
        guide_tap("? Step help", "tv_guides_fire_account_help")
        guide_tap("Account sign-in finished", "tv_guides_fire_account_done")
        wait_for("Step 8 of 8", "tv_guides_fire_skipped_code")
        tap("Back", "tv_guides_fire_back")
        wait_for("Step 6 of 8", "tv_guides_fire_back_to_qr")
        screenshot("tv_guides_fire_back_to_qr")
        tap("Close", "tv_guides_fire_close")

        open_brand("TCL", "tv_guides_google_manual", "Google TV / Android TV")
        guide_tap("? Help", "tv_guides_google_setup_help")
        guide_tap("Try another way", "tv_guides_google_setup_options")
        guide_tap("Google TV — first setup with Google Home", "tv_guides_google_setup")
        start_picture("tv_guides_google_qr")
        for number in range(8): tap("Next", f"tv_guides_google_qr_prefix_{number}")
        wait_for_all(("Step 9 of 13", "Open the phone scanner", "On your phone"), "tv_guides_google_qr_phone")
        screenshot("tv_guides_google_qr_phone")
        tap("Next", "tv_guides_google_qr_point")
        wait_for_all(("Step 10 of 13", "Scan the TV setup code", "Your TV + your phone"), "tv_guides_google_qr_tv")
        screenshot("tv_guides_google_qr_tv")
        guide_tap("? Step help", "tv_guides_google_manual_help")
        guide_tap("Use the TV remote instead", "tv_guides_google_manual_select")
        wait_for("Google TV — finish setup with the TV remote", "tv_guides_google_manual_intro")
        start_picture("tv_guides_google_manual")
        tap("Next", "tv_guides_google_manual_down")
        wait_for_all(("Step 2 of 7", "On your TV remote", "Down button"), "tv_guides_google_manual_remote")
        screenshot("tv_guides_google_manual_remote")
        tap("Back", "tv_guides_google_manual_back")
        wait_for("Step 1 of 7", "tv_guides_google_manual_back_restored")
        tap("Close", "tv_guides_google_manual_close")
        tap("Home", "tv_guides_home")
        wait_for("Connection not verified", "tv_guides_no_protection")
        print("TV_GUIDES_OBSERVED: TV/phone code separation, optional choices, Philips pairing decisions, Fire QR completion, brand/platform menus, app-specific phone checks, rotation/resume and large text; illustrated navigation only, no physical pairing", flush=True)
        return
    if args.output_inventory_only:
        check_output_freshness()
        return
    if args.samsung_setup_only:
        def tap_scroll(label, name):
            for attempt in range(8):
                root, clicked = screen(f"{name}-{attempt}", click=label)
                if clicked:
                    return
                scroll_meter(f"{name}-scroll-{attempt}", down=True)
            raise AssertionError(f"Samsung setup target unavailable: {label}")

        def open_samsung(name):
            tap_scroll("Illustrated setup guides. TV pairing, Google Home & Alexa · one picture at a time", name + "_guides")
            tap_scroll("Samsung", name + "_brand")

        tap("Devices", "samsung_devices")
        open_samsung("samsung_first")
        intro = wait_for("Set up your Samsung TV", "samsung_single_intro")
        assert not has(intro, "TV shows a PIN"), "Do not predict the TV request at the entry screen"
        tap("Start guide", "samsung_start")
        for number in range(14):
            tap("Next", f"samsung_prefix_{number}")
        wait_for_all(("Step 15 of 17", "Approve on the television"), "samsung_ok_request")
        screenshot("samsung_ok_request")
        tap_scroll("? Step help", "samsung_pin_options_help")
        tap_scroll("TV shows a PIN", "samsung_switch_pin")
        wait_for_all(("Step 15 of 18", "Read the TV PIN", "On your TV"), "samsung_tv_pin")
        screenshot("samsung_tv_pin")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        wait_for_all(("Step 15 of 17", "Approve on the television"), "samsung_branch_back")
        tap_scroll("? Step help", "samsung_pin_options_help")
        tap_scroll("TV shows a PIN", "samsung_switch_pin_again")
        tap("Next", "samsung_pin_phone")
        wait_for_all(("Step 16 of 18", "Enter the TV PIN", "On your phone"), "samsung_phone_pin")
        screenshot("samsung_phone_pin")
        adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
        adb("shell", "settings", "put", "system", "user_rotation", "1")
        wait_for_all(("Step 16 of 18", "Enter the TV PIN"), "samsung_pin_rotated")
        adb("shell", "settings", "put", "system", "user_rotation", "0")
        wait_for("Enter the TV PIN", "samsung_pin_portrait")
        tap("Close", "samsung_close_pin")
        open_samsung("samsung_reopen_pin")
        wait_for("Continue at picture 16.", "samsung_pin_resume_intro")
        tap("Resume guide", "samsung_resume_pin")
        wait_for("Enter the TV PIN", "samsung_resumed_phone_pin")
        tap("Next", "samsung_name"); tap("Next", "samsung_result")
        wait_for("Check the actual result", "samsung_pin_result")
        tap("Finish guide", "samsung_pin_finish")
        wait_for("No qualified device connected", "samsung_pin_finished_unknown")
        open_samsung("samsung_cleared")
        root = wait_for_all(("Samsung — connect with SmartThings", "Start guide"), "samsung_pairing_bookmark_cleared")
        assert not has(root, "Continue at picture"), "Completing the variant must clear the shared pairing bookmark"
        tap("Close", "samsung_close_cleared")
        tap("Home", "samsung_home")
        tap_scroll("Back to Tutorial", "samsung_resume_tutorial")
        tap("Start picture setup", "samsung_begin_tutorial")
        tap_scroll("Samsung", "samsung_choose_tv"); tap("Next", "samsung_choose_home_step")
        tap_scroll("Neither / not sure", "samsung_no_assistant"); tap("Next", "samsung_plan")
        tap_scroll("Show Samsung steps", "samsung_pair_from_tutorial")
        tap("Start guide", "samsung_ok_start")
        for number in range(14):
            tap("Next", f"samsung_ok_prefix_{number}")
        wait_for("Approve on the television", "samsung_ok_actual_request")
        tap("Next", "samsung_ok_name"); tap("Next", "samsung_ok_result")
        tap("Finish guide", "samsung_ok_finish")
        wait_for("Step 5 of 6", "samsung_phone_part")
        tap_scroll("Phone pictures", "samsung_phone_pictures")
        wait_for_all(("2. Check Samsung on your phone", "TV is missing — open pairing"), "samsung_phone_intro")
        tap_scroll("TV is missing — open pairing", "samsung_missing_help")
        wait_for("Set up your Samsung TV", "samsung_missing_pairing_intro")
        tap("Back", "samsung_missing_back")
        wait_for("2. Check Samsung on your phone", "samsung_missing_returns_to_phone_intro")
        tap("Start part two", "samsung_phone_begin")
        for number in range(4):
            tap("Next", f"samsung_phone_check_{number}")
        wait_for("Check the phone controls", "samsung_phone_controls")
        screenshot("samsung_phone_controls")
        tap("Finish part two", "samsung_phone_finish")
        wait_for("Step 6 of 6", "samsung_both_parts_complete")
        tap("Exit tutorial", "samsung_exit")
        wait_for("Connection not verified", "samsung_still_unknown")
        record = {"source_commit": os.environ.get("GITHUB_SHA"), "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
                  "version": version, "build": build, "scope": "native emulator guide navigation, no physical pairing",
                  "checks": ["single entry", "OK/PIN choice at request", "PIN Back", "PIN rotation", "PIN resume", "pairing bookmark cleared", "OK completion", "Samsung phone companion", "missing TV help and Back", "both tutorial parts", "connection remains unverified"]}
        (out / "samsung-setup-observed.json").write_text(json.dumps(record, indent=2))
        print("SAMSUNG_SETUP_EMULATOR_OBSERVED " + json.dumps(record, sort_keys=True), flush=True)
        return

    review_insights_recaps("insights_recaps_empty", ("No completed sound checks in this app session.",), return_sound=False, report=True)
    tap("Recent sound checks", "insights_recaps_reopen_empty")
    wait_for("No completed sound checks in this app session.", "insights_recaps_reopened_empty")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for_all(("Audio trends", "Recent sound checks"), "insights_recaps_back_returns_to_insights")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Connection not verified", "insights_recaps_back_returns_home")
    tap("Settings", "build_details_settings")
    wait_for("Appearance", "build_details_settings_page")
    tap("Build details", "build_details_open")
    build_details = wait_for_all(("Build details", f"Version: {version}", f"Build: {build}",
                                  "Include the version and build when reporting a problem."), "installed_build_details")
    assert any(node.get("content-desc") == "Back" or node.get("text") == "Back" for node in build_details.iter("node")), "Build details requires an accessible Back control"
    screenshot("installed_build_details")
    receiver = "com.aqss.bodyguard.sharetest"
    receiver_file = "files/shared-build-details.json"
    adb("shell", "run-as", receiver, "rm", "-f", receiver_file)
    tap("Share build details", "build_share_open")
    chooser = wait_for("Build details test", "build_share_native_chooser")
    assert any(node.get("package") == "com.android.intentresolver" for node in chooser.iter("node")), "Require the real Android Sharesheet"
    screenshot("build_share_native_chooser")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    expected_share = f"Audio Bodyguard\nPlatform: Android\nVersion: {version}\nBuild: {build}"
    wait_for_all(("Build details", expected_share, "Share build details"), "build_share_cancel_return")
    adb("shell", shlex.join(["run-as", receiver, "sh", "-c", "test ! -e " + receiver_file]))
    screenshot("build_share_cancel_return")
    tap("Share build details", "build_share_reopen")
    wait_for("Build details test", "build_share_native_chooser_again")
    select_share_receiver("build_share_select_test_receiver")
    received = wait_for_all(("Build details received for test", expected_share, "Return to Build details"), "build_share_receiver_observed")
    assert any(node.get("package") == receiver for node in received.iter("node")), "Require the independent receiver Activity"
    screenshot("build_share_receiver_observed")
    receipt = adb("shell", "run-as", receiver, "cat", receiver_file)
    (out / "shared-build-details-receiver-raw.txt").write_bytes(receipt)
    observed = json.loads(receipt.decode())
    assert observed["action"] == "android.intent.action.SEND" and observed["type"] == "text/plain", observed
    assert observed["text"] == expected_share, observed
    assert observed["data"] is None and observed["has_stream"] is False, observed
    assert all(item["text"] == expected_share and item["uri"] is None and item["has_intent"] is False for item in observed["clips"]), observed
    (out / "shared-build-details.json").write_text(json.dumps(observed, sort_keys=True))
    shared_appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
    (out / "build-share-appops.txt").write_text(shared_appops)
    assert "(running)" not in shared_appops, shared_appops
    tap("Return to Build details", "build_share_leave_test_receiver")
    wait_for_all(("Build details", expected_share, "Share build details"), "build_share_receiver_return")
    screenshot("build_share_receiver_return")
    print("BUILD_DETAILS_SHARE_OBSERVED: native cancel, exact four-field Intent receipt and enabled preview return", flush=True)
    tap("Back", "build_details_close")
    wait_for_all(("Appearance", "? More settings"), "build_details_return_to_settings")

    def open_support_report(name):
        tap("Advanced Settings", name + "_advanced")
        for attempt in range(7):
            root, _ = screen(f"{name}_find_{attempt}")
            bounds = _support_report_anchor(root)
            if bounds:
                tap("About Private support report", name + "_open")
                return bounds
            scroll_meter(f"{name}_scroll_{attempt}", down=True)
        raise AssertionError("Private support report was not visible in Advanced Settings")

    def close_support_report(name, caller_bounds):
        tap("Back", name + "_back")
        # The title can be above the viewport. Require the same visible report
        # control in the restored settings scroll position.
        returned = wait_for_all(("Jump to", "Private support report"), name + "_caller")
        assert _support_report_anchor(returned) == caller_bounds, "Back must preserve the report's settings position"

    # Start with a genuinely fresh process: no completed input checks exist.
    caller_bounds = open_support_report("support_report")
    expected_report = expected_share + "\n\nRecent sound checks (this app session)\nNo completed sound checks in this app session.\n\nInput observations only; not proof of sound safety, protection or TV control."
    wait_for(expected_report, "support_report_default_includes_checks")
    tap("Include recent sound checks", "support_report_exclude_choice_required")
    root = wait_for(expected_share, "support_report_build_only_preview")
    assert any(n.get("text") == expected_share for n in root.iter("node"))
    assert not any("Recent sound checks (this app session)" in n.get("text", "") for n in root.iter("node"))
    screenshot("support_report_build_only_preview")
    tap("Include recent sound checks", "support_report_restore_checks")
    wait_for(expected_report, "support_report_restored_snapshot")
    tap("Share support report", "support_report_share_required")
    wait_for("Build details test", "support_report_native_chooser")
    screenshot("support_report_native_chooser")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for_all((expected_report, "Share support report", "Review before sharing"), "support_report_cancel_return")
    # The earlier build-detail receipt must not be replaced by Cancel.
    assert adb("shell", "run-as", receiver, "cat", receiver_file) == receipt
    screenshot("support_report_cancel_return")
    tap("Share support report", "support_report_reopen")
    select_share_receiver("support_report_select_test_receiver")
    report_received = wait_for_all(("Build details received for test", expected_report, "Return to Build details"), "support_report_receiver_observed")
    assert any(n.get("package") == receiver for n in report_received.iter("node"))
    report_receipt = adb("shell", "run-as", receiver, "cat", receiver_file)
    (out / "shared-support-report-receiver-raw.txt").write_bytes(report_receipt)
    report_observed = json.loads(report_receipt.decode())
    assert report_observed["action"] == "android.intent.action.SEND" and report_observed["type"] == "text/plain", report_observed
    assert report_observed["text"] == expected_report, report_observed
    assert report_observed["data"] is None and report_observed["has_stream"] is False, report_observed
    assert all(item["text"] == expected_report and item["uri"] is None and item["has_intent"] is False for item in report_observed["clips"]), report_observed
    (out / "shared-support-report.json").write_text(json.dumps(report_observed, sort_keys=True))
    tap("Return to Build details", "support_report_leave_test_receiver")
    wait_for_all((expected_report, "Share support report"), "support_report_receiver_return")
    screenshot("support_report_receiver_return")
    report_appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
    (out / "support-report-appops.txt").write_text(report_appops)
    assert "(running)" not in report_appops, report_appops
    close_support_report("support_report", caller_bounds)
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Appearance", "support_report_back_to_settings")
    print("SUPPORT_REPORT_SHARE_OBSERVED: empty allowlisted preview, native Cancel, exact Intent receipt and return to Advanced Settings", flush=True)
    tap("Home", "build_details_return_home")
    wait_for("Connection not verified", "build_details_home_still_unverified")
    def review_report(name, recap, share=False, exclude=False):
        expected = expected_share + "\n\nRecent sound checks (this app session)\n" + recap + "\n\nInput observations only; not proof of sound safety, protection or TV control."
        tap("Settings", name + "_settings")
        caller_bounds = open_support_report(name)
        wait_for(expected, name + "_preview")
        if exclude:
            tap("Include recent sound checks", name + "_exclude_checks")
            expected = expected_share
            preview = wait_for(expected, name + "_build_only")
            assert any(n.get("text") == expected for n in preview.iter("node"))
            assert not any("Recent sound checks (this app session)" in n.get("text", "") for n in preview.iter("node"))
        screenshot(name + "_preview")
        if share:
            previous = adb("shell", "run-as", receiver, "cat", receiver_file)
            tap("Share support report", name + "_share")
            chooser = wait_for("Build details test", name + "_chooser")
            assert any(n.get("package") == "com.android.intentresolver" for n in chooser.iter("node"))
            screenshot(name + "_chooser")
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            wait_for_all((expected, "Share support report"), name + "_cancel_return")
            assert adb("shell", "run-as", receiver, "cat", receiver_file) == previous
            tap("Share support report", name + "_reopen")
            select_share_receiver(name + "_receiver")
            received = wait_for_all((expected, "Return to Build details"), name + "_received")
            assert any(n.get("package") == receiver for n in received.iter("node"))
            raw = adb("shell", "run-as", receiver, "cat", receiver_file)
            (out / (name + "_receiver_raw.txt")).write_bytes(raw)
            item = json.loads(raw.decode())
            assert item["action"] == "android.intent.action.SEND" and item["type"] == "text/plain", item
            assert item["text"] == expected and item["data"] is None and item["has_stream"] is False, item
            assert all(c["text"] == expected and c["uri"] is None and c["has_intent"] is False for c in item["clips"]), item
            (out / (name + "_receipt.json")).write_text(json.dumps(item, sort_keys=True))
            tap("Return to Build details", name + "_return")
            wait_for_all((expected, "Share support report"), name + "_returned_preview")
            screenshot(name + "_returned_preview")
        ops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
        (out / (name + "_appops.txt")).write_text(ops)
        assert "(running)" not in ops, ops
        close_support_report(name, caller_bounds)
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        wait_for("Appearance", name + "_ordinary_settings")
        tap("Sound", name + "_return_sound")
        wait_for("Voice check", name + "_sound_page")
        print("SUPPORT_REPORT_NATIVE_OBSERVED: " + name, flush=True)

    # A synthetic image in this isolated emulator goes through the real system
    # picker, image decoder, bundled ML Kit and app review screen. Never inject
    # OCR text or a result directly into the app.
    def choose_photo_fixture(display_name, case_prefix):
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

    def photo_fixture_case(fixture_name, display_name, case_prefix, expected):
        tap("Devices", f"{case_prefix}_devices_page")
        tap("TV photo setup. Read a model label or Network settings photo", "open_photo_check")
        empty = wait_for("No photo selected", f"{case_prefix}_starts_empty")
        assert not has(empty, "Brand:") and not has(empty, "Model:") and not has(empty, "TV IP hint:"), "New photo screen must keep optional details hidden"
        if case_prefix == "photo":
            tap("? Photo help", "photo_open_guide_help")
            tap("VIZIO V505M-K09 address pictures", "photo_open_model_guide")
            intro = wait_for_all(("VIZIO V505M-K09 · Android", "My TV matches"), "photo_confirm_guide_model")
            assert not has(intro, "Check this address"), "Photo help must open the pictures only"
            tap("My TV matches", "photo_start_model_guide")
            for step, target in enumerate(("Menu (gear)", "Network", "Network Information", "IP Address"), start=1):
                page = wait_for(f"Step {step} of 4", f"photo_model_guide_step_{step}")
                assert any(f"Highlighted: {target}." in n.get("content-desc", "") for n in page.iter("node"))
                if step == 2:
                    adb("shell", "input", "keyevent", "KEYCODE_BACK")
                    wait_for("Step 1 of 4", "photo_guide_system_back")
                    tap("Next", "photo_guide_next_again")
                    wait_for("Step 2 of 4", "photo_guide_step_restored")
                if step == 4:
                    screenshot("photo_guide_ip_address")
                tap("Back to photo setup" if step == 4 else "Next", f"photo_guide_advance_{step}")
            wait_for_all(("TV photo setup", "No photo selected"), "photo_guide_returns_to_photo")
        tap("Show photo details", f"{case_prefix}_show_details")
        wait_photo_fields(("No photo selected", "Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified"), f"{case_prefix}_empty_details")
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
            choose_photo_fixture(display_name, case_prefix)
            wait_photo_fields(expected,
                         f"{case_prefix}_native_ocr_result", attempts=30)
            screenshot(f"{case_prefix}_native_ocr_result")
            if case_prefix == "photo":
                wait_for("Address read from photo: 10.20.30.40", "photo_address_review")
                tap("Use address in VIZIO check", "photo_address_confirm")
                check = wait_for_all(("VIZIO network check", "Ready to check the address you enter."), "photo_address_idle_check")
                field = next(n for n in check.iter("node") if n.get("class") == "android.widget.EditText")
                assert field.get("text") == "10.20.30.40" and field.get("enabled") == "true"
                assert not has(check, "Review test result"), "Filling the address must not start the check"
                screenshot("photo_address_idle_check")
                adb("shell", "input", "keyevent", "KEYCODE_HOME"); launch()
                check = wait_for_all(("TV IP address", "Ready to check the address you enter."), "photo_address_check_cleared")
                assert not has(check, "10.20.30.40"), "The handoff must not replay after backgrounding"
                tap("Back", "photo_address_back")
                wait_for("Address read from photo: 10.20.30.40", "photo_address_back_to_review")
                # A newly opened selection replaces the old review even if cancelled.
                # Use the real picker, then prove the old VIZIO/model/IP do not return.
                tap("Choose a photo", "photo_replace_to_cancel")
                screen("photo_replacement_picker")
                adb("shell", "input", "keyevent", "KEYCODE_BACK")
                empty = wait_photo_fields(("No photo selected", "Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified"),
                                          "photo_replacement_cancel_empty")
                assert not has(empty, "Use address in VIZIO check"), "Cancelled replacement must clear the old address action"
                screenshot("photo_replacement_cancel_empty")
                choose_photo_fixture(display_name, "photo_reselect")
                wait_photo_fields(expected, "photo_reselect_native_ocr_result", attempts=30)
            for attempt in range(4):
                _, opened = screen(f"{case_prefix}_clear_help_{attempt}", click="? Photo help")
                if opened:
                    break
                scroll_meter(f"{case_prefix}_find_photo_help_{attempt}", down=True)
            else:
                raise AssertionError("Photo help is unreachable in the photo review")
            tap("Clear photo details", f"{case_prefix}_clear")
            for attempt in range(3):
                scroll_meter(f"{case_prefix}_after_clear_top_{attempt}", down=False)
            wait_photo_fields(("No photo selected", "Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified"),
                         f"{case_prefix}_clear_empty")
            screenshot(f"{case_prefix}_clear_empty")
            tap("Choose a photo", f"{case_prefix}_choose_to_cancel")
            screen(f"{case_prefix}_picker_before_cancel")
            adb("shell", "input", "keyevent", "KEYCODE_BACK")
            wait_photo_fields(("No photo selected", "Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified"), f"{case_prefix}_cancel_stays_empty")
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
    for case in ("empty", "unrelated"):
        photo_fixture_case(f"tv-photo-{case}.png", f"aqss-tv-{case}.png", f"photo_{case}",
                           ("Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified",
                            "No TV details found. Try a closer photo of the model label or IP address row."))
    photo_fixture_case("tv-photo-brand-only.png", "aqss-tv-brand-only.png", "photo_brand_only",
                       ("Brand: SAMSUNG", "Model: Not identified", "TV IP hint: Not identified", "Nothing is connected."))
    photo_fixture_case("tv-photo-text-limit.png", "aqss-tv-text-limit.png", "photo_limit",
                       ("Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified",
                        "Photo text could not be reviewed. Choose a closer photo of the model or IP address row."))

    # A test-only Instrumentation monitor returns camera fixture bytes through
    # EXTRA_OUTPUT, with no result thumbnail; the real decoder and ML Kit run.
    camera = adb("shell", "am", "instrument", "-w", "com.aqss.bodyguard.uiprobe/.CameraCaptureProbe", timeout=150).decode()
    (out / "camera-capture-contract.txt").write_text(camera)
    assert "INSTRUMENTATION_RESULT: camera_capture=passed:" in camera, camera
    for name in ("camera-full-image", "camera-cancel"):
        (out / f"{name}.png").write_bytes(adb("exec-out", "run-as", package, "cat", f"files/{name}.png"))
        adb("shell", "run-as", package, "rm", f"files/{name}.png")
    assert (out / "camera-full-image.png").read_bytes() != (out / "camera-cancel.png").read_bytes(), "Camera evidence reused the previous rendered frame"
    deadline = adb("shell", "am", "instrument", "-w", "com.aqss.bodyguard.uiprobe/.PhotoDeadlineProbe", timeout=150).decode()
    (out / "photo-deadline-contract.txt").write_text(deadline)
    assert "INSTRUMENTATION_RESULT: photo_deadline=passed:" in deadline, deadline
    for name in ("photo-deadline", "photo-work-busy", "photo-work-ready", "photo-work-ready-resume", "photo-deadline-retry"):
        (out / f"{name}.png").write_bytes(adb("exec-out", "run-as", package, "cat", f"files/{name}.png"))
        adb("shell", "run-as", package, "rm", f"files/{name}.png")
    assert (out / "photo-deadline.png").read_bytes() != (out / "photo-deadline-retry.png").read_bytes(), "Photo retry evidence reused the expired frame"
    assert (out / "photo-work-busy.png").read_bytes() != (out / "photo-work-ready.png").read_bytes(), "Ready notice reused the busy frame"
    launch()
    wait_for("Connection not verified", "camera_probe_returned_home")

    tap("Sound", "sound_page")
    tap("Output inventory. Check this phone’s available audio outputs", "output_inventory_open")
    inventory_idle = wait_for_all(("Not read yet. Tap Refresh outputs.",
                                   "Check available outputs to get one clear next step.",
                                   "Connection not verified • No TV command sent"),
                                  "output_inventory_idle")
    assert not has(inventory_idle, "Start sound check")
    tap("Refresh outputs", "output_inventory_refresh")
    inventory = wait_for_all(("available output device", "Snapshot only.",
                              "Connection not verified • No TV command sent"),
                             "output_inventory_read")
    assert not has(inventory, "Output inventory unavailable")
    assert not has(inventory, "Advertised sample rates:"), "Advanced capabilities must stay behind Review"
    screenshot("output_inventory_read")
    permission = adb("shell", "dumpsys", "package", package).decode()
    assert "android.permission.RECORD_AUDIO: granted=false" in permission, "Inventory must not request microphone access"
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    launch()
    wait_for_all(("Output inventory", "Not read yet. Tap Refresh outputs."), "output_inventory_resume_cleared")
    tap("Refresh outputs", "output_inventory_refresh_again")
    wait_for("Snapshot only.", "output_inventory_refreshed_again")
    tap("Back", "output_inventory_back")
    wait_for("Live sound check", "output_inventory_back_in_sound")
    tap("Output inventory. Check this phone’s available audio outputs", "output_inventory_reopen")
    wait_for("Not read yet. Tap Refresh outputs.", "output_inventory_reopened_empty")
    tap("Back", "output_inventory_close_again")
    print("OUTPUT_INVENTORY_OBSERVED: simple next-step guide keeps selection unverified and sends no command; advanced capabilities remain behind Review; explicit metadata refresh, microphone permission unrequested, background/resume clears snapshot, Back/reopen clears snapshot; no playback or physical qualification", flush=True)
    check_test_setup()
    check_setup_output_report()
    check_output_report()
    check_output_freshness()
    launch()
    wait_for("Connection not verified", "output_probe_returned_home")
    tap("Sound", "sound_after_output_probe")
    tap("Live sound check. Try the phone microphone for 30 seconds", "open_check")
    idle_meter = wait_for("Microphone off", "microphone_off")
    assert not has(idle_meter, "Open app settings"), "Permission shortcut appeared before an attempted request"
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

    def open_app_permission_settings(name, return_activity="com.aqss.bodyguard.prototype.LiveSoundCheckActivity"):
        tap("Open app settings", name)
        settings = wait_for_all(("Audio Bodyguard Live Test", "Permissions"), name + "-app-info")
        assert any(node.get("package") == "com.android.settings" for node in settings.iter("node")), "Settings did not open"
        activities = adb("shell", "dumpsys", "activity", "activities").decode()
        (out / (name + "-activities.txt")).write_text(activities)
        # Android can replace the public details intent with its internal SPA
        # route. Require the observed app-specific page and foreground Settings,
        # rather than expecting the caller's action/data to survive that redirect.
        assert re.search(r"topResumedActivity=ActivityRecord\{[^\n]*com\.android\.settings/", activities), "Settings is not foreground"
        assert package + "/" + return_activity in activities, "Input screen is missing from the Settings return history"

    open_app_permission_settings("permission_settings_denied")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for_all(("Microphone permission denied", "No live input", "Start sound check"), "settings_denied_return_off")
    denied_appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
    (out / "settings-denied-appops.txt").write_text(denied_appops)
    assert "(running)" not in denied_appops, denied_appops
    screenshot("settings_denied_return_off")
    open_app_permission_settings("permission_settings_granted")
    adb("shell", "pm", "grant", package, "android.permission.RECORD_AUDIO")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    after_settings = wait_for_all(("Permission granted. Tap Start when you are ready.", "No live input", "Start sound check"), "settings_granted_return_off")
    assert not has(after_settings, "Open app settings"), "Permission shortcut remains after grant"
    assert not has(after_settings, "Microphone permission denied"), "Permission status remained denied after grant"
    granted_appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
    (out / "settings-granted-appops.txt").write_text(granted_appops)
    assert "(running)" not in granted_appops, granted_appops
    screenshot("settings_granted_return_off")
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
    close_recaps("close_recaps_before_support_report")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Voice check", "support_report_after_manual_meter_close")
    review_report("support_report_completed", "Check 1: Input samples observed\nStopped by you", share=True)
    review_report("support_report_completed_build_only", "Check 1: Input samples observed\nStopped by you", share=True, exclude=True)
    review_insights_recaps("insights_recaps_completed", ("Input samples observed", "Stopped by you"), report=True)
    tap("Live sound check. Try the phone microphone for 30 seconds", "meter_after_report_share")
    open_recaps("manual_recaps_after_support_share")
    wait_for_all(("Input samples observed", "Stopped by you"), "support_share_did_not_clear_recaps")
    tap("Clear recaps", "clear_manual_recaps")
    wait_for("No completed sound checks in this app session.", "recaps_cleared")
    screenshot("recaps_cleared")
    close_recaps("close_cleared_recaps")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    review_report("support_report_after_clear", "No completed sound checks in this app session.")
    review_report("support_report_empty_build_only", "No completed sound checks in this app session.", share=True, exclude=True)
    tap("Live sound check. Try the phone microphone for 30 seconds", "meter_after_cleared_report")

    tap("Start sound check", "insights_recaps_start_actual_check")
    wait_for("Microphone samples received", "insights_recaps_actual_input")
    tap("Stop sound check", "insights_recaps_stop_actual_check")
    wait_for_all(("Microphone stopped", "No live input", "Start sound check"), "insights_recaps_stopped")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Voice check", "insights_recaps_actual_meter_closed")
    review_insights_recaps("insights_recaps_clear", ("Input samples observed", "Stopped by you"), clear=True)
    tap("Live sound check. Try the phone microphone for 30 seconds", "meter_after_insights_clear")
    open_recaps("meter_recaps_after_insights_clear")
    wait_for("No completed sound checks in this app session.", "insights_clear_also_empty_in_meter")
    close_recaps("close_meter_recaps_after_insights_clear")

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

    close_recaps("close_before_voice_permission_fixture")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    review_report("support_report_new_process", "No completed sound checks in this app session.")
    review_insights_recaps("insights_recaps_new_process", ("No completed sound checks in this app session.",))
    # The stock emulator may have no on-device speech model. Ask for the real
    # microphone permission from the real Voice Activity through the test APK;
    # no recognition service or permission callback is replaced.
    adb("shell", "am", "force-stop", package)
    adb("shell", "pm", "revoke", package, "android.permission.RECORD_AUDIO")
    adb("shell", "pm", "clear-permission-flags", package, "android.permission.RECORD_AUDIO", "user-set", "user-fixed")
    consent_probe = subprocess.Popen(
        ["adb", "shell", "am", "instrument", "-w", "com.aqss.bodyguard.uiprobe/.VoicePermissionProbe"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        denied = tap("Don’t allow", "voice_permission_deny", optional=True) or tap("Don't allow", "voice_permission_deny_ascii", optional=True)
        assert denied, "Expected the real microphone permission dialog from the Voice fixture"
        wait_for_voice_permission_idle("Microphone permission denied", "voice_permission_denied_off")
        open_app_permission_settings("voice_permission_settings_denied", "com.aqss.bodyguard.prototype.InputAssistanceActivity")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        wait_for_voice_permission_idle("Microphone permission denied", "voice_settings_denied_return_off")
        voice_denied_appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
        (out / "voice-settings-denied-appops.txt").write_text(voice_denied_appops)
        assert "(running)" not in voice_denied_appops, voice_denied_appops
        screenshot("voice_settings_denied_return_off")
        open_app_permission_settings("voice_permission_settings_granted", "com.aqss.bodyguard.prototype.InputAssistanceActivity")
        adb("shell", "pm", "grant", package, "android.permission.RECORD_AUDIO")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        voice_granted = wait_for_voice_permission_idle("Permission granted. Tap Start when you are ready.", "voice_settings_granted_return_off")
        assert not has(voice_granted, "Open app settings"), "Voice Settings shortcut remains after native grant"
        assert not has(voice_granted, "Microphone permission denied"), "Voice permission guidance remained denied"
        voice_granted_appops = adb("shell", "cmd", "appops", "get", package, "RECORD_AUDIO").decode()
        (out / "voice-settings-granted-appops.txt").write_text(voice_granted_appops)
        assert "(running)" not in voice_granted_appops, voice_granted_appops
        screenshot("voice_settings_granted_return_off")
    finally:
        adb("shell", "run-as", package, "touch", "files/voice-permission-finish")
        try:
            consent_result, _ = consent_probe.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            consent_probe.kill(); consent_result, _ = consent_probe.communicate()
        (out / "voice-permission-fixture-contract.txt").write_text(consent_result)
    assert "voice_permission_fixture=passed:" in consent_result, consent_result

    crashes = adb("logcat", "-b", "crash", "-d").decode()
    (out / "crash-log.txt").write_text(crashes)
    assert "FATAL EXCEPTION" not in crashes, crashes
    print("LIVE_INPUT_EMULATOR_OBSERVED: Insights empty/completed recaps, Close/Back returns, cross-route Clear and process restart, native build-details preview/cancel/four-field share handoff, permission denial, app-specific Settings round trips with denied/granted access and no capture until another Start, PCM samples, manual stop, notification-shade focus loss, background stop, rotation stop, no automatic restart, 30-second limit, voice navigation/service attempt, real Voice microphone-denial/Settings fixture with denied and granted returns kept off, meter reuse, bounded input recaps, Clear, navigation retention, empty recaps after process restart, synthetic-photo picker/ML Kit review, over-budget photo rejection, photo Clear/cancel and unverified connection passed. No physical microphone, real-photo accuracy or output qualification.", flush=True)


if __name__ == "__main__":
    main()
