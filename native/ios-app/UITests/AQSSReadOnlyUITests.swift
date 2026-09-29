import XCTest

final class AQSSReadOnlyUITests: XCTestCase {
    private func label(_ text: String, _ app: XCUIApplication) {
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", text)).firstMatch.waitForExistence(timeout: 10), "Missing: \(text)")
    }
    private func tap(_ title: String, _ app: XCUIApplication) {
        let button = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", title)).firstMatch
        guard button.waitForExistence(timeout: 10) else { XCTFail("Missing button: \(title)"); return }
        let scroll = app.scrollViews["home-scroll"]
        // isHittable can be true for a sliver of a button whose center lies
        // under the fixed page bar or tutorial footer. Bring the whole control
        // into the content viewport before XCTest taps its center.
        func insideViewport() -> Bool {
            let visible = button.frame.intersection(scroll.frame)
            return !visible.isNull && visible.height >= min(44, button.frame.height)
                && scroll.frame.contains(CGPoint(x: button.frame.midX, y: button.frame.midY))
        }
        for _ in 0..<16 {
            if button.isHittable && insideViewport() { break }
            // A fast swipe can pass the target completely. Use a short drag
            // without momentum, and recover in either direction if necessary.
            let below = button.frame.midY >= scroll.frame.midY
            let start = scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: below ? 0.75 : 0.35))
            let end = scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: below ? 0.35 : 0.75))
            start.press(forDuration: 0.1, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.1)
        }
        guard button.isHittable && insideViewport() else {
            screenshot("Unreachable \(title)", app)
            XCTFail("Unreachable button within content viewport: \(title)"); return
        }
        button.tap()
    }
    private func tab(_ id: String, _ app: XCUIApplication) { app.buttons["tab-\(id)"].tap() }
    private func jump(_ title: String, _ app: XCUIApplication) { app.buttons["Jump to"].tap(); app.buttons[title].tap() }
    private func screenshot(_ name: String, _ app: XCUIApplication) {
        let shot = XCTAttachment(screenshot: app.screenshot()); shot.name = name; shot.lifetime = .keepAlways; add(shot)
    }

    func testAllFivePagesKeepHelpAndTruthfulEmptyStates() {
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.buttons["start-beginner-tour"].isHittable)
        label("does not monitor or change audio", app)
        screenshot("00 Beginner welcome", app)
        jump("Coverage", app)
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

    func testBeginnerTourOrderInteractiveExampleThemeExitAndReplay() {
        let app = XCUIApplication(); app.launch()
        app.buttons["start-beginner-tour"].tap()
        label("Step 1 of 5", app); XCTAssertFalse(app.buttons["Back"].isEnabled)
        screenshot("Beginner 1 Welcome", app)
        app.buttons["Next"].tap(); label("Step 2 of 5", app); label("Six setup checks unknown", app)
        app.buttons["Back"].tap(); label("Step 1 of 5", app)
        app.buttons["Next"].tap(); app.buttons["Next"].tap()
        label("Step 3 of 5", app); label("Sound options", app)
        app.buttons["Next"].tap(); label("Step 4 of 5", app)
        tap("Explore an example", app); label("EXAMPLE · synthetic data", app)
        screenshot("Beginner 4 Example", app)
        tap("Read chart values", app); label("Sample 4: 64 relative units", app)
        label("Step 4 of 5", app)
        app.buttons["Next"].tap(); label("Step 5 of 5", app)
        tap("Daylight", app); label("Step 5 of 5", app)
        screenshot("Beginner 5 Daylight", app)
        app.buttons["Done"].tap(); label("TOUR FINISHED", app)
        XCTAssertFalse(app.buttons["Close tutorial"].exists)
        XCTAssertTrue(app.buttons["start-beginner-tour"].isHittable)
        app.buttons["start-beginner-tour"].tap(); label("Step 1 of 5", app)
        app.buttons["Close tutorial"].tap()
        jump("Coverage", app); label("Unknown physical state", app)
        tab("settings", app); tap("Midnight", app)
        app.buttons["Help & tutorials"].tap(); app.buttons["Start here · 5-step tour"].tap()
        app.buttons["Next"].tap(); app.buttons["Close tutorial"].tap()
        label("Make space for you.", app)
        tab("home", app)
        tap("Step 3. Explore sound features", app); label("Step 3 of 5", app)
        app.buttons["Close tutorial"].tap()
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
        tap("Start 5-step tour", app); label("Step 1 of 5", app)
        XCTAssertTrue(app.buttons["Next"].isHittable)
        XCTAssertTrue(app.buttons["Close tutorial"].isHittable)
        screenshot("Largest text beginner tutorial", app)
        app.buttons["Close tutorial"].tap()
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
