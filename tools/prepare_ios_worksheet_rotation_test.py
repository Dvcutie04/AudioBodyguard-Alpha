#!/usr/bin/env python3
"""Prepare an attributed XCTest-only rotation synchronization repair.

The compiled application is unchanged. The original test blob is pinned, every
existing assertion and timeout is preserved, and both test-source hashes are
retained. This temporary generation step must be folded into the source when a
full repository checkout is available; it must never silently patch other input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_BLOB = "61db35e8647b1c95cb241859d4e7dc6f7b728e7b"
ANCHOR = '''        XCUIDevice.shared.orientation = .landscapeLeft
        app.buttons["test-setup-review"].tap()
        XCTAssertTrue(preview.waitForExistence(timeout: 5)); let reviewed = preview.label
'''
REPLACEMENT = '''        XCUIDevice.shared.orientation = .landscapeLeft
        // A preserved iPad 18.5 failure tapped an intermediate rotation frame
        // (471.7 x 271.9), not the settled Review control (541 x 61).
        // Observe stable, hittable geometry before the one original tap.
        // No retries, fixed sleeps or changes to the five-second preview check.
        let reviewAfterRotation = app.buttons["test-setup-review"]
        var previousLayout: (window: CGRect, button: CGRect)?
        var stableSince: TimeInterval?
        var readinessSamples = 0
        var lastReadiness = "No review geometry observed"
        let layoutReady = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            guard reviewAfterRotation.exists, reviewAfterRotation.isEnabled,
                  reviewAfterRotation.isHittable else {
                lastReadiness = "Review not present, enabled and hittable"
                previousLayout = nil; stableSince = nil; return false
            }
            let window = app.frame
            let button = reviewAfterRotation.frame
            readinessSamples += 1
            lastReadiness = "Sample \\(readinessSamples): window=\\(window), review=\\(button)"
            let dimensions = [window.minX, window.minY, window.width, window.height,
                              button.minX, button.minY, button.width, button.height]
            guard dimensions.allSatisfy({ $0.isFinite }), window.width > window.height,
                  window.height > 0, button.width >= 44, button.height >= 44,
                  window.contains(button) else {
                lastReadiness += "; geometry not landscape, in-bounds and at least 44pt"
                previousLayout = nil; stableSince = nil; return false
            }
            let now = ProcessInfo.processInfo.systemUptime
            guard let previous = previousLayout, previous.window == window,
                  previous.button == button, let since = stableSince else {
                lastReadiness += "; awaiting matching subsequent frame"
                previousLayout = (window, button); stableSince = now; return false
            }
            lastReadiness += "; matching frame for \\(now - since) seconds"
            return now >= since && now - since >= 0.25
        }, object: nil)
        guard XCTWaiter.wait(for: [layoutReady], timeout: 3) == .completed else {
            screenshot("Worksheet rotation did not settle before Review", app)
            XCTFail("Require stable landscape Review geometry before the first tap; last observation: \\(lastReadiness). \\(app.debugDescription)")
            return
        }
        reviewAfterRotation.tap()
        XCTAssertTrue(preview.waitForExistence(timeout: 5)); let reviewed = preview.label
'''


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def transform(data: bytes, expected_blob: str = EXPECTED_BLOB) -> bytes:
    if git_blob_sha(data) != expected_blob:
        raise ValueError("Unexpected test-source blob; refusing to modify a different revision")
    original = data.decode("utf-8")
    if original.count(ANCHOR) != 1:
        raise ValueError("Require exactly one preserved worksheet rotation sequence")
    repaired = original.replace(ANCHOR, REPLACEMENT, 1)
    # The only deletion is the original single tap, replaced by a single tap
    # after readiness. All existing test assertions and timeouts remain bytes.
    if repaired.replace(REPLACEMENT, ANCHOR, 1) != original:
        raise ValueError("Test repair changed unrelated source")
    return repaired.encode("utf-8")


def prepare(source: Path, receipt: Path, expected_blob: str = EXPECTED_BLOB) -> None:
    original = source.read_bytes()
    repaired = transform(original, expected_blob)
    provenance = {
        "scope": "XCTest-only generated source; application bytes unchanged",
        "source_path": source.as_posix(),
        "original_test_blob": git_blob_sha(original),
        "compiled_test_blob": git_blob_sha(repaired),
        "original_test_sha256": hashlib.sha256(original).hexdigest(),
        "compiled_test_sha256": hashlib.sha256(repaired).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "existing_assertions_preserved": True,
        "preview_timeout_seconds": 5,
        "layout_readiness_timeout_seconds": 3,
        "action_count": 1,
        "native_execution": "UNRUN at source preparation",
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    source.write_bytes(repaired)
    print(json.dumps(provenance, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.receipt)


if __name__ == "__main__":
    main()
