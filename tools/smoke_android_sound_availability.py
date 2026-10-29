#!/usr/bin/env python3
"""Native microphone availability presentation; synthetic leases, no physical qualification."""
import base64
import json
import re
import subprocess
from pathlib import Path


def adb(*args):
    return subprocess.check_output(["adb", *args], timeout=90)


def main():
    package = "com.aqss.bodyguard.prototype.liveinput"
    out = Path("artifacts/ui/android-live-input")
    out.mkdir(parents=True, exist_ok=True)
    installed = adb("shell", "dumpsys", "package", package).decode()
    version = re.search(r"^\s*versionName=(.+)$", installed, re.MULTILINE).group(1).strip()
    build = re.search(r"^\s*versionCode=(\d+)\b", installed, re.MULTILINE).group(1)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    try:
        for label, scale in (("normal", "1.0"), ("large", "1.5")):
            adb("shell", "settings", "put", "system", "font_scale", scale)
            for permission in ("missing", "granted"):
                name = f"sound-availability-{label}-{permission}"
                adb("shell", "am", "force-stop", package)
                adb("shell", "pm", "grant" if permission == "granted" else "revoke", package, "android.permission.RECORD_AUDIO")
                adb("logcat", "-b", "crash", "-c")
                observation = adb("shell", "am", "instrument", "-w", "com.aqss.bodyguard.uiprobe/.SoundAvailabilityProbe").decode()
                (out / f"{name}.txt").write_text(observation)
                if "INSTRUMENTATION_RESULT: sound_availability=passed:" not in observation:
                    (out / f"{name}-crash.txt").write_bytes(adb("logcat", "-b", "crash", "-d", "-t", "200"))
                    try:
                        (out / f"{name}-failure.png").write_bytes(adb("exec-out", "run-as", package, "cat", "files/sound-availability-failure.png"))
                    except subprocess.CalledProcessError:
                        pass
                    raise AssertionError(observation)
                encoded = re.search(r"^INSTRUMENTATION_RESULT: sound_availability_report_b64=(.+)$", observation, re.MULTILINE)
                assert encoded, "Missing actual historical support report preview"
                report = base64.b64decode(encoded.group(1).strip(), validate=True).decode("utf-8")
                assert f"Version: {version}\nBuild: {build}" in report
                assert "Check 1: No input samples observed\nStopped by you" in report
                (out / f"{name}-report.txt").write_text(report)
                for state in ("busy", "released", "blocked", "report"):
                    (out / f"{name}-{state}.png").write_bytes(adb("exec-out", "run-as", package, "cat", f"files/sound-availability-{state}.png"))
                permissions = adb("shell", "dumpsys", "package", package).decode()
                assert f"android.permission.RECORD_AUDIO: granted={str(permission == 'granted').lower()}" in permissions
        (out / "sound-availability-summary.json").write_text(json.dumps({
            "source_commit": revision, "version": version, "build": build,
            "font_scales": [1.0, 1.5], "microphone_permission": ["missing", "granted"],
            "scope": "Synthetic process reservations/quarantine and historical recap; actual native screen/permission/share actions, no delayed recorder, real cleanup failure or physical qualification",
        }, indent=2) + "\n")
        print("SOUND_AVAILABILITY_OBSERVED: both font/permission states passed; synthetic ownership/quarantine, no microphone allocation, exact historical sharing and manual-only retry", flush=True)
    finally:
        adb("shell", "settings", "put", "system", "font_scale", "1.0")
        adb("shell", "am", "force-stop", package)
        adb("shell", "pm", "revoke", package, "android.permission.RECORD_AUDIO")


if __name__ == "__main__":
    main()
