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

    private func assertLabel(_ label: String, in app: XCUIApplication) {
        let element = app.descendants(matching: .any)
            .matching(NSPredicate(format: "label CONTAINS %@", label)).firstMatch
        XCTAssertTrue(element.waitForExistence(timeout: 10), "Missing simulated UI label: \(label)")
    }
}
