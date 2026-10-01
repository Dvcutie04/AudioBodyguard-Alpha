"""Compare Android gfxinfo framestats snapshots without claiming action latency."""
import argparse
import csv
import json
import statistics
from pathlib import Path

SCOPE = "rendered frames; not touch-to-response or physical latency"

def _snapshot(text):
    columns = None
    frames = set()
    watermark = None
    for line in text.splitlines():
        fields = next(csv.reader([line]))
        if "Flags" in fields and "IntendedVsync" in fields and "FrameCompleted" in fields:
            columns = {name: i for i, name in enumerate(fields)}
            continue
        if columns is None:
            continue
        try:
            flag, start, end = (int(fields[columns[name]]) for name in ("Flags", "IntendedVsync", "FrameCompleted"))
        except (ValueError, IndexError):
            continue
        if flag != 0 or not 0 < start < 2**63 - 1:
            continue
        watermark = start if watermark is None else max(watermark, start)
        if start <= end < 2**63 - 1:
            frames.add((start, end))
    return watermark, frames

def compare_frames(before, after):
    cutoff, _ = _snapshot(before)
    _, frames = _snapshot(after)
    durations = sorted((end - start) / 1_000_000 for start, end in frames if cutoff is not None and start > cutoff)
    n = len(durations)
    return {
        "scope": SCOPE,
        "baseline_available": cutoff is not None,
        "frame_count": n,
        "durations_ms": durations,
        "median_ms": statistics.median(durations) if n else None,
        "maximum_ms": max(durations) if n else None,
        "warning": "Hosted renderer measurements do not qualify installed-phone smoothness or AQSS physical response.",
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = compare_frames(args.before.read_text(errors="replace"), args.after.read_text(errors="replace"))
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['frame_count']} new rendered frames; action/physical latency unqualified")

if __name__ == "__main__":
    main()
