import XCTest

final class AQSSReadOnlyUITests: XCTestCase {
    private func label(_ text: String, _ app: XCUIApplication) {
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", text)).firstMatch.waitForExistence(timeout: 10), "Missing: \(text)")
    }
    private func tap(_ title: String, _ app: XCUIApplication) {
        // Match within the active surface. A sheet can coexist with an
        // identically named button on the page underneath it.
        let scroll = app.scrollViews["setup-scroll"].exists ? app.scrollViews["setup-scroll"] : app.scrollViews["menu-scroll"].exists ? app.scrollViews["menu-scroll"] : app.scrollViews["guide-scroll"].exists ? app.scrollViews["guide-scroll"] : app.scrollViews["home-scroll"]
        let button = scroll.buttons.matching(NSPredicate(format: "label CONTAINS %@", title)).firstMatch
        guard button.waitForExistence(timeout: 10) else { screenshot("Missing \(title)", app); XCTFail("Missing button: \(title)"); return }
        // isHittable can be true for a sliver of a button whose center lies
        // under the fixed page bar or tutorial footer. Bring the whole control
        // into the content viewport before XCTest taps its center.
        func insideViewport() -> Bool {
            let viewport = scroll.frame.intersection(app.frame).insetBy(dx: 0, dy: 24)
            let visible = button.frame.intersection(viewport)
            return !visible.isNull && visible.height >= min(44, button.frame.height)
                && viewport.contains(CGPoint(x: button.frame.midX, y: button.frame.midY))
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
        let visible = button.frame.intersection(scroll.frame.intersection(app.frame).insetBy(dx: 0, dy: 24))
        app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: visible.midX, dy: visible.midY)).tap()
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

    func testInputToolsStartIdleAndNeverClaimAConnection() {
        let app = launch()
        tab("sound", app); tap("Voice check", app)
        label("Microphone off", app); label("No words recognized yet", app)
        XCTAssertTrue(app.buttons["voice-start-stop"].exists)
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("Voice check idle", app)
        app.buttons["Close"].firstMatch.tap()
        tab("devices", app); tap("TV photo setup", app)
        label("No photo selected", app); label("Brand: Not identified", app)
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("TV photo setup idle", app)
        app.buttons["Close"].firstMatch.tap()
        tab("home", app); label("Unknown physical state", app)
    }

    func testAllFivePagesKeepHelpAndTruthfulEmptyStates() {
        let app = launch()
        XCTAssertTrue(app.buttons["start-beginner-tour"].isHittable)
        label("does not monitor or change TV audio", app)
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
        XCTAssertFalse(app.buttons["guide-next"].isEnabled)
        XCTAssertFalse(app.buttons["choice-alexa"].exists)
        tap("Samsung", app); XCTAssertEqual(app.buttons["choice-samsung"].value as? String, "Selected")
        screenshot("Guide 2 TV selection", app)
        next(app); label("Step 3 of 7", app)
        XCTAssertFalse(app.buttons["guide-next"].isEnabled)
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
        next(app); XCTAssertFalse(app.buttons["guide-next"].isEnabled)
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
        label("No audio files saved by this app", app)
        label("Appearance and guide dismissal stay on this phone", app)
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
        jump("Privacy and storage", app); label("No audio files saved by this app", app)
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
        tap("Voice requests", app); label("No command is sent by Voice check", app); app.buttons["Got it"].tap()
        tab("home", app); label("Unknown physical state", app)
    }

    func testRokuPicturesResumeAndFinishWithoutClaimingConnection() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app)
        tap("TCL", app); tap("Roku TV", app); tap("Find my IP address", app)
        tap("I’m already in Settings", app); label("Step 3 of 5", app)
        XCTAssertTrue(app.otherElements["setup-illustration"].exists)
        screenshot("Roku matching Settings Network picture", app)
        let started = Date()
        app.buttons["setup-next"].tap()
        XCTAssertTrue(app.staticTexts["setup-progress"].waitForExistence(timeout: 2))
        XCTAssertEqual(app.staticTexts["setup-progress"].label, "Step 4 of 5")
        print("SIMULATOR_GUIDE_DRIVER_SECONDS=\(Date().timeIntervalSince(started)) includes XCTest tap overhead")
        app.buttons["setup-close"].tap()
        tap("Illustrated setup guides", app); tap("TCL", app); tap("Roku TV", app); tap("Find my IP address", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Resume guide")
        app.buttons["setup-next"].tap(); label("Step 4 of 5", app)
        screenshot("Roku About selection and resumed step", app)
        app.buttons["setup-next"].tap(); label("Step 5 of 5", app)
        screenshot("Roku IP address information diagram", app)
        app.buttons["setup-next"].tap()
        tab("home", app); label("Unknown physical state", app)
    }

    func testIllustratedGuideFromTCLPlanAndVoiceHelp() {
        let app = launch(true)
        next(app); tap("TCL", app); next(app); tap("Google Home", app); next(app)
        tap("Show TCL steps", app)
        tap("Google TV / Android TV", app); tap("TCL QM851G", app); label("85QM851G", app)
        app.buttons["setup-next"].tap(); label("Step 1 of 12", app)
        screenshot("TCL illustrated TV first setup", app)
        app.buttons["setup-next"].tap(); app.buttons["setup-next"].tap()
        label("Step 3 of 12", app)
        XCTAssertTrue(app.otherElements["setup-illustration"].exists)
        tap("My screen looks different", app)
        label("Pause at this step", app)
        app.buttons["setup-back"].tap(); label("Step 3 of 12", app)
        app.buttons["setup-close"].tap(); label("Step 4 of 7", app)
        tap("Show Google Home steps", app); tap("SmartThings → Google Home", app)
        app.buttons["setup-next"].tap()
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        label("Choose the provider path", app)
        screenshot("Google Home illustrated provider linking", app)
        app.buttons["setup-close"].tap(); exit(app)
        tab("settings", app); tap("Hide advanced options", app); tap("Voice requests", app)
        app.alerts.buttons["Show voice steps"].tap()
        label("Step 1 of 9", app)
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        label("Speak and watch the meter", app)
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("Voice help illustrated steps", app)
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        app.buttons["setup-next"].tap()
        label("Microphone off", app); label("No words recognized yet", app)
        app.buttons["Close"].firstMatch.tap()
        tab("home", app); label("Unknown physical state", app)
    }

    func testIllustratedApprovalFinishesWithoutClaimingConnection() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Samsung", app)
        tap("Samsung — TV shows OK approval", app); app.buttons["setup-next"].tap()
        for _ in 0..<13 { app.buttons["setup-next"].tap() }
        label("Approve on the television", app)
        screenshot("Samsung illustrated TV approval", app)
        app.buttons["setup-next"].tap(); app.buttons["setup-next"].tap()
        label("Check the actual result", app)
        app.buttons["setup-next"].tap()
        label("No qualified device connected", app)
        tap("Illustrated setup guides", app); tap("Amazon Alexa", app); tap("Roku TV → Alexa", app)
        app.buttons["setup-next"].tap()
        for _ in 0..<6 { app.buttons["setup-next"].tap() }
        label("Review Roku approval", app)
        screenshot("Alexa illustrated account approval", app)
        app.buttons["setup-close"].tap()
        tab("home", app); label("Unknown physical state", app)
    }

    func testNewBrandPicturesAreReachable() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Philips", app)
        tap("Philips Google TV — pair the voice remote", app)
        app.buttons["setup-next"].tap()
        label("Start with your TV home screen", app)
        app.buttons["setup-next"].tap()
        label("Open the profile menu", app)
        screenshot("Philips illustrated profile choice", app)
        app.buttons["setup-close"].tap()
        tab("home", app); label("Unknown physical state", app)
    }

    func testIllustratedGuideKeepsScrollContainerAndResetsPosition() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "YES", "--aqss-trace-navigation"]
        app.launch(); tab("devices", app); tap("Illustrated setup guides", app)
        let scroll = app.scrollViews["setup-scroll"]
        let instance = scroll.value as? String
        XCTAssertNotNil(UUID(uuidString: instance ?? ""))
        tap("TCL", app); tap("Roku TV", app); tap("Find my IP address", app)
        tap("I’m already in Settings", app); label("Step 3 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        scroll.swipeUp()
        app.buttons["setup-next"].tap(); label("Step 4 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        // A new step must start at its heading, even after scrolling the old one.
        let heading = app.staticTexts["Open About"]
        XCTAssertTrue(heading.waitForExistence(timeout: 5))
        XCTAssertTrue(heading.isHittable)
        XCTAssertLessThan(heading.frame.minY, scroll.frame.minY + 100)
        app.buttons["setup-back"].tap(); label("Step 3 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        tap("My screen looks different", app); label("Pause at this step", app)
        app.buttons["setup-back"].tap(); label("Step 3 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        screenshot("Stable scrolling container after Next Back and help", app)
    }

    func testSelectingATVDoesNotMoveItsButtonOrReplaceTheScroll() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "NO", "--aqss-trace-navigation"]
        app.launch(); next(app); label("Step 2 of 7", app)
        let scroll = app.scrollViews["guide-scroll"]
        let instance = scroll.value as? String
        XCTAssertFalse(instance?.isEmpty ?? true)
        let button = app.buttons["choice-samsung"]
        let before = button.frame
        XCTAssertFalse(app.buttons["guide-next"].isEnabled)
        tap("Samsung", app)
        XCTAssertTrue(app.buttons["guide-next"].isEnabled)
        XCTAssertEqual(button.frame.minY, before.minY, accuracy: 1)
        XCTAssertEqual(scroll.value as? String, instance)
        next(app); label("Step 3 of 7", app)
        XCTAssertEqual(scroll.value as? String, instance)
        XCTAssertFalse(app.buttons["guide-next"].isEnabled)
        tap("Google Home", app); next(app); label("Step 4 of 7", app)
        app.buttons["Back"].tap(); label("Step 3 of 7", app)
        XCTAssertEqual(app.buttons["choice-google"].value as? String, "Selected")
        XCTAssertEqual(scroll.value as? String, instance)
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
        // A page sheet can still be dismissing after the navigation tap.
        // Assert reachability after the transition, not during its animation.
        let helpReady = XCTNSPredicateExpectation(predicate: NSPredicate(format: "hittable == true"), object: app.buttons["Help & tutorials"])
        XCTAssertEqual(XCTWaiter.wait(for: [helpReady], timeout: 5), .completed)
        XCTAssertTrue(app.buttons["Help & tutorials"].isHittable)
        app.buttons["Help & tutorials"].tap(); tap("Readiness checklist", app)
        label("Step 1 of 6", app); assertOnlyGuide(app)
        screenshot("Largest text contextual guide", app)
        exit(app); XCTAssertTrue(app.buttons["page-picker"].isHittable)
        tap("Illustrated setup guides", app); tap("Samsung", app)
        tap("Samsung — TV shows OK approval", app); app.buttons["setup-next"].tap()
        label("Step 1 of 16", app)
        XCTAssertTrue(app.buttons["setup-close"].isHittable)
        XCTAssertTrue(app.buttons["setup-next"].isHittable)
        XCTAssertGreaterThanOrEqual(app.buttons["setup-next"].frame.height, 44)
        screenshot("Largest text illustrated setup", app)
        app.buttons["setup-close"].tap()
    }
}
