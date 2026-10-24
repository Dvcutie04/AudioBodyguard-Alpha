"""Compare Android gfxinfo framestats snapshots without claiming action latency."""
import argparse
import csv
import json
import re
import statistics
from pathlib import Path

SCOPE = "rendered frames; not touch-to-response or physical latency"

def _process_identity(text):
    identities = set()
    for line in text.splitlines():
        if not line.lstrip().startswith("** Graphics info for pid"):
            continue
        match = re.fullmatch(r"\*\* Graphics info for pid ([1-9][0-9]*) \[([^\[\]\r\n]+)\] \*\*", line.strip())
        if match is None or not match.group(2).strip():
            return None  # A malformed additional header cannot be ignored.
        identities.add((match.group(1), match.group(2).strip()))
    return next(iter(identities)) if len(identities) == 1 else None

def _snapshot(text):
    columns = None
    frames = set()
    watermark = None
    invalid = set()
    clock = re.search(r"(?m)^Uptime:\s*(\d+)", text)
    uptime_ms = int(clock.group(1)) if clock else None
    # A generous diagnostic horizon tolerates dump collection after its header.
    # Samples outside it are unknown, never clipped into an apparently fast frame.
    horizon = (uptime_ms + 60_000) * 1_000_000 if uptime_ms is not None else None
    for line in text.splitlines():
        fields = next(csv.reader([line]))
        if "Flags" in fields and "IntendedVsync" in fields and "FrameCompleted" in fields:
            columns = {name: i for i, name in enumerate(fields)}
            continue
        if columns is None:
            continue
        try:
            flag, start = (int(fields[columns[name]]) for name in ("Flags", "IntendedVsync"))
        except (ValueError, IndexError):
            continue
        if flag != 0 or not 0 < start < 2**63 - 1:
            continue
        try:
            end = int(fields[columns["FrameCompleted"]])
        except (ValueError, IndexError):
            end = None
        if horizon is not None and start > horizon:
            invalid.add((start, end))
            continue
        watermark = start if watermark is None else max(watermark, start)
        if end is None:
            # The start is still observed; an unreadable completion is not an
            # absent frame or a duration, and must not qualify a new interval.
            invalid.add((start, None))
            continue
        if end == 0:
            continue  # In-flight or unpopulated completion, not a duration.
        if not start < end < 2**63 - 1 or end - start > 60_000_000_000 or (horizon is not None and end > horizon):
            invalid.add((start, end))
        else:
            frames.add((start, end))
    return watermark, frames, invalid, uptime_ms, _process_identity(text)

def compare_frames(before, after):
    cutoff, _, _, before_uptime, before_process = _snapshot(before)
    _, frames, invalid, after_uptime, after_process = _snapshot(after)
    identities_available = before_process is not None and after_process is not None
    identities_match = identities_available and before_process == after_process
    clocks_available = before_uptime is not None and after_uptime is not None
    uptime_order_valid = clocks_available and after_uptime >= before_uptime
    uptime_regressed = clocks_available and not uptime_order_valid
    invalid_count = sum(1 for start, _ in invalid if cutoff is not None and start > cutoff)
    qualified = cutoff is not None and identities_match and uptime_order_valid and not invalid_count
    # A known regression invalidates attribution even if each dump's rows are
    # individually plausible. An unknown or changed process also has no common
    # frame scope. Preserve the raw dumps instead of attributing those samples.
    durations = sorted((end - start) / 1_000_000 for start, end in frames
                       if identities_match and not uptime_regressed and cutoff is not None and start > cutoff)
    n = len(durations)
    return {
        "scope": SCOPE,
        "baseline_available": cutoff is not None,
        "frame_count": n,
        "invalid_timing_count": invalid_count,
        "clock_bound_available": clocks_available,
        "uptime_order_valid": uptime_order_valid,
        "process_identity_available": identities_available,
        "process_identity_matches": identities_match,
        "timing_qualified": bool(qualified and n),
        "diagnostic_horizon_ms": 60_000,
        "durations_ms": durations,
        "median_ms": statistics.median(durations) if n and qualified else None,
        "maximum_ms": max(durations) if n and qualified else None,
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
