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
}
