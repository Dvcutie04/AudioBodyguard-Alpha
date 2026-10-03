import XCTest
@testable import AQSSNativeFeedback

final class SetupProgressTests: XCTestCase {
    func testBookmarksRoundTripAndFinishClearsOnlyThatRoute() {
        var saved = AQSSSetupProgress()
        XCTAssertTrue(saved.record("roku_network", 3))
        XCTAssertTrue(saved.record("roku_model", 1))
        let restored = AQSSSetupProgress(serialized: saved.serialized())
        XCTAssertEqual(restored.resumeIndex("roku_network"), 3)
        XCTAssertEqual(restored.resumeIndex("roku_model"), 1)
        XCTAssertTrue(saved.record("roku_network", nil))
        XCTAssertNil(AQSSSetupProgress(serialized: saved.serialized()).resumeIndex("roku_network"))
        XCTAssertEqual(saved.resumeIndex("roku_model"), 1)
    }
    func testUnchangedBookmarksDoNotRequestAnotherWrite() {
        var saved = AQSSSetupProgress(serialized: "{\"roku_network\":3}")
        let original = saved.serialized()
        XCTAssertFalse(saved.record("roku_network", 3))
        XCTAssertFalse(saved.record("roku_model", nil))
        XCTAssertEqual(saved.serialized(), original)
        XCTAssertTrue(saved.record("roku_network", 4))
    }
    func testInvalidOrVoiceBookmarksCannotResume() {
        var saved = AQSSSetupProgress(serialized: "{\"roku_network\":99,\"roku_model\":-1,\"voice\":3,\"invented\":0}")
        for id in ["roku_network", "roku_model", "voice", "invented"] { XCTAssertNil(saved.resumeIndex(id)) }
        XCTAssertFalse(saved.record("roku_network", -1))
        XCTAssertFalse(saved.record("roku_network", 5))
        XCTAssertFalse(saved.record("voice", 0))
        XCTAssertFalse(saved.record("invented", 0))
    }
    func testMalformedOrOversizedStorageStartsFresh() {
        for raw in ["", "not JSON", "{\"roku_network\":\"3\"}", "{\"roku_network\":9223372036854775808}", String(repeating: " ", count: 16_385)] {
            let saved = AQSSSetupProgress(serialized: raw)
            XCTAssertNil(saved.resumeIndex("roku_network"))
            XCTAssertEqual(saved.serialized(), "{}")
        }
    }
}
