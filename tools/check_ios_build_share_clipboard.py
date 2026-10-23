#!/usr/bin/env python3
"""Check only an isolated Simulator's actual clipboard around native share tests."""
from pathlib import Path
import argparse
import json
import plistlib
import subprocess

FIXTURE = b"AQSS isolated build-share cancel fixture"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "cancel", "copy", "clear"))
    parser.add_argument("simulator")
    parser.add_argument("--app-info", type=Path)
    parser.add_argument("--support-report", action="store_true")
    parser.add_argument("--completed-check", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    def simctl(*command, data=None):
        call = subprocess.run(["xcrun", "simctl", *command], input=data,
                              capture_output=True, timeout=20, check=True)
        return call.stdout

    if args.mode == "prepare":
        # The installed Xcode's own help is the primary subcommand contract.
        for command in ("pbcopy", "pbpaste"):
            help_call = subprocess.run(["xcrun", "simctl", "help", command],
                                       capture_output=True, timeout=20, check=True)
            (args.output / (command + "-help.txt")).write_bytes(help_call.stdout + help_call.stderr)
        simctl("pbcopy", args.simulator, data=FIXTURE)
        assert simctl("pbpaste", args.simulator) == FIXTURE, "Require a working, isolated clipboard fixture"
        print("BUILD_SHARE_CLIPBOARD_PREPARED")
    elif args.mode == "cancel":
        observed = simctl("pbpaste", args.simulator)
        assert observed == FIXTURE, repr(observed)
        result = {"cancel_preserved": True, "fixture": FIXTURE.decode("utf-8")}
        (args.output / "build-share-cancel-clipboard.json").write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
        print("BUILD_SHARE_CANCEL_CLIPBOARD_UNCHANGED")
    elif args.mode == "copy":
        assert args.app_info is not None, "Require the independently compiled app Info.plist"
        info = plistlib.loads(args.app_info.read_bytes())
        version, build = (info.get(key) for key in ("CFBundleShortVersionString", "CFBundleVersion"))
        assert all(isinstance(value, str) and value for value in (version, build))
        expected = f"Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: {version}\nBuild: {build}".encode("utf-8")
        if args.support_report:
            recap = "Check 1: Input samples observed\nStopped by you" if args.completed_check else "No completed sound checks in this app session."
            expected += ("\n\nRecent sound checks (this app session)\n" + recap + "\n\nInput observations only; not proof of sound safety, protection or TV control.").encode("utf-8")
        observed = simctl("pbpaste", args.simulator)
        assert observed == expected, {"observed": repr(observed), "expected": repr(expected)}
        result = {"text": observed.decode("utf-8"), "platform": "iPhone/iPad", "version": version, "build": build}
        (args.output / "build-share-copy-clipboard.json").write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
        print("BUILD_SHARE_COPY_CLIPBOARD_EXACT " + json.dumps(result, sort_keys=True))
    else:
        simctl("pbcopy", args.simulator, data=b"")
        print("BUILD_SHARE_CLIPBOARD_FIXTURE_CLEARED")

if __name__ == "__main__":
    main()
