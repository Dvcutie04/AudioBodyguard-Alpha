#!/usr/bin/env python3
"""Check visible emulator UI only; these labels provide no physical evidence."""

import sys
from xml.etree import ElementTree


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_android_simulation_screen.py <uiautomator-xml>", file=sys.stderr)
        return 2
    try:
        root = ElementTree.parse(sys.argv[1]).getroot()
    except (OSError, ElementTree.ParseError) as exc:
        print(f"ANDROID_SIMULATION_UI_UNREADABLE: {exc}", file=sys.stderr)
        return 1

    visible = [node.get("text", "") for node in root.iter()]
    expected = (
        "SIMULATION — no audio path connected",
        "Unknown physical state",
        "No output observation",
        "Six setup checks unknown",
    )
    missing = [label for label in expected if not any(label in text for text in visible)]
    if missing:
        print(f"ANDROID_SIMULATION_UI_MISSING: {missing!r}", file=sys.stderr)
        return 1
    print("ANDROID_SIMULATION_UI_VISIBLE_PHYSICAL_UNVERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
