import XCTest
import UIKit

final class OutputDetailsUITests: XCTestCase {
    private func shot(_ name: String, _ app: XCUIApplication) {
        let image = XCTAttachment(screenshot: app.screenshot()); image.name = name; image.lifetime = .keepAlways; add(image)
    }
    private func open(_ app: XCUIApplication) throws {
        if app.buttons["page-picker"].exists {
            app.buttons["page-picker"].tap()
            let menu = app.scrollViews["menu-scroll"]
            let sound = app.buttons["Sound"].firstMatch
            for _ in 0..<6 { if sound.isHittable { break }; menu.swipeUp() }
            XCTAssertTrue(sound.isHittable); sound.tap()
            let closed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: menu)
            XCTAssertEqual(XCTWaiter.wait(for: [closed], timeout: 5), .completed)
        } else { app.buttons["tab-sound"].tap() }
        let entry = app.buttons["output-details-open"]
        guard entry.waitForExistence(timeout: 5) else {
            shot("Output details entry missing", app); XCTFail("Sound has no Output details entry")
            throw NSError(domain: "AQSSOutputDetails", code: 1)
        }
        entry.tap(); XCTAssertTrue(app.buttons["output-details-refresh"].waitForExistence(timeout: 5))
    }
    private func launch() -> XCUIApplication {
        let app = XCUIApplication(); app.launchArguments = ["-aqssGuideDismissedV1", "YES"]; app.launch(); return app
    }
    private func review(_ app: XCUIApplication) -> String {
        XCTAssertFalse(app.buttons["output-details-review"].isEnabled)
        XCTAssertEqual(app.alerts.count, 0)
        app.buttons["output-details-refresh"].tap()
        XCTAssertTrue(app.buttons["output-details-review"].isEnabled)
        app.buttons["output-details-review"].tap()
        let preview = app.staticTexts["output-details-preview"]
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        let text = preview.label
        let env = ProcessInfo.processInfo.environment
        let metadata = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: " + (env["AQSS_TEST_APP_VERSION"] ?? "MISSING") + "\nBuild: " + (env["AQSS_TEST_APP_BUILD"] ?? "MISSING")
        XCTAssertTrue(text.hasPrefix("Audio Bodyguard iPhone output details (v1)\n")); XCTAssertTrue(text.contains(metadata))
        XCTAssertTrue(text.contains("Audio session active: Unknown")); XCTAssertTrue(text.contains("Actual playback route: Unknown"))
        XCTAssertTrue(text.contains("Physical output and protection: Not verified"))
        XCTAssertTrue(app.staticTexts["output-details-notice"].isHittable)
        XCTAssertFalse(app.buttons["sound-check-start-stop"].exists); XCTAssertEqual(app.alerts.count, 0)
        return text
    }
    private func share(_ copy: Bool) throws {
        let app = launch(); try open(app); let text = review(app)
        let attachment = XCTAttachment(string: text); attachment.name = "Output details reviewed text"; attachment.lifetime = .keepAlways; add(attachment)
        shot("Output details immutable review", app)
        let button = app.buttons["output-details-share"]; XCTAssertTrue(button.isHittable); button.tap()
        let nativeCopy = app.cells["Copy"].firstMatch; XCTAssertTrue(nativeCopy.waitForExistence(timeout: 8))
        shot("Output details native share", app)
        if copy { nativeCopy.tap() }
        else if UIDevice.current.userInterfaceIdiom == .pad {
            let heading = app.staticTexts["output-details-heading"]
            let point = heading.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            let popover = app.popovers.firstMatch
            guard heading.exists, popover.exists, app.frame.contains(point.screenPoint), !popover.frame.contains(point.screenPoint) else {
                XCTFail("No observed heading point outside the share popover"); throw NSError(domain: "AQSSOutputDetails", code: 2)
            }
            point.tap()
        } else {
            let close = app.navigationBars["UIActivityContentView"].buttons["Close"].firstMatch
            XCTAssertTrue(close.waitForExistence(timeout: 5)); close.tap()
        }
        let returned = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true AND hittable == true"), object: button)
        XCTAssertEqual(XCTWaiter.wait(for: [returned], timeout: 8), .completed)
        XCTAssertEqual(app.staticTexts["output-details-preview"].label, text); XCTAssertFalse(nativeCopy.exists)
        shot("Output details share returned unchanged", app)
    }
    func testOutputDetailsCancelPreservesReviewedSnapshot() throws { try share(false) }
    func testOutputDetailsCopyMatchesActualReviewedSnapshot() throws { try share(true) }

    func testOutputDetailsLifecycleAndLargestText() throws {
        let app = launch(); try open(app); let text = review(app)
        XCUIDevice.shared.orientation = .landscapeLeft
        XCTAssertEqual(app.staticTexts["output-details-preview"].label, text)
        XCUIDevice.shared.orientation = .portrait
        XCTAssertEqual(app.staticTexts["output-details-preview"].label, text)
        shot("Output details rotation retains immutable snapshot", app)
        XCUIDevice.shared.press(.home); app.activate()
        XCTAssertTrue(app.buttons["output-details-refresh"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["output-details-review"].isEnabled)
        XCTAssertFalse(app.staticTexts["output-details-preview"].exists)
        app.buttons["output-details-back"].tap()
        XCTAssertTrue(app.buttons["output-details-open"].waitForExistence(timeout: 5))
        app.buttons["output-details-open"].tap(); XCTAssertFalse(app.buttons["output-details-review"].isEnabled)
        app.terminate(); app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch(); try open(app); _ = review(app)
        XCTAssertTrue(app.buttons["output-details-share"].isHittable)
        XCTAssertTrue(app.buttons["output-details-back"].isHittable)
        XCTAssertTrue(app.staticTexts["output-details-notice"].isHittable)
        shot("Output details largest text keeps notice and controls reachable", app)
        XCTAssertEqual(app.alerts.count, 0)
    }
}
