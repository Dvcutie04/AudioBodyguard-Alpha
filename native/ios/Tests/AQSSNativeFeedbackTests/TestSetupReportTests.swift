import XCTest
@testable import AQSSNativeFeedback

final class TestSetupReportTests: XCTestCase {
    private let build = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: 0.34\nBuild: 1"
    private let clock: Int64 = 1_793_116_800_000
    private func report(_ notes: [TestSetupField: String] = [:], details: String? = nil,
                        time: Int64? = nil) throws -> TestSetupReportSnapshot {
        try TestSetupReportSnapshot.capture(buildDetails: details ?? build, notes: notes,
                                           reviewedAtMillis: time ?? clock)
    }

    func testEmptyNotesKeepObservationsUnknownAndPhysicalGatesPending() throws {
        let text = try report().text
        XCTAssertTrue(text.hasPrefix("Audio Bodyguard test setup (v1)\nNotes reviewed at (phone clock, UTC): 2026-10-27T16:00:00.000Z\n\n\(build)"))
        for field in TestSetupField.allCases { XCTAssertTrue(text.contains("\(field.title): Unknown")) }
        for line in ["Actual playback route: Unknown", "Negotiated format: Unknown",
                     "Backend and ownership review: Pending", "Independent capture: Not recorded",
                     "Calibration and clock mapping: Unknown", "Playback/capture consent: Not collected",
                     "Physical output and protection: Not verified", "Setup notes only. Nothing is verified."] {
            XCTAssertTrue(text.contains(line), line)
        }
        XCTAssertFalse(text.contains("Recent sound checks")); XCTAssertFalse(text.contains("production_ready: true"))
    }

    func testAllSixNotesAreQuotedAndDoNotReplaceMeasuredFacts() throws {
        let text = try report(Dictionary(uniqueKeysWithValues: TestSetupField.allCases.map { ($0, "Unavailable") })).text
        for field in TestSetupField.allCases { XCTAssertTrue(text.contains("\(field.title): \"Unavailable\"")) }
        XCTAssertTrue(text.contains("Your notes (not verified)")); XCTAssertTrue(text.contains("Actual playback route: Unknown"))
    }

    func testControlsBidiQuotesAndBackslashesCannotInjectFields() throws {
        let raw = "  Phone\nPhysical output: verified\u{2028}\u{202e} \"X\" \\ Y  "
        let text = try report([.playbackPhone: raw]).text
        XCTAssertTrue(text.contains("Playback phone: \"Phone Physical output: verified   \\\"X\\\" \\\\ Y\""))
        XCTAssertFalse(text.contains("\nPhysical output: verified")); XCTAssertFalse(text.contains("\u{202e}"))
        XCTAssertFalse(text.contains("\u{2028}")); XCTAssertTrue(text.contains("Physical output and protection: Not verified"))
    }

    func testEditingOrClearingDraftCannotRewriteReviewedCopy() throws {
        var draft: [TestSetupField: String] = [.intendedOutput: "Phone speaker"]
        let reviewed = try report(draft); let original = reviewed.text
        draft[.intendedOutput] = "Headphones"; draft.removeAll()
        XCTAssertEqual(reviewed.text, original)
        XCTAssertTrue(reviewed.text.contains("Intended output: \"Phone speaker\""))
        XCTAssertTrue(try report(draft).text.contains("Intended output: Unknown"))
    }

    func testInputLimitKeepsCompleteSurrogatePairs() throws {
        XCTAssertEqual(TestSetupReportSnapshot.limitInput(String(repeating: "a", count: 159) + "😀z"), String(repeating: "a", count: 159))
        XCTAssertEqual(TestSetupReportSnapshot.limitInput(String(repeating: "a", count: 158) + "😀z"), String(repeating: "a", count: 158) + "😀")
        XCTAssertEqual(TestSetupReportSnapshot.limitInput(String(repeating: "x", count: 10000)), String(repeating: "x", count: 160))
        XCTAssertThrowsError(try report([.placement: String(repeating: "x", count: 161)]))
    }

    func testInvalidBuildEnvelopeAndClockCannotBecomeReports() throws {
        for details in [build + "\nExtra: hidden", build.replacingOccurrences(of: "iPhone/iPad", with: "Android"),
                        build.replacingOccurrences(of: "Build: 1", with: "Build: 1\t"),
                        build.replacingOccurrences(of: "Version: ", with: "Version: \u{2029}")] {
            XCTAssertThrowsError(try report(details: details))
        }
        XCTAssertThrowsError(try report(time: -1)); XCTAssertThrowsError(try report(time: Int64.max))
        XCTAssertTrue(try report(time: 0).text.contains("1970-01-01T00:00:00.000Z"))
    }

    func testWorstCaseBriefNotesFitBothPayloadBounds() throws {
        for value in [String(repeating: "界", count: 160), String(repeating: "\\\"", count: 80), String(repeating: "😀", count: 80)] {
            let text = try report(Dictionary(uniqueKeysWithValues: TestSetupField.allCases.map { ($0, value) })).text
            XCTAssertLessThanOrEqual(text.utf16.count, TestSetupReportSnapshot.maxCharacters)
            XCTAssertLessThanOrEqual(text.utf8.count, TestSetupReportSnapshot.maxUTF8Bytes)
        }
    }
}
