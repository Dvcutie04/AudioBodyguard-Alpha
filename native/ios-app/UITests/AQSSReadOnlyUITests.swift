import XCTest

final class AQSSReadOnlyUITests: XCTestCase {
    private func label(_ text: String, _ app: XCUIApplication) {
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", text)).firstMatch.waitForExistence(timeout: 10), "Missing: \(text)")
    }
    private func tap(_ title: String, _ app: XCUIApplication) {
        let button = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", title)).firstMatch
        guard button.waitForExistence(timeout: 10) else { XCTFail("Missing button: \(title)"); return }
        let scroll = app.scrollViews["menu-scroll"].exists ? app.scrollViews["menu-scroll"] : app.scrollViews["guide-scroll"].exists ? app.scrollViews["guide-scroll"] : app.scrollViews["home-scroll"]
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
    private func launch(_ firstVisit: Bool = false) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", firstVisit ? "NO" : "YES"]
        app.launch(); return app
    }
    private func next(_ app: XCUIApplication) { app.buttons["guide-next"].tap() }
    private func exit(_ app: XCUIApplication) { app.buttons["exit-tutorial"].tap() }
    private func assertOnlyGuide(_ app: XCUIApplication) {
        XCTAssertFalse(app.buttons["tab-home"].exists)
        XCTAssertFalse(app.buttons["Help & tutorials"].exists)
        XCTAssertFalse(app.buttons["Jump to"].exists)
        XCTAssertFalse(app.scrollViews["home-scroll"].exists)
        XCTAssertTrue(app.buttons["exit-tutorial"].isHittable)
    }
    private func tab(_ id: String, _ app: XCUIApplication) { app.buttons["tab-\(id)"].tap() }
    private func jump(_ title: String, _ app: XCUIApplication) { app.buttons["Jump to"].tap(); tap(title, app) }
    private func screenshot(_ name: String, _ app: XCUIApplication) {
        let shot = XCTAttachment(screenshot: app.screenshot()); shot.name = name; shot.lifetime = .keepAlways; add(shot)
    }

    func testAllFivePagesKeepHelpAndTruthfulEmptyStates() {
        let app = launch()
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

    func testFirstVisitHasOnePathChoiceGatesTailoredPlanAndReplay() {
        let app = launch(true)
        label("Step 1 of 7", app); assertOnlyGuide(app)
        XCTAssertFalse(app.buttons["Back"].exists)
        XCTAssertFalse(app.buttons["choice-samsung"].exists)
        screenshot("Guide 1 Welcome", app)
        next(app); label("Step 2 of 7", app); assertOnlyGuide(app)
        XCTAssertFalse(app.buttons["guide-next"].exists)
        XCTAssertFalse(app.buttons["choice-alexa"].exists)
        tap("Samsung", app); XCTAssertEqual(app.buttons["choice-samsung"].value as? String, "Selected")
        screenshot("Guide 2 TV selection", app)
        next(app); label("Step 3 of 7", app)
        XCTAssertFalse(app.buttons["guide-next"].exists)
        tap("Amazon Alexa", app); next(app)
        label("Step 4 of 7", app); label("Samsung", app); label("Amazon Alexa", app)
        screenshot("Guide 4 Tailored connection", app)
        app.buttons["Back"].tap(); label("Step 3 of 7", app)
        XCTAssertEqual(app.buttons["choice-alexa"].value as? String, "Selected")
        next(app); next(app); label("Step 5 of 7", app)
        label("not connected to Audio Bodyguard", app); assertOnlyGuide(app)
        next(app); label("Step 6 of 7", app); next(app); label("Step 7 of 7", app)
        next(app); XCTAssertTrue(app.buttons["tab-home"].isHittable)
        label("TOUR FINISHED", app)
        app.buttons["start-beginner-tour"].tap(); label("Step 1 of 7", app)
        next(app); XCTAssertFalse(app.buttons["guide-next"].exists)
        exit(app); tab("sound", app); label("Dialogue preset", app)
        tab("devices", app); label("Six setup checks unknown", app)
        app.terminate(); app.launchArguments = []; app.launch()
        XCTAssertFalse(app.buttons["exit-tutorial"].exists)
        XCTAssertTrue(app.buttons["tab-home"].isHittable)
    }

    func testOptionsAndAdvancedRemainUnavailable() {
        let app = launch(); tab("sound", app)
        label("No qualified device volume control", app)
        label("Dialogue preset", app); label("Night preset", app)
        label("Custom Equalizer", app); label("Defaults and Undo", app)
        jump("Advanced options", app)
        label("No independent observation is available", app)
        jump("Privacy and storage", app)
        label("No audio recorded by this app", app)
        label("Your appearance and guide dismissal are saved locally", app)
        screenshot("Advanced privacy", app)
    }

    func testExitAtWelcomeAndContextualGuideRestoreFullApp() {
        let app = launch(true); exit(app)
        XCTAssertTrue(app.buttons["tab-home"].isHittable)
        tab("settings", app)
        app.buttons["Help & tutorials"].tap(); tap("Home and coverage", app)
        label("Step 1 of 4", app); assertOnlyGuide(app)
        next(app); label("Step 2 of 4", app)
        next(app); label("Step 3 of 4", app)
        app.buttons["Back"].tap(); label("Step 2 of 4", app)
        XCUIDevice.shared.press(.home); app.activate(); label("Step 2 of 4", app)
        exit(app); label("Make space for you.", app)
        jump("Privacy and storage", app); label("No audio recorded by this app", app)
        app.buttons["Help & tutorials"].tap(); tap("Sound options", app)
        next(app); label("Step 2 of 4", app); screenshot("Contextual Sound guide", app)
        exit(app); XCTAssertTrue(app.buttons["Help & tutorials"].isHittable)
    }

    func testExampleAppearanceAndFutureFeatureDoNotClaimAudio() {
        let app = launch(); tab("insights", app)
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

    func testLargestTextKeepsExitAndNextReachable() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "NO", "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch(); label("Step 1 of 7", app); assertOnlyGuide(app)
        XCTAssertTrue(app.buttons["guide-next"].isHittable)
        XCTAssertGreaterThanOrEqual(app.buttons["exit-tutorial"].frame.height, 44)
        screenshot("Largest text single-step guide", app)
        next(app); tap("Samsung", app)
        XCTAssertTrue(app.buttons["guide-next"].isHittable)
        exit(app)
        app.buttons["page-picker"].tap(); tap("Devices", app)
        XCTAssertTrue(app.buttons["Help & tutorials"].isHittable)
        app.buttons["Help & tutorials"].tap(); tap("Readiness checklist", app)
        label("Step 1 of 6", app); assertOnlyGuide(app)
        screenshot("Largest text contextual guide", app)
        exit(app); XCTAssertTrue(app.buttons["page-picker"].isHittable)
    }
}
