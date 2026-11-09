#!/usr/bin/env python3
"""Compare Simulator native Copy against exact rejected VIZIO report attached by XCTest."""
from pathlib import Path
import argparse
import hashlib
import json
import plistlib
import subprocess

if __package__:
    from .check_ios_build_share_clipboard import simctl_clipboard
else:
    from check_ios_build_share_clipboard import simctl_clipboard


def validate_reviewed_text(text, info):
    version, build = info["CFBundleShortVersionString"], info["CFBundleVersion"]
    assert isinstance(version, str) and version and isinstance(build, str) and build
    metadata = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: {}\nBuild: {}".format(version, build)
    assert text.startswith("Audio Bodyguard connection trial (v1)\n")
    assert "\n" + metadata + "\n" in text, "Must identify actual compiled build"
    assert "\nOutcome: ADDRESS_REJECTED\n" in text
    assert "No native check started: the entered address was rejected." in text
    assert "No TV command or audio was sent by this check." in text
    for claim in ("TV identity: Not verified", "TV pairing: Not verified", "Audio protection: Not verified",
                  "Reviewing or sharing this text does not authorize a device action."):
        assert claim in text, "Must preserve unverified state and nonauthority"
    for leaked in ("8.8.8.8", "192.168.", "10.0.0.", "Wi-Fi password:"):
        assert leaked not in text, "No network details in the review"
    assert len(text.encode("utf-16-le")) // 2 <= 8192 and len(text.encode("utf-8")) <= 16384
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("simulator")
    parser.add_argument("result", type=Path)
    parser.add_argument("app_info", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    seen, payloads = set(), set()

    def get(identifier=None):
        command = ["xcrun", "xcresulttool", "get", "--path", str(args.result), "--format", "json"]
        if identifier:
            command += ["--id", identifier]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            result = subprocess.run(command + ["--legacy"], capture_output=True, text=True)
        result.check_returncode()
        return json.loads(result.stdout)

    def walk(value):
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            name = value.get("name", {}).get("_value", "")
            if name.startswith("VIZIO rejected network reviewed text") and "payloadRef" in value:
                payloads.add(value["payloadRef"]["id"]["_value"])
            for key, item in value.items():
                if key in ("testsRef", "summaryRef") and isinstance(item, dict):
                    identifier = item.get("id", {}).get("_value")
                    if identifier and identifier not in seen:
                        seen.add(identifier)
                        walk(get(identifier))
                else:
                    walk(item)

    walk(get())
    assert len(payloads) == 1, "Require one actual reviewed attachment"
    reviewed = args.output / "reviewed-vizio-report.txt"
    subprocess.run(["xcrun", "xcresulttool", "export", "--legacy", "--type", "file",
                    "--path", str(args.result), "--id", payloads.pop(), "--output-path", str(reviewed)], check=True)
    expected = reviewed.read_bytes()
    assert simctl_clipboard(args.simulator) == expected, "Clipboard differs from exact reviewed bytes"
    validate_reviewed_text(expected.decode("utf-8"), plistlib.loads(args.app_info.read_bytes()))
    receipt = {"exact_preview_match": True, "bytes": len(expected),
               "sha256": hashlib.sha256(expected).hexdigest(),
               "scope": "Simulator rejected public address; no physical TV contact"}
    (args.output / "vizio-copy.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("VIZIO_NATIVE_COPY_EXACT " + json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
