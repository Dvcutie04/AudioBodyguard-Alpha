"""Inspect the hierarchy of an actually launched read-only Android emulator app."""

import sys
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def valid_hierarchy(path: str) -> bool:
    try:
        root = ET.parse(Path(path)).getroot()
    except (ET.ParseError, FileNotFoundError):
        return False
    return root.tag == "hierarchy" and any(node.tag == "node" for node in root.iter())


def launcher_close_coordinates(path: str) -> None:
    nodes = list(ET.parse(Path(path)).getroot().iter())
    launcher_titles = {"Pixel Launcher isn't responding", "Quickstep isn't responding"}
    if not any(node.get("package") == "android" and node.get("text") in launcher_titles for node in nodes):
        return
    close = next((node for node in nodes if node.get("text") == "Close app"), None)
    close_bounds = close.get("bounds", "") if close is not None else ""
    bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", close_bounds)
    if bounds is None:
        raise SystemExit("System launcher dialog has no inspectable Close app button")
    left, top, right, bottom = map(int, bounds.groups())
    print((left + right) // 2, (top + bottom) // 2)


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
    launcher_titles = ("Pixel Launcher isn't responding", "Quickstep isn't responding")
    if any(title in text for text in labels for title in launcher_titles):
        raise SystemExit("Android emulator system launcher ANR obscured the AQSS UI; inspect the saved screenshot")
    missing = [label for label in expected if not any(label in text for text in labels)]
    if missing:
        raise SystemExit(f"Android emulator UI missing expected labels: {missing}")
    print("ANDROID_SIMULATION_UI_OBSERVED: launch and uncertainty labels visible")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--valid-hierarchy":
        raise SystemExit(0 if valid_hierarchy(sys.argv[2]) else 1)
    if len(sys.argv) == 3 and sys.argv[1] == "--launcher-close-coordinates":
        launcher_close_coordinates(sys.argv[2])
        raise SystemExit(0)
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_android_simulation_ui.py TOP.xml BOTTOM.xml")
    main(sys.argv[1:])
