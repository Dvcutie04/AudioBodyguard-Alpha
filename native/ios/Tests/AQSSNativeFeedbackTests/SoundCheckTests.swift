import XCTest
@testable import AQSSNativeFeedback

final class SoundCheckTests: XCTestCase {
    private func level(_ values: [Float]) throws -> SoundInputLevel {
        try values.withUnsafeBufferPointer { try SoundInputLevel.measure($0) }
    }

    func testZeroIsUnknownAcousticallyAndHalfScaleIsDigitalOnly() throws {
        let zero = try level([0, 0])
        XCTAssertNil(zero.rmsDbfs)
        XCTAssertEqual(zero.peakFraction, 0)
        XCTAssertEqual(zero.fullScaleSamples, 0)
        let half = try level([0.5, -0.5])
        XCTAssertEqual(half.rmsDbfs!, -6.020599913, accuracy: 0.000001)
        XCTAssertEqual(half.peakFraction, 0.5)
        XCTAssertEqual(half.sampleCount, 2)
    }

    func testNonfiniteAndUnboundedBuffersAreRejected() throws {
        for bad in [[Float](), [.nan], [.infinity], [-.infinity], Array(repeating: 0, count: 65_537)] {
            XCTAssertThrowsError(try level(bad))
        }
        let full = try level([-1, 1, 2])
        XCTAssertEqual(full.fullScaleSamples, 3)
        XCTAssertEqual(full.peakFraction, 2)
        XCTAssertTrue(full.rmsDbfs! > 0) // Float PCM can exceed digital full scale; never hide it.
        let prefix: [Float] = [0.5, -0.5, .nan]
        let measured = try prefix.withUnsafeBufferPointer {
            try SoundInputLevel.measure(UnsafeBufferPointer(start: $0.baseAddress, count: 2))
        }
        XCTAssertEqual(measured.sampleCount, 2)
    }

    func testStopRestartAndLateCallbacksNeverRestoreOldInput() throws {
        var window = SoundInputWindow()
        let first = window.start(at: 1)!
        let value = try level([0.5])
        XCTAssertTrue(window.offer(run: first, receivedAt: 1.1, now: 1.1, value: value))
        window.stop()
        XCTAssertNil(window.current(at: 1.2))
        XCTAssertFalse(window.offer(run: first, receivedAt: 1.2, now: 1.2, value: value))
        let second = window.start(at: 2)!
        XCTAssertFalse(window.offer(run: first, receivedAt: 2.1, now: 2.1, value: value))
        XCTAssertTrue(window.offer(run: second, receivedAt: 2.1, now: 2.1, value: value))
    }

    func testStalenessClearsAtBoundaryAndThirtySecondsEndsTheRun() throws {
        var window = SoundInputWindow()
        let run = window.start(at: 1)!
        let value = try level([0.5])
        XCTAssertTrue(window.offer(run: run, receivedAt: 2, now: 2, value: value))
        XCTAssertNotNil(window.current(at: 2.749))
        XCTAssertNil(window.current(at: 2.75))
        XCTAssertTrue(window.offer(run: run, receivedAt: 30.9, now: 30.9, value: value))
        XCTAssertNil(window.current(at: 31))
        XCTAssertFalse(window.active)
        XCTAssertFalse(window.offer(run: run, receivedAt: 31.1, now: 31.1, value: value))
    }

    func testRollbackNonfiniteFutureAndDuplicateTimesFailClosed() throws {
        var window = SoundInputWindow()
        XCTAssertNil(window.start(at: .nan))
        let run = window.start(at: 1)!
        let value = try level([0.5])
        XCTAssertFalse(window.offer(run: run, receivedAt: 0.9, now: 1.1, value: value))
        XCTAssertFalse(window.offer(run: run, receivedAt: 1.3, now: 1.2, value: value))
        XCTAssertTrue(window.offer(run: run, receivedAt: 1.3, now: 1.3, value: value))
        XCTAssertFalse(window.offer(run: run, receivedAt: 1.3, now: 1.4, value: value))
        XCTAssertNil(window.current(at: 1.39))
        XCTAssertFalse(window.active)
        XCTAssertFalse(window.offer(run: run, receivedAt: 2, now: 2, value: value))
        _ = window.start(at: 3)
        XCTAssertNil(window.current(at: .infinity))
        XCTAssertFalse(window.active)
    }

    func testMailboxKeepsOneSummaryAndClosureRejectsLatePublication() throws {
        let mailbox = SoundInputMailbox()
        let first = try level([0.25]), second = try level([0.5])
        mailbox.publish(first, at: 1)
        mailbox.publish(second, at: 2)
        XCTAssertEqual(mailbox.take()?.level, second)
        XCTAssertNil(mailbox.take())
        mailbox.publish(first, at: 3)
        mailbox.close()
        mailbox.publish(second, at: 4)
        XCTAssertNil(mailbox.take())
    }
}
