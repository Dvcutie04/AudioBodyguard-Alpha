import Foundation
import XCTest
@testable import AQSSNativeFeedback

final class PhotoWorkSlotTests: XCTestCase {
    func testOneReadOwnsCapacityUntilItsActualReturn() throws {
        let slot = PhotoWorkSlot(); XCTAssertFalse(slot.occupied)
        let work = try XCTUnwrap(slot.acquire()); XCTAssertTrue(slot.occupied)
        for _ in 0..<100 { XCTAssertNil(slot.acquire()) }
        XCTAssertTrue(slot.release(work)); XCTAssertFalse(slot.occupied)
        XCTAssertNotNil(slot.acquire())
    }
    func testAForeignLeaseCannotFreeTheOccupiedSlot() throws {
        let slot = PhotoWorkSlot(); let work = try XCTUnwrap(slot.acquire())
        let foreign = try XCTUnwrap(PhotoWorkSlot().acquire())
        XCTAssertFalse(slot.release(foreign)); XCTAssertTrue(slot.occupied); XCTAssertNil(slot.acquire())
        XCTAssertTrue(slot.release(work))
    }
    func testDuplicateReturnCannotFreeTheNextRead() throws {
        let slot = PhotoWorkSlot(); let old = try XCTUnwrap(slot.acquire())
        XCTAssertTrue(slot.release(old)); XCTAssertFalse(slot.release(old))
        let current = try XCTUnwrap(slot.acquire()); XCTAssertNotEqual(old, current)
        XCTAssertFalse(slot.release(old)); XCTAssertNil(slot.acquire()); XCTAssertTrue(slot.release(current))
    }
    func testClearingAnExpiredReviewDoesNotSettleItsRead() throws {
        let slot = PhotoWorkSlot(); var now = 0.0
        let oldView = PhotoReviewRun(now: { now }); let token = oldView.select()
        let work = try XCTUnwrap(slot.acquire()); XCTAssertTrue(oldView.beginReading(token))
        now = 30; XCTAssertFalse(oldView.complete(token)); oldView.clear()
        let newView = PhotoReviewRun(now: { now }); let next = newView.select()
        XCTAssertTrue(newView.isSelecting(next)); XCTAssertTrue(slot.occupied); XCTAssertNil(slot.acquire())
        XCTAssertTrue(slot.release(work)); XCTAssertFalse(oldView.complete(token))
        let current = try XCTUnwrap(slot.acquire()); XCTAssertTrue(newView.beginReading(next))
        XCTAssertTrue(newView.complete(next)); XCTAssertTrue(slot.release(current))
    }
    func testPublishingAResultDoesNotSettleItsCleanup() throws {
        let slot = PhotoWorkSlot(); let run = PhotoReviewRun(now: { 0 }); let token = run.select()
        let work = try XCTUnwrap(slot.acquire()); XCTAssertTrue(run.beginReading(token)); XCTAssertTrue(run.complete(token))
        run.clear(); XCTAssertNil(slot.acquire()); XCTAssertTrue(slot.release(work)); XCTAssertNotNil(slot.acquire())
    }
    func testClosingASelectingViewDoesNotOwnOrReleaseAnotherRead() throws {
        let slot = PhotoWorkSlot(); let work = try XCTUnwrap(slot.acquire())
        let chooser = PhotoReviewRun(now: { 0 }); let token = chooser.select()
        XCTAssertTrue(chooser.cancel(token)); chooser.clear()
        XCTAssertNil(slot.acquire()); XCTAssertTrue(slot.release(work))
    }
    func testSimultaneousCallersAdmitExactlyOneRead() throws {
        let slot = PhotoWorkSlot(); let results = AdmittedPhotoWork()
        DispatchQueue.concurrentPerform(iterations: 16) { _ in
            if let work = slot.acquire() { results.append(work) }
        }
        let admitted = results.snapshot
        XCTAssertEqual(admitted.count, 1); XCTAssertTrue(slot.occupied)
        if admitted.count == 1 { XCTAssertTrue(slot.release(admitted[0])); XCTAssertFalse(slot.occupied) }
    }
}

private final class AdmittedPhotoWork: @unchecked Sendable {
    private let lock = NSLock()
    private var items: [PhotoWorkSlot.Lease] = []
    func append(_ item: PhotoWorkSlot.Lease) { lock.lock(); defer { lock.unlock() }; items.append(item) }
    var snapshot: [PhotoWorkSlot.Lease] { lock.lock(); defer { lock.unlock() }; return items }
}
