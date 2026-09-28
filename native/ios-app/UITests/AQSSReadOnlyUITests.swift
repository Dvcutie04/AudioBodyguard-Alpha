import XCTest

final class AQSSReadOnlyUITests: XCTestCase {
    private func label(_ text: String, _ app: XCUIApplication) {
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", text)).firstMatch.waitForExistence(timeout: 10), "Missing: \(text)")
    }
    private func tap(_ title: String, _ app: XCUIApplication) {
        let button = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", title)).firstMatch
        XCTAssertTrue(button.waitForExistence(timeout: 10), "Missing button: \(title)")
        for _ in 0..<10 where !button.isHittable { app.scrollViews["home-scroll"].swipeUp() }
        XCTAssertTrue(button.isHittable, "Unreachable button: \(title)")
        button.tap()
    }
    private func tab(_ id: String, _ app: XCUIApplication) { app.buttons["tab-\(id)"].tap() }
    private func jump(_ title: String, _ app: XCUIApplication) { app.buttons["Jump to"].tap(); app.buttons[title].tap() }
    private func screenshot(_ name: String, _ app: XCUIApplication) {
        let shot = XCTAttachment(screenshot: app.screenshot()); shot.name = name; shot.lifetime = .keepAlways; add(shot)
    }

    func testAllFivePagesKeepHelpAndTruthfulEmptyStates() {
        let app = XCUIApplication(); app.launch()
        label("Unknown physical state", app); label("No output observation", app)
        screenshot("01 Midnight Home", app)
        for (id, title) in [("sound", "Sound, on your terms."), ("devices", "A clear path to sound."), ("insights", "Know what happened."), ("settings", "Make space for you.")] {
            tab(id, app); label(title, app)
            XCTAssertTrue(app.buttons["Help & tutorials"].isHittable)
            screenshot("Page \(id)", app)
        }
        jump("Readiness checklist", app); label("Six setup checks unknown", app)
        jump("Session transfer", app); label("No supported endpoint or verified transfer path", app)
        tab("home", app); label("Unknown physical state", app)
    }

    func testOptionsAndAdvancedRemainUnavailable() {
        let app = XCUIApplication(); app.launch(); tab("sound", app)
        label("No qualified device volume control", app)
        label("Dialogue preset", app); label("Night preset", app)
        label("Custom Equalizer", app); label("Defaults and Undo", app)
        jump("Advanced options", app)
        label("No independent observation is available", app)
        jump("Privacy and storage", app)
        label("No audio recorded by this app", app)
        label("Only your appearance choice is saved locally", app)
        screenshot("Advanced privacy", app)
    }

    func testTutorialRoutesAcrossPagesAndRestoresOrigin() {
        let app = XCUIApplication(); app.launch()
        app.buttons["Help & tutorials"].tap(); app.buttons["Home and coverage"].tap()
        label("Step 1 of 4", app)
        app.buttons["Next"].tap(); label("Step 2 of 4", app); label("Six setup checks unknown", app)
        app.buttons["Next"].tap(); label("Step 3 of 4", app); label("No observed events", app)
        app.buttons["Back"].tap(); label("Step 2 of 4", app)
        XCUIDevice.shared.press(.home); app.activate(); label("Step 2 of 4", app)
        app.buttons["Close tutorial"].tap(); label("Your listening space.", app)
        app.buttons["Help & tutorials"].tap(); app.buttons["Sound options"].tap()
        app.buttons["Next"].tap(); label("Step 2 of 4", app)
        screenshot("Contextual Sound tutorial", app)
        app.buttons["Close tutorial"].tap()
        app.buttons["Help & tutorials"].tap(); app.buttons["Session transfer"].tap()
        label("Step 1 of 2", app); app.buttons["Next"].tap(); label("Step 2 of 2", app); app.buttons["Done"].tap()
        label("Unknown physical state", app)
    }

    func testExampleAppearanceAndFutureFeatureDoNotClaimAudio() {
        let app = XCUIApplication(); app.launch(); tab("insights", app)
        label("No measurements yet", app); tap("Explore an example", app)
        label("EXAMPLE · synthetic data", app); label("Relative level (0–100)", app)
        screenshot("Example chart clearly labeled", app)
        tap("Read chart values", app); label("Sample 4: 64 relative units", app)
        tap("Close example", app); label("No measurements yet", app)
        tab("settings", app); tap("Daylight", app)
        XCTAssertEqual(app.buttons["Daylight"].value as? String, "Selected")
        screenshot("Daylight Settings", app)
        tab("home", app); screenshot("Daylight Home", app); label("Unknown physical state", app)
        tab("settings", app); tap("Midnight", app); tap("Hide advanced options", app)
        tap("Voice requests", app); label("This app is not listening for commands", app); app.buttons["Got it"].tap()
        tab("home", app); label("Unknown physical state", app)
    }

    func testLargestTextKeepsPagesHelpAndTutorialExitReachable() {
        let app = XCUIApplication()
        app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch()
        let help = app.buttons["Help & tutorials"]
        XCTAssertTrue(help.isHittable); XCTAssertGreaterThanOrEqual(help.frame.height, 44)
        app.buttons["page-picker"].tap(); app.buttons["Devices"].tap()
        help.tap()
        let readiness = app.buttons["Readiness checklist"]
        for _ in 0..<5 where !readiness.isHittable { app.swipeUp() }
        XCTAssertTrue(readiness.isHittable); readiness.tap()
        let close = app.buttons["Close tutorial"]
        XCTAssertTrue(close.isHittable); XCTAssertGreaterThanOrEqual(close.frame.height, 44)
        XCTAssertGreaterThan(close.frame.width, app.frame.width * 0.8)
        XCTAssertGreaterThan(close.frame.minY, help.frame.maxY)
        XCTAssertLessThan(close.frame.maxY, app.buttons["page-picker"].frame.minY)
        screenshot("Largest text themed tutorial", app)
        close.tap(); XCTAssertTrue(help.isHittable)
        app.buttons["page-picker"].tap(); app.buttons["Home"].tap(); label("Unknown physical state", app)
    }
}
