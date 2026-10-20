import XCTest
@testable import AQSSNativeFeedback

final class SoundCheckRecapsTests: XCTestCase {
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
