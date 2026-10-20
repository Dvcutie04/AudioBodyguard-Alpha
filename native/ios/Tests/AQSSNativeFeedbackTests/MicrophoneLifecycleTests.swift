import XCTest
@testable import AQSSNativeFeedback

final class MicrophoneLifecycleTests: XCTestCase {
    private enum Failure: Error { case expected }

    func testVoiceAndMeterCannotOwnTheSessionTogether() async {
        await MainActor.run {
            let gate = ForegroundMicrophoneGate()
            XCTAssertNotNil(gate.acquire())
            XCTAssertNil(gate.acquire())
            XCTAssertFalse(gate.available)
        }
    }

    func testClosingAnIdleToolCannotDeactivateAnActiveOwner() async throws {
        try await MainActor.run {
            let gate = ForegroundMicrophoneGate()
            let meter = try XCTUnwrap(gate.acquire())
            var activations = 0, deactivations = 0
            try gate.activate(meter) { activations += 1 }
            XCTAssertFalse(gate.release(nil) { deactivations += 1 })
            XCTAssertEqual(activations, 1)
            XCTAssertEqual(deactivations, 0)
            XCTAssertNil(gate.acquire())
            XCTAssertTrue(gate.release(meter) { deactivations += 1 })
            XCTAssertEqual(deactivations, 1)
            XCTAssertTrue(gate.available)
        }
    }

    func testStaleLeaseCannotActivateOrStopAnotherRun() async throws {
        try await MainActor.run {
            let gate = ForegroundMicrophoneGate()
            let old = try XCTUnwrap(gate.acquire())
            XCTAssertTrue(gate.release(old) { XCTFail("Never activated") })
            let current = try XCTUnwrap(gate.acquire())
            XCTAssertNotEqual(old, current)
            XCTAssertThrowsError(try gate.activate(old) { XCTFail("Wrong owner") })
            try gate.activate(current) {}
            XCTAssertFalse(gate.release(old) { XCTFail("Must not stop current input") })
            XCTAssertNil(gate.acquire())
            XCTAssertTrue(gate.release(current) {})
        }
    }

    func testRepeatedActivationAndCleanupCannotTouchSessionTwice() async throws {
        try await MainActor.run {
            let gate = ForegroundMicrophoneGate()
            let owner = try XCTUnwrap(gate.acquire())
            try gate.activate(owner) {}
            XCTAssertThrowsError(try gate.activate(owner) { XCTFail("Already active") })
            XCTAssertTrue(gate.release(owner) {})
            XCTAssertFalse(gate.release(owner) { XCTFail("Already released") })
        }
    }

    func testFailedActivationReleasesReservationWithoutDeactivating() async throws {
        try await MainActor.run {
            let gate = ForegroundMicrophoneGate()
            let owner = try XCTUnwrap(gate.acquire())
            XCTAssertThrowsError(try gate.activate(owner) { throw Failure.expected })
            XCTAssertTrue(gate.release(owner) { XCTFail("Activation never succeeded") })
            XCTAssertNotNil(gate.acquire())
        }
    }

    func testCleanupFailureBlocksBothToolsAndCannotBeRetriedAway() async throws {
        try await MainActor.run {
            let gate = ForegroundMicrophoneGate()
            let owner = try XCTUnwrap(gate.acquire())
            try gate.activate(owner) {}
            XCTAssertFalse(gate.release(owner) { throw Failure.expected })
            XCTAssertTrue(gate.blocked)
            XCTAssertFalse(gate.available)
            XCTAssertNil(gate.acquire())
            XCTAssertFalse(gate.release(owner) { XCTFail("Failure must stay latched") })
            XCTAssertThrowsError(try gate.activate(owner) { XCTFail("Blocked") })
            XCTAssertNil(gate.acquire())
        }
    }

    func testSpeechDeliveryKeepsOnlyLatestBoundedWords() {
        let mailbox = VoiceResultMailbox()
        mailbox.publish(text: "old words", final: false, failed: false)
        mailbox.publish(text: String(repeating: "x", count: 2_000), final: false, failed: false)
        let update = mailbox.take()
        XCTAssertEqual(update?.text, String(repeating: "x", count: 500))
        XCTAssertFalse(update?.final ?? true)
        XCTAssertNil(mailbox.take())
    }

    func testFinalOrErrorCannotBeOverwrittenByLatePartialWords() {
        for failed in [false, true] {
            let mailbox = VoiceResultMailbox()
            mailbox.publish(text: "last words", final: false, failed: false)
            mailbox.publish(text: nil, final: !failed, failed: failed)
            mailbox.publish(text: "late partial", final: false, failed: false)
            let update = mailbox.take()
            XCTAssertEqual(update?.text, "last words")
            XCTAssertEqual(update?.final, !failed)
            XCTAssertEqual(update?.failed, failed)
            mailbox.publish(text: "still late", final: false, failed: false)
            XCTAssertNil(mailbox.take())
        }
    }

    func testStopDropsPendingWordsAndRejectsLateRecognitionCallbacks() {
        let mailbox = VoiceResultMailbox()
        mailbox.publish(text: "pending", final: false, failed: false)
        mailbox.close()
        mailbox.publish(text: "late", final: true, failed: false)
        XCTAssertNil(mailbox.take())
        let next = VoiceResultMailbox()
        next.publish(text: "new run", final: false, failed: false)
        XCTAssertEqual(next.take()?.text, "new run")
        XCTAssertNil(mailbox.take())
    }
}
