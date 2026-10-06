import XCTest
@testable import AQSSNativeFeedback

final class SettingSwitchStateTests: XCTestCase {
    func testDisconnectedAttemptLastsTwoSecondsAndDoesNotEnableSetting() {
        var state = AQSSSettingSwitchState()
        state.press("captions", connectionVerified: false, now: 10)
        XCTAssertTrue(state.isOn("captions")); XCTAssertTrue(state.isAttempting("captions"))
        XCTAssertTrue(state.enabled.isEmpty)
        state.expire(now: 11.999); XCTAssertTrue(state.isOn("captions"))
        state.expire(now: 12); XCTAssertFalse(state.isOn("captions")); XCTAssertNil(state.nextExpiry)
    }
    func testRepeatedTapsCannotExtendAttemptAndOldExpiryCannotEraseNewAttempt() {
        var state = AQSSSettingSwitchState()
        state.press("voice", connectionVerified: false, now: 10)
        state.press("voice", connectionVerified: false, now: 11.5)
        state.expire(now: 12); XCTAssertFalse(state.isOn("voice"))
        state.press("voice", connectionVerified: false, now: 12.1)
        state.expire(now: 12.5); XCTAssertTrue(state.isAttempting("voice"))
        state.expire(now: 14.1); XCTAssertFalse(state.isOn("voice"))
    }
    func testIndependentAttemptsAndVerifiedConnectionRemainDistinct() {
        var state = AQSSSettingSwitchState()
        state.press("captions", connectionVerified: false, now: 10)
        state.press("background", connectionVerified: false, now: 11)
        state.expire(now: 12)
        XCTAssertFalse(state.isOn("captions")); XCTAssertTrue(state.isOn("background"))
        state.press("captions", connectionVerified: true, now: 12)
        state.expire(now: 100)
        XCTAssertTrue(state.isOn("captions")); XCTAssertFalse(state.isAttempting("captions"))
        XCTAssertFalse(state.isOn("background"))
        state.press("captions", connectionVerified: true, now: 101); XCTAssertFalse(state.isOn("captions"))
    }
    func testLostConnectionAndLifecycleResetTurnOffEverySetting() {
        var state = AQSSSettingSwitchState()
        for id in ["captions", "profiles", "voice"] { state.press(id, connectionVerified: true, now: 10) }
        state.press("background", connectionVerified: false, now: 11)
        XCTAssertTrue(state.enabled.isEmpty)
        state.connectionLost(); XCTAssertNil(state.nextExpiry)
        for item in AQSSInterfaceContent.settings { XCTAssertFalse(state.isOn(item.id)) }
        state.press("captions", connectionVerified: true, now: 20); state.reset()
        XCTAssertFalse(state.isOn("captions"))
    }
    func testPresetChoicesAreExclusiveAndInvalidInputsNeverEnableAnything() {
        var state = AQSSSettingSwitchState()
        state.press("dialogue", connectionVerified: true, now: 1)
        state.press("night", connectionVerified: true, now: 2)
        XCTAssertFalse(state.isOn("dialogue")); XCTAssertTrue(state.isOn("night"))
        state.press("dialogue", connectionVerified: true, now: 3)
        XCTAssertTrue(state.isOn("dialogue")); XCTAssertFalse(state.isOn("night"))
        state.reset()
        for now in [Double.nan, Double.infinity, -1] { state.press("captions", connectionVerified: true, now: now) }
        state.press("invented", connectionVerified: true, now: 1)
        XCTAssertTrue(state.enabled.isEmpty); XCTAssertNil(state.nextExpiry)
    }
}
