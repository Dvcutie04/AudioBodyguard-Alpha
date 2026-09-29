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


def button_coordinates(path: str, label: str) -> None:
    nodes = list(ET.parse(Path(path)).getroot().iter())
    parents = {child: parent for parent in nodes for child in parent}
    def actionable(node):
        # Illustration labels can say Next/Close too. Only a real control or
        # a label inside a clickable row may receive the navigation tap.
        current = node
        while current is not None:
            if current.get("enabled") == "false":
                return False
            if current.get("clickable") == "true" or current.get("class", "").endswith("Button"):
                return True
            current = parents.get(current)
        return False
    button = next((node for node in nodes if (node.get("text", "").casefold() == label.casefold() or node.get("content-desc", "").casefold() == label.casefold()) and node.get("package") == "com.aqss.bodyguard.prototype" and actionable(node)), None)
    bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", button.get("bounds", "")) if button is not None else None
    if bounds is not None:
        left, top, right, bottom = map(int, bounds.groups())
        # A hierarchy can report a clickable row at the screen edge even
        # when a tap there is intercepted by Android's system navigation.
        screen_bottom = max(
            (int(match.group(4)) for node in nodes
             if (match := re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", "")))),
            default=0,
        )
        center_y = (top + bottom) // 2
        # A native dialog reports its own window bounds, not the full display.
        # Its lower rows are still safely above system navigation.
        native_dialog = any(node.get("resource-id") == "android:id/alertTitle" for node in nodes)
        # Tutorial footer controls are laid out above consumed system insets.
        footer_labels = {"Jump to", "Help & tutorials", "Back", "Begin", "Next", "Done", "Start guide", "Finish guide", "Return to step", "Open Voice check", "Open full app", "Exit tutorial", "Close tutorial", "Help", "Home", "Sound", "Devices", "Insights", "Settings", "Pages · Home", "Pages · Devices", "Pages · Settings"}
        if center_y < screen_bottom * 0.85 or label in footer_labels or native_dialog:
            print((left + right) // 2, center_y)


def main(paths: list[str], *, options: bool = False) -> None:
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
        "SIMULATION · No audio path connected",
        "Unknown physical state",
        "No output observation",
        "Six setup checks unknown",
        "No supported endpoint or verified transfer path",
    ) if not options else (
        "Sound options",
        "Volume",
        "Unavailable",
        "Dialogue preset",
        "Night preset",
        "Unknown physical state",
        "No independent observation is available",
        "Background monitoring",
    )
    launcher_titles = ("Pixel Launcher isn't responding", "Quickstep isn't responding")
    if any(title in text for text in labels for title in launcher_titles):
        raise SystemExit("Android emulator system launcher ANR obscured the AQSS UI; inspect the saved screenshot")
    missing = [label for label in expected if not any(label in text for text in labels)]
    if missing:
        raise SystemExit(f"Android emulator UI missing expected labels: {missing}")
    print("ANDROID_SIMULATION_UI_OBSERVED: " + ("read-only options visible" if options else "launch and uncertainty labels visible"))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--assert-tutorial-target":
        nodes = list(ET.parse(Path(sys.argv[2])).getroot().iter())
        def bounds(node):
            match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", ""))
            return tuple(map(int, match.groups())) if match else None
        panels = [bounds(node) for node in nodes if node.get("text", "").startswith("Tutorial — ")]
        panel = next((b for b in panels if b), None)
        target = next((node for node in nodes if node.get("text") == sys.argv[3]), None)
        box = bounds(target) if target is not None else None
        separated = box is not None and panel is not None and (box[3] <= panel[1] or box[2] <= panel[0])
        # UiAutomator may retain a heading clipped to a single pixel. Such a
        # sliver is not a readable highlighted target on this emulator matrix.
        if box is None or box[3] - box[1] < 32 or box[2] - box[0] < 32 or not separated:
            raise SystemExit(f"Tutorial target is not visible beside or above its guide: {sys.argv[3]}")
        raise SystemExit(0)
    if len(sys.argv) == 4 and sys.argv[1] == "--assert-label":
        nodes = ET.parse(Path(sys.argv[2])).getroot().iter()
        if not any(sys.argv[3] in (node.get("text", "") + node.get("content-desc", "")) for node in nodes):
            raise SystemExit(f"Android tutorial missing label: {sys.argv[3]}")
        raise SystemExit(0)
    if len(sys.argv) == 3 and sys.argv[1] == "--valid-hierarchy":
        raise SystemExit(0 if valid_hierarchy(sys.argv[2]) else 1)
    if len(sys.argv) == 3 and sys.argv[1] == "--launcher-close-coordinates":
        launcher_close_coordinates(sys.argv[2])
        raise SystemExit(0)
    if len(sys.argv) == 4 and sys.argv[1] == "--text-tap-coordinates":
        button_coordinates(sys.argv[2], sys.argv[3])
        raise SystemExit(0)
    if len(sys.argv) >= 4 and sys.argv[1] == "--options-menu":
        main(sys.argv[2:], options=True)
        raise SystemExit(0)
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_android_simulation_ui.py TOP.xml BOTTOM.xml")
    main(sys.argv[1:])
