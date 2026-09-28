import XCTest

final class AQSSReadOnlyUITests: XCTestCase {
    func testSimulationLaunchShowsUnknownCoverageAndUnavailableHandoff() {
        let app = XCUIApplication()
        app.launch()

        assertLabel("SIMULATION — no audio path connected", in: app)
        assertLabel("Unknown physical state", in: app)
        assertLabel("No output observation", in: app)
        assertLabel("Six setup checks unknown", in: app)

        let scrollView = app.scrollViews.firstMatch
        XCTAssertTrue(scrollView.exists)
        scrollView.swipeUp()
        scrollView.swipeUp()
        assertLabel("Moving a session between phones is not available here", in: app)

        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Read-only simulation screen"
        screenshot.lifetime = .keepAlways
        add(screenshot)
    }

    func testOptionsAndAdvancedDetailsStayReadOnlyInSimulation() {
        let app = XCUIApplication()
        app.launch()
        let scroll = app.scrollViews.firstMatch
        XCTAssertTrue(scroll.waitForExistence(timeout: 10))
        tapButton("Options", in: app, scrolling: scroll)
        assertLabel("Options preview — controls are unavailable", in: app)
        assertLabel("Dialogue preset", in: app)
        assertLabel("Night preset", in: app)
        assertLabel("No qualified device volume control", in: app)

        tapButton("Advanced options", in: app, scrolling: scroll)
        assertLabel("No independent observation is available", in: app)
        assertLabel("changes while away are unknown", in: app)

        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Read-only advanced options"
        screenshot.lifetime = .keepAlways
        add(screenshot)
    }

    private func tapButton(_ title: String, in app: XCUIApplication, scrolling scroll: XCUIElement) {
        let button = app.buttons[title]
        XCTAssertTrue(button.waitForExistence(timeout: 10), "Missing button: \(title)")
        for _ in 0..<8 where !button.isHittable { scroll.swipeUp() }
        XCTAssertTrue(button.isHittable, "Button outside the scroll view: \(title)")
        button.tap()
    }

    func testContextualTutorialCanNavigateCloseAndReplay() {
        let app = XCUIApplication()
        app.launch()
        app.buttons["Help & tutorials"].tap()
        app.buttons["Sound options"].tap()
        assertLabel("Step 1 of 4", in: app)
        app.buttons["Next"].tap()
        assertLabel("Step 2 of 4", in: app)
        assertLabel("Volume needs a supported output", in: app)
        let highlighted = app.descendants(matching: .any)
            .matching(NSPredicate(format: "value == %@", "Tutorial focus")).firstMatch
        XCTAssertTrue(highlighted.waitForExistence(timeout: 10))
        app.buttons["Back"].tap()
        assertLabel("Step 1 of 4", in: app)
        app.buttons["Close tutorial"].tap()
        XCTAssertFalse(app.buttons["Close tutorial"].exists)

        app.buttons["Help & tutorials"].tap()
        app.buttons["Advanced and privacy"].tap()
        assertLabel("Step 1 of 5", in: app)
        app.buttons["Next"].tap()
        app.buttons["Next"].tap()
        assertLabel("Step 3 of 5", in: app)
        assertLabel("Unknown physical state", in: app)
        app.buttons["Close tutorial"].tap()

        app.buttons["Help & tutorials"].tap()
        app.buttons["Captions"].tap()
        app.buttons["Next"].tap()
        assertLabel("Step 2 of 2", in: app)
        app.buttons["Done"].tap()
        XCTAssertFalse(app.buttons["Close tutorial"].exists)

        app.buttons["Help & tutorials"].tap()
        app.buttons["Sound options"].tap()
        assertLabel("Step 1 of 4", in: app)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Contextual tutorial with persistent help"
        screenshot.lifetime = .keepAlways
        add(screenshot)
    }

    private func assertLabel(_ label: String, in app: XCUIApplication) {
        let element = app.descendants(matching: .any)
            .matching(NSPredicate(format: "label CONTAINS %@", label)).firstMatch
        XCTAssertTrue(element.waitForExistence(timeout: 10), "Missing simulated UI label: \(label)")
    }

    func testQuickNavigationReadinessAndReturnKeepCoverageUnknown() {
        let app = XCUIApplication()
        app.launch()
        app.buttons["Jump to"].tap()
        app.buttons["Readiness checklist"].tap()
        assertLabel("These are unconfirmed requirements", in: app)
        for title in ["Output hardware", "Qualified path", "Permission and authority",
                      "Output route", "Runtime eligibility", "Independent observation"] {
            assertLabel(title, in: app)
        }
        let scroll = app.scrollViews["home-scroll"]
        tapButton("Help with readiness", in: app, scrolling: scroll)
        assertLabel("Step 1 of 6", in: app)
        app.buttons["Next"].tap()
        assertLabel("Step 2 of 6", in: app)
        app.buttons["Close tutorial"].tap()
        XCTAssertTrue(app.buttons["Hide readiness checklist"].exists)
        app.buttons["Jump to"].tap()
        app.buttons["Privacy and storage"].tap()
        assertLabel("No audio recorded by this app", in: app)
        XCUIDevice.shared.press(.home)
        app.activate()
        app.buttons["Jump to"].tap()
        app.buttons["Coverage"].tap()
        assertLabel("Unknown physical state", in: app)
        XCTAssertFalse(app.buttons["Hide options"].exists)
        XCTAssertFalse(app.buttons["Hide readiness checklist"].exists)
        keepScreenshot("Quick navigation and unknown coverage", app: app)
    }

    func testLargestTextKeepsNavigationAndTutorialExitReachable() {
        let app = XCUIApplication()
        app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch()
        let help = app.buttons["Help & tutorials"]
        XCTAssertGreaterThanOrEqual(help.frame.height, 44)
        XCTAssertTrue(help.isHittable)
        app.buttons["Jump to"].tap()
        app.buttons["Readiness checklist"].tap()
        help.tap()
        let readiness = app.buttons["Readiness checklist"]
        for _ in 0..<4 where !readiness.isHittable { app.swipeUp() }
        XCTAssertTrue(readiness.isHittable)
        readiness.tap()
        XCTAssertTrue(app.buttons["Close tutorial"].isHittable)
        XCTAssertGreaterThanOrEqual(app.buttons["Close tutorial"].frame.height, 44)
        // At accessibility sizes Close has its own full-width row, so its
        // visible title cannot be compressed into a third-width column.
        XCTAssertGreaterThan(app.buttons["Close tutorial"].frame.width, app.frame.width * 0.8)
        XCTAssertLessThan(app.buttons["Close tutorial"].frame.maxY, help.frame.minY)
        keepScreenshot("Largest text readiness tutorial", app: app)
        app.buttons["Close tutorial"].tap()
        XCTAssertTrue(help.isHittable)
    }

    private func keepScreenshot(_ name: String, app: XCUIApplication) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
