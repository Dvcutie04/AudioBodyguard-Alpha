#!/usr/bin/env python3
"""Native quiet-check observer; no acoustic or physical qualification."""
import base64
import json
import re
import subprocess
from pathlib import Path


def adb(*args, timeout=120):
    return subprocess.check_output(["adb", *args], timeout=timeout)


def main():
    package = "com.aqss.bodyguard.prototype.liveinput"
    out = Path("artifacts/ui/android-live-input")
    out.mkdir(parents=True, exist_ok=True)
    installed = adb("shell", "dumpsys", "package", package).decode()
    version = re.search(r"^\s*versionName=(.+)$", installed, re.MULTILINE).group(1).strip()
    build = re.search(r"^\s*versionCode=(\d+)\b", installed, re.MULTILINE).group(1)
    try:
        for label, scale in (("normal", "1.0"), ("large", "1.5")):
            adb("shell", "settings", "put", "system", "font_scale", scale)
            adb("shell", "am", "force-stop", package)
            adb("shell", "pm", "revoke", package, "android.permission.RECORD_AUDIO")
            adb("logcat", "-b", "crash", "-c")
            observation = adb("shell", "am", "instrument", "-w", "-e", "quiet_setup", "1",
                              "com.aqss.bodyguard.uiprobe/.QuietOutputProbe").decode()
            (out / f"quiet-output-{label}.txt").write_text(observation)
            if "INSTRUMENTATION_RESULT: quiet_output=passed:" not in observation:
                (out / f"quiet-output-{label}-crash.txt").write_bytes(adb("logcat", "-b", "crash", "-d", "-t", "200"))
                try:
                    (out / f"quiet-output-{label}-failure.png").write_bytes(
                        adb("exec-out", "run-as", package, "cat", "files/quiet-output-failure.png"))
                except subprocess.CalledProcessError:
                    pass
                raise AssertionError(observation)
            assert "INSTRUMENTATION_RESULT: quiet_setup=passed:" in observation
            joined_match = re.search(r"^INSTRUMENTATION_RESULT: quiet_setup_b64=(.+)$", observation, re.MULTILINE)
            assert joined_match, "Missing actual combined quiet/setup preview"
            joined = base64.b64decode(joined_match.group(1).strip(), validate=True).decode("utf-8")
            assert joined.startswith("Audio Bodyguard test setup (v2)") and "Attached quiet check report" in joined
            (out / f"quiet-setup-{label}-report.txt").write_text(joined)
            for name in ("report", "rotated", "removed"):
                (out / f"quiet-setup-{label}-{name}.png").write_bytes(
                    adb("exec-out", "run-as", package, "cat", f"files/quiet-setup-{name}.png"))
            encoded = re.search(r"^INSTRUMENTATION_RESULT: quiet_report_b64=(.+)$", observation, re.MULTILINE)
            assert encoded, "No reviewed native report returned"
            report = base64.b64decode(encoded.group(1).strip(), validate=True).decode("utf-8")
            assert f"Version: {version}\nBuild: {build}" in report
            assert joined.endswith(report), "Combined report differs from its original quiet snapshot"
            assert "Physical output and protection: Not verified" in report
            assert version == "0.37-quiet-setup-live-input" and build == "40"
            (out / f"quiet-output-{label}-report.txt").write_text(report)
            for name in ("busy", "main", "report", "rotated"):
                (out / f"quiet-output-{label}-{name}.png").write_bytes(
                    adb("exec-out", "run-as", package, "cat", f"files/quiet-output-{name}.png"))
            permissions = adb("shell", "dumpsys", "package", package).decode()
            assert "android.permission.RECORD_AUDIO: granted=false" in permissions
        (out / "quiet-output-summary.json").write_text(json.dumps({
            "version": version, "build": build, "font_scales": [1.0, 1.5],
            "scope": "Actual emulator framework stream, synthetic input exclusion and exact cancelled share intent; no acoustic/physical qualification",
        }, indent=2) + "\n")
        print("QUIET_OUTPUT_OBSERVED: native framework, input exclusion, cleanup, frozen share intent, rotation, large text and Back passed; physical output unverified", flush=True)
    finally:
        adb("shell", "settings", "put", "system", "font_scale", "1.0")


if __name__ == "__main__":
    main()
