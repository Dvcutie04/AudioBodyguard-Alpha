import XCTest

final class AQSSReadOnlyUITests: XCTestCase {
    func testRoseExitResumesTheExactTutorialAndHeadStaysDisconnected() {
        let app = launch(true)
        next(app); tap("LG", app); next(app); tap("Google Home", app); next(app)
        label("Step 4 of 6", app)
        tap("Show Google Home steps", app)
        XCTAssertTrue(app.buttons["setup-route-google_lg"].exists)
        XCTAssertFalse(app.buttons["setup-route-google_samsung"].exists)
        XCTAssertFalse(app.buttons["setup-route-google_roku"].exists)
        XCTAssertEqual(app.buttons["setup-close"].label, "Back to Tutorial")
        app.buttons["setup-close"].tap(); label("Step 4 of 6", app)
        exit(app); label("HOME", app); label("Connection not verified", app)
        XCTAssertTrue(app.images["connection-head"].label.contains("Black and white"))
        tap("Back to Tutorial", app); label("Step 4 of 6", app)
        app.buttons["Back"].tap(); label("Step 3 of 6", app)
        XCTAssertEqual(app.buttons["choice-google"].value as? String, "Selected")
        screenshot("Rose navigation returns to the exact tutorial", app)
    }

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
        tab("home", app); label("Connection not verified", app)
    }

    func testAllFivePagesKeepHelpAndTruthfulEmptyStates() {
        let app = launch()
        XCTAssertTrue(app.buttons["start-beginner-tour"].isHittable)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "does not monitor or change TV audio")).firstMatch.exists)
        screenshot("00 Beginner welcome", app)
        jump("Coverage", app)
        label("Connection not verified", app); label("No output observation", app)
        screenshot("01 Midnight Home", app)
        for (id, title) in [("sound", "SOUND"), ("devices", "DEVICES"), ("insights", "INSIGHTS"), ("settings", "SETTINGS")] {
            tab(id, app); label(title, app)
            XCTAssertTrue(app.buttons["Help & tutorials"].isHittable)
            screenshot("Page \(id)", app)
        }
        XCTAssertFalse(app.staticTexts["Make space for you."].exists)
        app.buttons["Help & tutorials"].tap(); label("Make space for you.", app)
        tap("Cancel", app)
        jump("Readiness checklist", app); label("Six setup checks unknown", app)
        jump("Session transfer", app); label("No supported endpoint or verified transfer path", app)
        tab("home", app); label("Connection not verified", app)
    }

    func testFirstVisitHasOnePathChoiceGatesTailoredPlanAndReplay() {
        let app = launch(true)
        label("Step 1 of 6", app); assertOnlyGuide(app)
        label("Both connections are required", app)
        label("1. Connect to your TV or home device", app)
        label("2. Connect to your phone", app)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Skip series intros")).firstMatch.exists)
        XCTAssertTrue(app.buttons["guide-next"].isHittable)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Voice input display and recognized words")).firstMatch.exists)
        label("Picture guide", app)
        XCTAssertFalse(app.staticTexts["What we're building"].exists)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Planned controls")).firstMatch.exists)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "This preview does not")).firstMatch.exists)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "a film is quiet, then an advert")).firstMatch.exists)
        XCTAssertFalse(app.buttons["Back"].exists)
        XCTAssertFalse(app.buttons["choice-samsung"].exists)
        screenshot("Guide 1 Welcome", app)
        tap("More features", app)
        label("Planned", app)
        label("Skip series intros", app)
        label("Voice input display and recognized words", app)
        label("Voice activated control", app)
        XCTAssertFalse(app.staticTexts["Picture guides and photo-assisted setup"].exists)
        let firstFeature = app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Skip series intros")).firstMatch
        let scroll = app.scrollViews["guide-scroll"]
        for _ in 0..<12 {
            if firstFeature.frame.midY < scroll.frame.midY { break }
            scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.7)).press(forDuration: 0.1,
                thenDragTo: scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.4)), withVelocity: .slow, thenHoldForDuration: 0.1)
        }
        XCTAssertTrue(firstFeature.isHittable)
        screenshot("Guide 1 Replacement feature list", app)
        tap("Fewer features", app)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Skip series intros")).firstMatch.exists)
        XCTAssertTrue(app.buttons["guide-next"].isHittable)
        next(app); label("Step 2 of 6", app); assertOnlyGuide(app)
        XCTAssertFalse(app.buttons["guide-next"].isEnabled)
        XCTAssertFalse(app.buttons["choice-alexa"].exists)
        tap("Samsung", app); XCTAssertEqual(app.buttons["choice-samsung"].value as? String, "Selected")
        screenshot("Guide 2 TV selection", app)
        next(app); label("Step 3 of 6", app)
        XCTAssertFalse(app.buttons["guide-next"].isEnabled)
        tap("Amazon Alexa", app); next(app)
        label("Step 4 of 6", app)
        XCTAssertTrue(app.buttons["setup-from-samsung"].exists)
        XCTAssertTrue(app.buttons["setup-from-alexa"].exists)
        screenshot("Guide 4 Tailored connection", app)
        app.buttons["Back"].tap(); label("Step 3 of 6", app)
        XCTAssertEqual(app.buttons["choice-alexa"].value as? String, "Selected")
        next(app); next(app); label("Step 5 of 6", app)
        label("2. Connect to your phone", app)
        screenshot("Guide 5 Phone connection", app)
        label("follow the pictures", app); assertOnlyGuide(app)
        XCTAssertTrue(app.buttons["setup-from-samsung"].exists)
        next(app); label("Step 6 of 6", app)
        next(app); XCTAssertTrue(app.buttons["tab-home"].isHittable)
        label("Connection not verified", app)
        app.buttons["start-beginner-tour"].tap(); label("Step 1 of 6", app)
        next(app); XCTAssertFalse(app.buttons["guide-next"].isEnabled)
        exit(app); tab("sound", app)
        XCTAssertFalse(app.staticTexts["Dialogue preset"].exists)
        tap("Options", app); label("Dialogue preset", app)
        tab("devices", app)
        XCTAssertFalse(app.staticTexts["Six setup checks unknown"].exists)
        tap("More device details", app); label("Six setup checks unknown", app)
        app.terminate(); app.launchArguments = []; app.launch()
        XCTAssertFalse(app.buttons["exit-tutorial"].exists)
        XCTAssertTrue(app.buttons["tab-home"].isHittable)
    }

    func testOptionsAndAdvancedRemainUnavailable() {
        let app = launch(); tab("sound", app)
        XCTAssertFalse(app.staticTexts["Dialogue preset"].exists)
        tap("Options", app); tap("More details", app)
        label("No qualified device volume control", app)
        label("Dialogue preset", app); label("Night preset", app)
        label("Custom Equalizer", app); label("Defaults and Undo", app)
        jump("Advanced options", app)
        tap("More details", app)
        // Physical output is a separate optional explanation.
        tap("More details", app)
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
        exit(app); label("HOME", app)
        app.buttons["page-back"].tap(); label("SETTINGS", app)
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
        XCTAssertFalse(app.staticTexts["Explore the direction. These features are not active."].exists)
        screenshot("Daylight Settings", app)
        tab("home", app); screenshot("Daylight Home", app); label("Connection not verified", app)
        tab("settings", app); tap("Midnight", app); tap("More features", app)
        tap("Voice requests", app); label("Voice control requires device authority and checked output", app); app.buttons["Got it"].tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testRokuPicturesResumeAndFinishWithoutClaimingConnection() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app)
        tap("TCL", app); tap("Roku TV", app); tap("Start TV setup", app)
        tap("More details", app)
        tap("I’m already in Settings", app); label("Step 3 of 5", app)
        app.buttons["setup-back"].tap()
        XCTAssertFalse(app.staticTexts["setup-progress"].exists)
        XCTAssertTrue(app.buttons["setup-next"].exists)
        tap("I’m already in Settings", app); label("Step 3 of 5", app)
        XCTAssertTrue(app.otherElements["setup-illustration"].exists)
        screenshot("Roku matching Settings Network picture", app)
        let started = Date()
        app.buttons["setup-next"].tap()
        XCTAssertTrue(app.staticTexts["setup-progress"].waitForExistence(timeout: 2))
        XCTAssertEqual(app.staticTexts["setup-progress"].label, "Step 4 of 5")
        print("SIMULATOR_GUIDE_DRIVER_SECONDS=\(Date().timeIntervalSince(started)) includes XCTest tap overhead")
        app.buttons["setup-close"].tap()
        tap("Illustrated setup guides", app); tap("TCL", app); tap("Roku TV", app); tap("Start TV setup", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Resume guide")
        app.buttons["setup-next"].tap(); label("Step 4 of 5", app)
        screenshot("Roku About selection and resumed step", app)
        app.buttons["setup-next"].tap(); label("Step 5 of 5", app)
        screenshot("Roku IP address information diagram", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Finish part one")
        app.buttons["setup-next"].tap()
        label("2. Connect to your phone (Roku)", app)
        app.buttons["setup-back"].tap(); label("Step 5 of 5", app)
        app.buttons["setup-next"].tap(); label("2. Connect to your phone (Roku)", app)
        XCTAssertTrue(["Start part two", "Resume guide"].contains(app.buttons["setup-next"].label))
        app.buttons["setup-next"].tap(); label("Step 1 of 5", app)
        screenshot("Roku phone app setup begins", app)
        app.buttons["setup-close"].tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testSimpleDefaultsAndBackRestoreTheActualPreviousPage() {
        let app = launch()
        XCTAssertFalse(app.staticTexts["No output observation"].exists)
        tap("Status details", app); label("No output observation", app)
        tab("devices", app)
        XCTAssertFalse(app.staticTexts["Six setup checks unknown"].exists)
        tap("Illustrated setup guides", app); tap("TCL", app); tap("Roku TV", app)
        XCTAssertTrue(app.buttons["setup-route-roku_network"].exists)
        XCTAssertFalse(app.buttons["setup-route-roku_model"].exists)
        XCTAssertFalse(app.buttons["setup-route-roku_alexa"].exists)
        XCTAssertFalse(app.links.firstMatch.exists)
        screenshot("Simple Roku setup choices", app)
        tap("Other setup options", app)
        tap("Find my exact model", app)
        XCTAssertFalse(app.buttons["setup-references"].exists)
        screenshot("Simple model guide introduction", app)
        tap("More details", app)
        XCTAssertTrue(app.buttons["setup-references"].exists)
        XCTAssertFalse(app.links.firstMatch.exists)
        app.buttons["setup-back"].tap()
        XCTAssertTrue(app.buttons["setup-route-roku_model"].exists)
        app.buttons["setup-back"].tap()
        XCTAssertTrue(app.buttons["setup-platform-tcl_roku"].exists)
        app.buttons["setup-back"].tap()
        XCTAssertTrue(app.buttons["setup-group-tcl"].exists)
        app.buttons["setup-close"].tap(); label("DEVICES", app)
        tab("sound", app)
        XCTAssertFalse(app.buttons["Help with options"].exists)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "A qualified device and observed result")).firstMatch.exists)
        let pageLabel = app.staticTexts["SOUND"]
        XCTAssertTrue(pageLabel.waitForExistence(timeout: 5))
        XCTAssertGreaterThanOrEqual(pageLabel.frame.minY, app.scrollViews["home-scroll"].frame.minY + 8)
        tap("Options", app)
        tab("settings", app)
        XCTAssertFalse(app.staticTexts["Device and route"].exists)
        app.buttons["page-back"].tap(); label("SOUND", app)
        label("Dialogue preset", app)
        app.buttons["page-back"].tap(); label("DEVICES", app)
        app.buttons["page-back"].tap(); label("Connection not verified", app)
        label("No output observation", app)
        screenshot("Back restores previous page and details", app)
        tab("devices", app); tab("home", app)
        XCTAssertFalse(app.staticTexts["No output observation"].exists)
    }

    func testRokuPartOneImmediatelyOpensPhonePicturesInFirstVisit() {
        let app = launch(true)
        next(app); tap("TCL", app); next(app); tap("Neither / not sure", app); next(app)
        tap("Show TCL steps", app); tap("Roku TV", app); tap("Start TV setup", app)
        tap("More details", app)
        tap("I’m already in Settings", app)
        for _ in 0..<2 { app.buttons["setup-next"].tap() }
        label("Step 5 of 5", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Finish part one")
        app.buttons["setup-next"].tap()
        label("2. Connect to your phone (Roku)", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Start part two")
        app.buttons["setup-next"].tap(); label("Step 1 of 5", app)
        screenshot("First visit Roku phone guide", app)
        app.buttons["setup-close"].tap()
        label("Step 5 of 6", app)
        label("2. Connect to your phone", app)
    }

    func testIllustratedGuideFromTCLPlanAndVoiceHelp() {
        let app = launch(true)
        next(app); tap("TCL", app); next(app); tap("Google Home", app); next(app)
        tap("Show TCL steps", app)
        tap("Google TV / Android TV", app); tap("Other setup options", app); tap("TCL QM851G", app)
        tap("More details", app); label("85QM851G", app)
        app.buttons["setup-next"].tap(); label("Step 1 of 12", app)
        screenshot("TCL illustrated TV first setup", app)
        app.buttons["setup-next"].tap(); app.buttons["setup-next"].tap()
        label("Step 3 of 12", app)
        XCTAssertTrue(app.otherElements["setup-illustration"].exists)
        tap("More details", app); tap("My screen looks different", app)
        label("Find the right screen", app)
        app.buttons["setup-back"].tap(); label("Step 3 of 12", app)
        app.buttons["setup-close"].tap(); label("Step 4 of 6", app)
        tap("Show Google Home steps", app)
        XCTAssertFalse(app.buttons["setup-route-google_samsung"].exists)
        tap("first setup with Google Home", app)
        app.buttons["setup-next"].tap()
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        label("Open Devices", app)
        screenshot("Google Home setup matches the selected TCL system", app)
        app.buttons["setup-close"].tap(); exit(app)
        tab("settings", app); tap("More features", app); tap("Voice requests", app)
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
        tab("home", app); label("Connection not verified", app)
    }

    func testIllustratedApprovalFinishesWithoutClaimingConnection() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Samsung", app)
        tap("Samsung — TV shows OK approval", app); app.buttons["setup-next"].tap()
        XCTAssertFalse(app.staticTexts["Use your real device. This picture is an illustration."].exists)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Illustrations may differ from your screen")).firstMatch.exists)
        for _ in 0..<14 { app.buttons["setup-next"].tap() }
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
        tab("home", app); label("Connection not verified", app)
    }

    func testFinishedPairingPicturesAdvanceLocallyAndCloseKeepsThePhoneStep() {
        let app = launch(true)
        next(app); tap("Samsung", app); next(app); tap("Neither", app); next(app)
        tap("Show Samsung steps", app); tap("Samsung — TV shows OK approval", app)
        app.buttons["setup-close"].tap(); label("Step 4 of 6", app)
        tap("Show Samsung steps", app); tap("Samsung — TV shows OK approval", app)
        app.buttons["setup-next"].tap()
        for _ in 0..<16 { app.buttons["setup-next"].tap() }
        label("Check the actual result", app)
        app.buttons["setup-next"].tap()
        label("Step 5 of 6", app); label("2. Connect to your phone", app)
        label("follow the pictures", app)
        XCTAssertFalse(app.staticTexts["Not connected · Audio protection is not active"].exists)
        tap("Need help?", app); label("official phone app", app)
        tap("Hide help", app)
        screenshot("Picture completion continues to phone setup", app)
        tap("Phone Wi-Fi pictures", app)
        label("iPhone — connect to your home Wi-Fi", app)
        app.buttons["setup-next"].tap(); label("Step 1 of 6", app)
        app.buttons["setup-next"].tap(); label("iPhone • Settings", app)
        screenshot("iPhone Wi-Fi uses the iPhone Settings menu", app)
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        label("blue checkmark", app)
        screenshot("iPhone Wi-Fi final check", app)
        app.buttons["setup-next"].tap()
        label("Step 5 of 6", app)
        tap("Show Samsung steps", app); tap("Samsung — TV shows OK approval", app)
        app.buttons["setup-close"].tap(); label("Step 5 of 6", app)
        exit(app); label("Connection not verified", app)
    }

    func testNewBrandPicturesAreReachable() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Philips", app); tap("Google TV / Android TV", app); tap("Other setup options", app)
        tap("Philips Google TV — pair the voice remote", app)
        app.buttons["setup-next"].tap()
        label("Start with your TV home screen", app)
        app.buttons["setup-next"].tap()
        label("Open the profile menu", app)
        screenshot("Philips illustrated profile choice", app)
        app.buttons["setup-close"].tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testIllustratedGuideKeepsScrollContainerAndResetsPosition() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "YES", "--aqss-trace-navigation"]
        app.launch(); tab("devices", app); tap("Illustrated setup guides", app)
        let scroll = app.scrollViews["setup-scroll"]
        let instance = scroll.value as? String
        XCTAssertNotNil(UUID(uuidString: instance ?? ""))
        tap("TCL", app); tap("Roku TV", app); tap("Start TV setup", app)
        tap("More details", app)
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
        tap("More details", app); tap("My screen looks different", app); label("Find the right screen", app)
        app.buttons["setup-back"].tap(); label("Step 3 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        screenshot("Stable scrolling container after Next Back and help", app)
    }

    func testSelectingATVDoesNotMoveItsButtonOrReplaceTheScroll() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "NO", "--aqss-trace-navigation"]
        app.launch(); next(app); label("Step 2 of 6", app)
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
        next(app); label("Step 3 of 6", app)
        XCTAssertEqual(scroll.value as? String, instance)
        XCTAssertFalse(app.buttons["guide-next"].isEnabled)
        tap("Google Home", app); next(app); label("Step 4 of 6", app)
        app.buttons["Back"].tap(); label("Step 3 of 6", app)
        XCTAssertEqual(app.buttons["choice-google"].value as? String, "Selected")
        XCTAssertEqual(scroll.value as? String, instance)
    }

    func testLargestTextKeepsExitAndNextReachable() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "NO", "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch(); label("Step 1 of 6", app); assertOnlyGuide(app)
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
        app.buttons["page-back"].tap(); label("DEVICES", app)
        tap("Illustrated setup guides", app); tap("Samsung", app)
        tap("Samsung — TV shows OK approval", app); app.buttons["setup-next"].tap()
        label("Step 1 of 17", app)
        XCTAssertTrue(app.buttons["setup-close"].isHittable)
        XCTAssertTrue(app.buttons["setup-next"].isHittable)
        XCTAssertGreaterThanOrEqual(app.buttons["setup-next"].frame.height, 44)
        screenshot("Largest text illustrated setup", app)
        app.buttons["setup-close"].tap()
    }
}
