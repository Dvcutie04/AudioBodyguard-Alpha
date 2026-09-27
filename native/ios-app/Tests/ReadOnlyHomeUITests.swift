import XCTest

final class ReadOnlyHomeUITests: XCTestCase {
    func testDisconnectedShellShowsUncertainty() {
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["SIMULATION — no audio path connected"].waitForExistence(timeout: 15))
        for label in ["Unknown physical state", "No output observation", "Six setup checks unknown"] {
            let matchingElement = app.descendants(matching: .any)
                .matching(NSPredicate(format: "label CONTAINS %@", label)).firstMatch
            XCTAssertTrue(matchingElement.exists, "Missing uncertainty label: \(label)")
        }
        XCTAssertEqual(app.buttons.count, 0, "This disconnected shell must have no controls")
    }
}
