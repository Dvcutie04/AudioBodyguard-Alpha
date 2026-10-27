#!/usr/bin/env python3
"""Compare an isolated Simulator's native Copy with its actual reviewed XCTest text."""
from pathlib import Path
import argparse
import hashlib
import json
import plistlib
import subprocess


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
            if name.startswith("Test setup reviewed text") and "payloadRef" in value:
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
    assert len(payloads) == 1, "Require one actual reviewed text attachment from the Copy test"
    expected_file = args.output / "reviewed.txt"
    subprocess.run(["xcrun", "xcresulttool", "export", "--type", "file", "--path", str(args.result),
                    "--id", payloads.pop(), "--output-path", str(expected_file)], check=True)
    expected = expected_file.read_bytes()
    observed = subprocess.check_output(["xcrun", "simctl", "pbpaste", args.simulator], timeout=20)
    assert observed == expected, "Native clipboard differs from the exact reviewed text"
    text = expected.decode("utf-8")
    info = plistlib.loads(args.app_info.read_bytes())
    metadata = ("Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: " + info["CFBundleShortVersionString"] +
                "\nBuild: " + info["CFBundleVersion"])
    assert text.startswith("Audio Bodyguard test setup (v1)\n") and metadata in text
    assert "Actual playback route: Unknown" in text and "Physical output and protection: Not verified" in text
    assert len(text.encode("utf-16-le")) // 2 <= 4096 and len(expected) <= 8192
    receipt = {"text": text, "exact_preview_match": True, "bytes": len(expected),
               "sha256": hashlib.sha256(expected).hexdigest(), "scope": "Simulator native Copy only; no physical qualification"}
    (args.output / "test-setup-copy-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("TEST_SETUP_COPY_EXACT " + json.dumps({k: v for k, v in receipt.items() if k != "text"}, sort_keys=True))


if __name__ == "__main__":
    main()
