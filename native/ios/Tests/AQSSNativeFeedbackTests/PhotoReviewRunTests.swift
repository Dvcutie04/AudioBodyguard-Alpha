import XCTest
@testable import AQSSNativeFeedback

final class PhotoReviewRunTests: XCTestCase {
    func testClearBeforeImportRejectsTheLateImage() {
        let run = PhotoReviewRun(now: { 0 }), token = run.select()
        run.clear()
        XCTAssertFalse(run.beginReading(token)); XCTAssertFalse(run.complete(token))
    }
    func testReplacementRejectsOldImportWithoutClosingTheNewSelection() {
        let run = PhotoReviewRun(now: { 0 }), old = run.select(), current = run.select()
        XCTAssertFalse(run.beginReading(old)); XCTAssertFalse(run.cancel(old)); XCTAssertFalse(run.complete(old))
        XCTAssertTrue(run.isSelecting(current)); XCTAssertTrue(run.beginReading(current)); XCTAssertTrue(run.complete(current))
    }
    func testClearDuringRecognitionRejectsTheLateResult() {
        let run = PhotoReviewRun(now: { 0 }), token = run.select()
        XCTAssertTrue(run.beginReading(token)); run.clear()
        XCTAssertFalse(run.isReading(token)); XCTAssertFalse(run.complete(token))
    }
    func testOneImportAndOneTerminalResultPerSelection() {
        let run = PhotoReviewRun(now: { 0 }), token = run.select()
        XCTAssertFalse(run.complete(token)); XCTAssertTrue(run.isSelecting(token))
        XCTAssertTrue(run.beginReading(token)); XCTAssertFalse(run.beginReading(token))
        XCTAssertTrue(run.complete(token)); XCTAssertFalse(run.complete(token)); XCTAssertFalse(run.beginReading(token))
    }
    func testCancelledSelectionCannotReviveAndAnotherSelectionStillWorks() {
        let run = PhotoReviewRun(now: { 0 }), token = run.select()
        XCTAssertTrue(run.cancel(token)); XCTAssertFalse(run.cancel(token)); XCTAssertFalse(run.beginReading(token))
        let current = run.select(); XCTAssertTrue(run.beginReading(current)); XCTAssertTrue(run.complete(current))
    }
    func testForeignOwnerCannotReadCancelOrCompleteAnotherReview() {
        let first = PhotoReviewRun(now: { 0 }), second = PhotoReviewRun(now: { 0 })
        let foreign = first.select(), current = second.select()
        XCTAssertFalse(second.beginReading(foreign)); XCTAssertFalse(second.cancel(foreign)); XCTAssertFalse(second.complete(foreign))
        XCTAssertTrue(second.beginReading(current)); XCTAssertTrue(second.complete(current))
    }
    func testOldRecognitionCannotPublishOrCancelAReplacementInProgress() {
        let run = PhotoReviewRun(now: { 0 }), old = run.select(); XCTAssertTrue(run.beginReading(old))
        let current = run.select(); XCTAssertTrue(run.beginReading(current))
        XCTAssertFalse(run.complete(old)); XCTAssertFalse(run.cancel(old))
        XCTAssertTrue(run.isReading(current)); XCTAssertTrue(run.complete(current))
    }
    func testResultJustBeforeTheDeadlineCanComplete() {
        var now = 100.0; let run = PhotoReviewRun(now: { now }), token = run.select()
        XCTAssertTrue(run.beginReading(token)); now = 114.999
        XCTAssertTrue(run.complete(token)); XCTAssertFalse(run.complete(token))
    }
    func testReadingExpiresAtTheDeadlineAndCannotRevive() {
        var now = 100.0; let run = PhotoReviewRun(now: { now }), token = run.select()
        XCTAssertTrue(run.beginReading(token)); now = 115
        XCTAssertFalse(run.isReading(token)); now = 101
        XCTAssertFalse(run.isReading(token)); XCTAssertFalse(run.complete(token))
    }
    func testCompletionChecksTheDeadlineWithoutATimerTick() {
        var now = 100.0; let run = PhotoReviewRun(now: { now }), token = run.select()
        XCTAssertTrue(run.beginReading(token)); now = 115
        XCTAssertFalse(run.complete(token)); now = 100
        XCTAssertFalse(run.complete(token))
    }
    func testClockRollbackDuringReadingLatchesTheReviewOff() {
        var now = 100.0; let run = PhotoReviewRun(now: { now }), token = run.select()
        XCTAssertTrue(run.beginReading(token)); now = 101; XCTAssertTrue(run.isReading(token))
        now = 100; XCTAssertFalse(run.isReading(token)); now = 102
        XCTAssertFalse(run.isReading(token)); XCTAssertFalse(run.complete(token))
    }
    func testChoosingAPictureDoesNotConsumeItsReadingWindow() {
        var now = 100.0; let run = PhotoReviewRun(now: { now }), token = run.select()
        now = 1_000; XCTAssertTrue(run.isSelecting(token)); XCTAssertTrue(run.beginReading(token))
        now = 1_014.999; XCTAssertTrue(run.complete(token))
    }
    func testStaleCallbacksDoNotSampleTheClockOrExpireTheReplacement() {
        var now = 100.0, samples = 0
        let run = PhotoReviewRun(now: { samples += 1; return now }), old = run.select(); XCTAssertTrue(run.beginReading(old))
        let token = run.select(); now = 200; XCTAssertTrue(run.beginReading(token)); let before = samples
        now = 0; XCTAssertFalse(run.isReading(old)); XCTAssertFalse(run.complete(old)); XCTAssertFalse(run.cancel(old))
        XCTAssertEqual(before, samples); now = 201; XCTAssertTrue(run.complete(token))
    }
    func testInvalidReadingClocksCannotRevive() {
        for invalid in [-1.0, .nan, .infinity, -.infinity] {
            var now = invalid; let run = PhotoReviewRun(now: { now }), token = run.select()
            XCTAssertFalse(run.beginReading(token)); now = 0
            XCTAssertFalse(run.beginReading(token)); XCTAssertFalse(run.complete(token))
        }
        var now = 0.0; let run = PhotoReviewRun(now: { now }), token = run.select()
        XCTAssertTrue(run.beginReading(token)); now = .nan; XCTAssertFalse(run.complete(token))
        now = 1; XCTAssertFalse(run.complete(token))
    }
}
