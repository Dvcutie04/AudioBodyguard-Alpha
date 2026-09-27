"""Inspect the hierarchy of an actually launched read-only Android emulator app."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main(paths: list[str]) -> None:
    labels = []
    for path in paths:
        root = ET.parse(Path(path)).getroot()
        labels.extend(
            value
            for node in root.iter()
            for value in (node.get("text", ""), node.get("content-desc", ""))
            if value
        )

    expected = (
        "SIMULATION — no audio path connected",
        "Unknown physical state",
        "No output observation",
        "Six setup checks unknown",
        "Moving a session between phones is not available here",
    )
    missing = [label for label in expected if not any(label in text for text in labels)]
    if missing:
        raise SystemExit(f"Android emulator UI missing expected labels: {missing}")
    print("ANDROID_SIMULATION_UI_OBSERVED: launch and uncertainty labels visible")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_android_simulation_ui.py TOP.xml BOTTOM.xml")
    main(sys.argv[1:])
