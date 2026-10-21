import XCTest
@testable import AQSSNativeFeedback

final class PhotoReviewRunTests: XCTestCase {
    func testClearBeforeImportRejectsTheLateImage() {
        let run = PhotoReviewRun(), token = run.select()
        run.clear()
        XCTAssertFalse(run.beginReading(token)); XCTAssertFalse(run.complete(token))
    }
    func testReplacementRejectsOldImportWithoutClosingTheNewSelection() {
        let run = PhotoReviewRun(), old = run.select(), current = run.select()
        XCTAssertFalse(run.beginReading(old)); XCTAssertFalse(run.cancel(old)); XCTAssertFalse(run.complete(old))
        XCTAssertTrue(run.isSelecting(current)); XCTAssertTrue(run.beginReading(current)); XCTAssertTrue(run.complete(current))
    }
    func testClearDuringRecognitionRejectsTheLateResult() {
        let run = PhotoReviewRun(), token = run.select()
        XCTAssertTrue(run.beginReading(token)); run.clear()
        XCTAssertFalse(run.isReading(token)); XCTAssertFalse(run.complete(token))
    }
    func testOneImportAndOneTerminalResultPerSelection() {
        let run = PhotoReviewRun(), token = run.select()
        XCTAssertFalse(run.complete(token)); XCTAssertTrue(run.isSelecting(token))
        XCTAssertTrue(run.beginReading(token)); XCTAssertFalse(run.beginReading(token))
        XCTAssertTrue(run.complete(token)); XCTAssertFalse(run.complete(token)); XCTAssertFalse(run.beginReading(token))
    }
    func testCancelledSelectionCannotReviveAndAnotherSelectionStillWorks() {
        let run = PhotoReviewRun(), token = run.select()
        XCTAssertTrue(run.cancel(token)); XCTAssertFalse(run.cancel(token)); XCTAssertFalse(run.beginReading(token))
        let current = run.select(); XCTAssertTrue(run.beginReading(current)); XCTAssertTrue(run.complete(current))
    }
    func testForeignOwnerCannotReadCancelOrCompleteAnotherReview() {
        let first = PhotoReviewRun(), second = PhotoReviewRun()
        let foreign = first.select(), current = second.select()
        XCTAssertFalse(second.beginReading(foreign)); XCTAssertFalse(second.cancel(foreign)); XCTAssertFalse(second.complete(foreign))
        XCTAssertTrue(second.beginReading(current)); XCTAssertTrue(second.complete(current))
    }
    func testOldRecognitionCannotPublishOrCancelAReplacementInProgress() {
        let run = PhotoReviewRun(), old = run.select(); XCTAssertTrue(run.beginReading(old))
        let current = run.select(); XCTAssertTrue(run.beginReading(current))
        XCTAssertFalse(run.complete(old)); XCTAssertFalse(run.cancel(old))
        XCTAssertTrue(run.isReading(current)); XCTAssertTrue(run.complete(current))
    }
}
