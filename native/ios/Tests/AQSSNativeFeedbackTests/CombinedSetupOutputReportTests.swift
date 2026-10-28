import XCTest
@testable import AQSSNativeFeedback

final class CombinedSetupOutputReportTests: XCTestCase {
    private let build = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: 0.38.0\nBuild: 1"
    private let clock: Int64 = 1_793_116_800_000
    private func output(_ types: [IOSOutputKind] = [.speaker], details: String? = nil,
                        total: Int? = nil) throws -> OutputDetailsSnapshot {
        try OutputDetailsSnapshot.capture(buildDetails: details ?? build, osVersion: "26.0.1",
            portTypes: types, totalReported: total ?? types.count, capturedAtMillis: clock)
    }
    private func report(_ source: OutputDetailsSnapshot?, notes: [TestSetupField: String] = [:],
                        details: String? = nil, time: Int64? = nil) throws -> TestSetupReportSnapshot {
        try TestSetupReportSnapshot.capture(buildDetails: details ?? build, notes: notes,
            reviewedAtMillis: time ?? clock + 300_000, outputDetails: source)
    }

    func testNoSnapshotPreservesOriginalWorksheetEnvelopeAndLimits() throws {
        let plain = try TestSetupReportSnapshot.capture(buildDetails: build, notes: [:], reviewedAtMillis: clock + 300_000)
        let explicit = try report(nil)
        XCTAssertEqual(plain.text, explicit.text); XCTAssertTrue(plain.text.hasPrefix("Audio Bodyguard test setup (v1)\n"))
        XCTAssertEqual(plain.reviewNotice, TestSetupReportSnapshot.notice)
        XCTAssertFalse(plain.text.contains("Included output details"))
    }

    func testTypedSnapshotIsIncludedVerbatimOnceUnderSeparateHeading() throws {
        let source = try output([.speaker, .headphones])
        let combined = try report(source, notes: [.intendedOutput: "Phone speaker"])
        XCTAssertTrue(combined.text.hasPrefix("Audio Bodyguard test setup (v2)\n"))
        XCTAssertTrue(combined.text.contains("Included output details (historical snapshot)"))
        XCTAssertTrue(combined.text.hasSuffix(source.text))
        XCTAssertEqual(combined.text.components(separatedBy: source.text).count, 2)
        XCTAssertTrue(combined.text.contains("Intended output: \"Phone speaker\""))
        XCTAssertEqual(combined.reviewNotice, "Setup notes and session details. Nothing is verified.")
    }

    func testOriginalCaptureAndLaterNotesReviewKeepSeparateClockLabels() throws {
        let text = try report(output()).text
        XCTAssertTrue(text.contains("Notes reviewed at (phone clock, UTC): 2026-10-27T16:05:00.000Z"))
        XCTAssertTrue(text.contains("Captured at (phone clock, UTC): 2026-10-27T16:00:00.000Z"))
        XCTAssertTrue(text.contains("Physical output and protection: Not verified"))
        XCTAssertTrue(text.contains("Actual playback route: Unknown"))
        XCTAssertTrue(text.contains("Playback/capture consent: Not collected"))
    }

    func testDifferentInstalledBuildCannotBeMixedIntoOneReport() throws {
        let old = try output(details: build.replacingOccurrences(of: "0.38.0", with: "0.37.0"))
        XCTAssertThrowsError(try report(old)) { XCTAssertEqual($0 as? TestSetupReportError, .invalidOutput) }
    }

    func testCanonicalUnicodeEqualityCannotHideDifferentBuildBytes() throws {
        let composed = build.replacingOccurrences(of: "0.38.0", with: "Caf\u{00e9}")
        let decomposed = build.replacingOccurrences(of: "0.38.0", with: "Cafe\u{0301}")
        XCTAssertEqual(composed, decomposed)
        XCTAssertFalse(composed.utf8.elementsEqual(decomposed.utf8))
        let source = try output(details: composed)
        XCTAssertThrowsError(try report(source, details: decomposed)) { XCTAssertEqual($0 as? TestSetupReportError, .invalidOutput) }
    }

    func testClearNotesAndRemoveOutputHaveIndependentMeaning() throws {
        let source = try output()
        let cleared = try report(source)
        XCTAssertTrue(cleared.text.hasSuffix(source.text)); XCTAssertTrue(cleared.text.contains("Intended output: Unknown"))
        let removed = try report(nil, notes: [.intendedOutput: "Phone speaker"])
        XCTAssertTrue(removed.text.contains("Intended output: \"Phone speaker\""))
        XCTAssertFalse(removed.text.contains("Included output details")); XCTAssertFalse(removed.text.contains(source.text))
    }

    func testLaterDraftOrSnapshotChangesCannotRewriteReviewedCopy() throws {
        var source = try output(); var notes: [TestSetupField: String] = [.constraints: "No calibration"]
        let frozen = try report(source, notes: notes); let text = frozen.text
        source = try output([.headphones]); notes.removeAll()
        XCTAssertEqual(frozen.text, text); XCTAssertTrue(frozen.text.contains("Output 1: Built-in speaker"))
        XCTAssertFalse(frozen.text.contains("Output 1: Headphones")); XCTAssertTrue(frozen.text.contains("Constraints: \"No calibration\""))
    }

    func testEmptyAndTruncatedPortSnapshotsDoNotResolvePlaybackUnknowns() throws {
        for source in [try output([]), try output(Array(repeating: .other, count: 16), total: 40)] {
            let text = try report(source).text
            XCTAssertTrue(text.hasSuffix(source.text)); XCTAssertTrue(text.contains("Negotiated format: Unknown"))
            XCTAssertTrue(text.contains("Independent capture: Not recorded")); XCTAssertTrue(text.contains("Audio session active: Unknown"))
        }
    }

    func testWorstCaseCombinedTextFitsDeclaredDualBounds() throws {
        let details = build.replacingOccurrences(of: "0.38.0", with: String(repeating: "😀", count: 48))
        let source = try output(Array(repeating: .bluetoothA2DP, count: 16), details: details, total: Int.max)
        for value in [String(repeating: "界", count: 160), String(repeating: "\\\"", count: 80), String(repeating: "😀", count: 80)] {
            let notes = Dictionary(uniqueKeysWithValues: TestSetupField.allCases.map { ($0, value) })
            let text = try report(source, notes: notes, details: details).text
            XCTAssertLessThanOrEqual(text.utf16.count, TestSetupReportSnapshot.maxCombinedCharacters)
            XCTAssertLessThanOrEqual(text.utf8.count, TestSetupReportSnapshot.maxCombinedUTF8Bytes)
        }
    }
}
