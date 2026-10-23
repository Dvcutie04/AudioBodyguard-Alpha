import XCTest
@testable import AQSSNativeFeedback

final class SoundCheckRecapsTests: XCTestCase {
    func testExcludedRecapsShareOnlyExactInstalledMetadata() {
        let metadata = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: test-version\nBuild: 1"
        let report = PrivateSupportReportSnapshot(buildDetails: metadata, recaps: [
            SoundCheckRecap(inputObserved: true, end: .stoppedByUser),
            SoundCheckRecap(inputObserved: false, end: .permissionChanged),
        ])
        XCTAssertEqual(report.text(includeRecentChecks: false), metadata)
    }

    func testSupportReportKeepsNewestFirstAndDoesNotCallMissingInputSilence() {
        let text = soundCheckSupportReportSection([
            SoundCheckRecap(inputObserved: true, end: .stoppedByUser),
            SoundCheckRecap(inputObserved: false, end: .noSamples),
        ])
        XCTAssertEqual(text, "Recent sound checks (this app session)\nCheck 1: Input samples observed\nStopped by you\n\nCheck 2: No input samples observed\nNo current input samples\n\nInput observations only; not proof of sound safety, protection or TV control.")
    }

    func testSupportReportDefensivelyExcludesASixthCompletedRow() {
        let ends: [SoundCheckEnd] = [.stoppedByUser, .timeLimit, .permissionChanged, .inputBlocked, .cleanupFailed, .closed]
        let text = soundCheckSupportReportSection(ends.map { SoundCheckRecap(inputObserved: false, end: $0) })
        XCTAssertEqual(text.components(separatedBy: "\n").filter { $0.hasPrefix("Check ") }.count, 5)
        XCTAssertFalse(text.contains("Check 6"))
        XCTAssertFalse(text.contains("Sound check closed"))
        XCTAssertTrue(text.contains("Input cleanup failed; restart the app before retrying"))
    }

    func testNewReportAfterClearIsEmptyWhileReviewedSnapshotStaysFixed() async throws {
        try await MainActor.run {
            let store = SoundCheckRecaps()
            let run = try XCTUnwrap(store.begin()); store.observe(run); store.finish(run, end: .stoppedByUser)
            let snapshot = store.snapshot()
            let reviewed = soundCheckSupportReportSection(snapshot)
            store.clear()
            XCTAssertTrue(reviewed.contains("Check 1: Input samples observed\nStopped by you"))
            XCTAssertEqual(reviewed, soundCheckSupportReportSection(snapshot))
            XCTAssertTrue(soundCheckSupportReportSection(store.snapshot()).contains("No completed sound checks in this app session."))
        }
    }

    func testSupportReportDoesNotInventCompletedChecksFromAnActiveDraft() async throws {
        try await MainActor.run {
            let store = SoundCheckRecaps()
            store.observe(try XCTUnwrap(store.begin()))
            XCTAssertEqual(soundCheckSupportReportSection(store.snapshot()),
                "Recent sound checks (this app session)\nNo completed sound checks in this app session.\n\nInput observations only; not proof of sound safety, protection or TV control.")
        }
    }

    func testOnlyFinishedChecksAppearAndMissingInputIsNotSilence() async throws {
        try await MainActor.run {
            let store = SoundCheckRecaps()
            let run = try XCTUnwrap(store.begin())
            XCTAssertTrue(store.snapshot().isEmpty)
            XCTAssertTrue(store.finish(run, end: .noSamples))
            XCTAssertEqual(store.snapshot(), [SoundCheckRecap(inputObserved: false, end: .noSamples)])
            XCTAssertFalse(store.finish(run, end: .stoppedByUser))
        }
    }

    func testOldCallbacksCannotChangeANewerCheck() async throws {
        try await MainActor.run {
            let store = SoundCheckRecaps()
            let old = try XCTUnwrap(store.begin())
            XCTAssertNil(store.begin())
            XCTAssertTrue(store.observe(old))
            XCTAssertTrue(store.finish(old, end: .leftScreen))
            let current = try XCTUnwrap(store.begin())
            XCTAssertFalse(store.observe(old))
            XCTAssertFalse(store.finish(old, end: .timeLimit))
            XCTAssertTrue(store.finish(current, end: .couldNotStart))
            XCTAssertFalse(store.snapshot()[0].inputObserved)
            XCTAssertTrue(store.snapshot()[1].inputObserved)
        }
    }

    func testOnlyFiveNewestSummariesSurviveWithIndependentSnapshots() async throws {
        try await MainActor.run {
            let store = SoundCheckRecaps()
            let ends = Array(SoundCheckEnd.allCases.prefix(6))
            for end in ends { store.finish(try XCTUnwrap(store.begin()), end: end) }
            let before = store.snapshot()
            XCTAssertEqual(before.map { $0.end }, Array(ends.dropFirst().reversed()))
            store.clear()
            XCTAssertEqual(before.count, 5)
            XCTAssertTrue(store.snapshot().isEmpty)
            XCTAssertTrue(SoundCheckRecaps().snapshot().isEmpty)
        }
    }

    func testClearRejectsLatePublicationOfDiscardedCheck() async throws {
        try await MainActor.run {
            let store = SoundCheckRecaps()
            let old = try XCTUnwrap(store.begin())
            store.observe(old); store.clear()
            let current = try XCTUnwrap(store.begin())
            XCTAssertFalse(store.observe(old))
            XCTAssertFalse(store.finish(old, end: .cleanupFailed))
            XCTAssertTrue(store.finish(current, end: .timeLimit))
            XCTAssertEqual(store.snapshot(), [SoundCheckRecap(inputObserved: false, end: .timeLimit)])
        }
    }

    func testClearingRecapsCannotUnlockMicrophoneCleanupFailure() async throws {
        enum Failure: Error { case expected }
        try await MainActor.run {
            let gate = ForegroundMicrophoneGate()
            let owner = try XCTUnwrap(gate.acquire())
            try gate.activate(owner) {}
            gate.release(owner) { throw Failure.expected }
            SoundCheckRecaps.shared.clear()
            XCTAssertTrue(gate.blocked)
            XCTAssertNil(gate.acquire())
        }
    }
}
