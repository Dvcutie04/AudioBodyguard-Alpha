#!/usr/bin/env python3
"""Install and inspect the live-input test in an isolated emulator; no acoustic claim."""
from pathlib import Path
import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
from android_frame_evidence import compare_frames


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", default="native/android/app/build/outputs/apk/liveInput/app-liveInput.apk")
    parser.add_argument("--package", default="com.aqss.bodyguard.prototype.liveinput")
    parser.add_argument("--probe-apk", default="native/android/uiprobe/build/outputs/apk/debug/uiprobe-debug.apk")
    parser.add_argument("--share-receiver-apk", default="native/android/sharereceiver/build/outputs/apk/debug/sharereceiver-debug.apk")
    args = parser.parse_args()
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
    wait_for_all(("Appearance", "Advanced Settings"), "build_details_return_to_settings")
    # Start with a genuinely fresh process: no completed input checks exist.
    tap("Advanced Settings", "support_report_advanced")
    for attempt in range(7):
        report_root, _ = screen(f"support_report_find_{attempt}")
        if any(n.get("content-desc") == "About Private support report" for n in report_root.iter("node")):
            break
        scroll_meter(f"support_report_scroll_{attempt}", down=True)
    tap("About Private support report", "support_report_open")
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
    tap("Back", "support_report_close")
    wait_for("Advanced Settings", "support_report_back_to_caller")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    wait_for("Appearance", "support_report_back_to_settings")
    print("SUPPORT_REPORT_SHARE_OBSERVED: empty allowlisted preview, native Cancel, exact Intent receipt and return to Advanced Settings", flush=True)
    tap("Home", "build_details_return_home")
    wait_for("Connection not verified", "build_details_home_still_unverified")
    def review_report(name, recap, share=False, exclude=False):
        expected = expected_share + "\n\nRecent sound checks (this app session)\n" + recap + "\n\nInput observations only; not proof of sound safety, protection or TV control."
        tap("Settings", name + "_settings")
        tap("Advanced Settings", name + "_advanced")
        for attempt in range(7):
            root, _ = screen(f"{name}_find_{attempt}")
            if any(n.get("content-desc") == "About Private support report" for n in root.iter("node")):
                break
            scroll_meter(f"{name}_scroll_{attempt}", down=True)
        tap("About Private support report", name + "_open")
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
        tap("Back", name + "_back")
        wait_for("Advanced Settings", name + "_caller")
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
            choose_photo_fixture(display_name, case_prefix)
            wait_for_all(expected,
                         f"{case_prefix}_native_ocr_result", attempts=30)
            screenshot(f"{case_prefix}_native_ocr_result")
            if case_prefix == "photo":
                # A newly opened selection replaces the old review even if cancelled.
                # Use the real picker, then prove the old VIZIO/model/IP do not return.
                tap("Choose a photo", "photo_replace_to_cancel")
                screen("photo_replacement_picker")
                adb("shell", "input", "keyevent", "KEYCODE_BACK")
                wait_for_all(("No photo selected", "Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified"),
                             "photo_replacement_cancel_empty")
                screenshot("photo_replacement_cancel_empty")
                choose_photo_fixture(display_name, "photo_reselect")
                wait_for_all(expected, "photo_reselect_native_ocr_result", attempts=30)
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
                                   "Selected playback route: Unknown", "Negotiated format: Unknown"),
                                  "output_inventory_idle")
    assert not has(inventory_idle, "Start sound check")
    tap("Refresh outputs", "output_inventory_refresh")
    inventory = wait_for_all(("available output device", "Snapshot only.",
                              "Selected playback route: Unknown", "Advertised sample rates:"),
                             "output_inventory_read")
    assert not has(inventory, "Output inventory unavailable")
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
    print("OUTPUT_INVENTORY_OBSERVED: explicit metadata refresh, route/format unknown, microphone permission unrequested, background/resume clears snapshot, Back/reopen clears snapshot; no playback or physical qualification", flush=True)
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
