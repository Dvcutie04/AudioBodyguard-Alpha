import XCTest
@testable import AQSSNativeFeedback

final class GuideProgressTests: XCTestCase {
    func testChoicesGateEachNextStepAndNeverSkip() {
        var guide = AQSSGuideProgress()
        XCTAssertFalse(guide.next()); XCTAssertFalse(guide.start("unknown"))
        XCTAssertTrue(guide.start("getting_started")); guide.back(); XCTAssertEqual(guide.index, 0)
        XCTAssertTrue(guide.next()); XCTAssertEqual(guide.step?.target, "chooseTV")
        XCTAssertFalse(guide.next()); XCTAssertFalse(guide.select("alexa")); XCTAssertFalse(guide.select("invented"))
        XCTAssertTrue(guide.select("samsung")); XCTAssertTrue(guide.next())
        XCTAssertEqual(guide.step?.target, "chooseHome"); XCTAssertFalse(guide.next())
        XCTAssertTrue(guide.select("alexa")); XCTAssertTrue(guide.next())
        XCTAssertEqual(guide.step?.target, "connectionPlan")
        XCTAssertEqual(guide.selected("chooseTV")?.title, "Samsung")
        guide.back(); XCTAssertEqual(guide.selected("chooseHome")?.id, "alexa")
        XCTAssertTrue(guide.select("neither")); XCTAssertTrue(guide.next())
        while guide.next() {}
        XCTAssertTrue(guide.isLast); XCTAssertEqual(guide.index, 5); XCTAssertFalse(guide.next())
        guide.close(); XCTAssertNil(guide.topic); XCTAssertTrue(guide.selections.isEmpty)
        XCTAssertTrue(guide.start("getting_started")); XCTAssertEqual(guide.index, 0); XCTAssertNil(guide.selected("chooseTV"))
    }
    func testRestoreCannotBypassMissingOrInvalidChoices() {
        var guide = AQSSGuideProgress()
        guide.restore("getting_started", index: 100, selections: [:]); XCTAssertEqual(guide.index, 1)
        guide.restore("getting_started", index: 6, selections: ["chooseTV": "invalid", "chooseHome": "alexa"]); XCTAssertEqual(guide.index, 1)
        guide.restore("getting_started", index: 6, selections: ["chooseTV": "unsure"]); XCTAssertEqual(guide.index, 2)
        guide.restore("getting_started", index: 6, selections: ["chooseTV": "unsure", "chooseHome": "neither"]); XCTAssertEqual(guide.index, 5)
        guide.restore("getting_started", index: -9, selections: [:]); XCTAssertEqual(guide.index, 0)
    }
    func testEveryTopicHasAReachableEndWithoutInventingADevice() {
        for topic in AQSSTutorialContent.topics {
            var guide = AQSSGuideProgress(); guide.start(topic.id)
            for _ in 0..<topic.steps.count {
                if let choice = guide.choices.last { XCTAssertTrue(guide.select(choice.id)) }
                if !guide.next() { break }
            }
            XCTAssertTrue(guide.isLast, topic.id)
        }
    }
    func testPictureCompletionAdvancesOnlyTheExpectedLocalConnectionSection() {
        var guide = AQSSGuideProgress()
        XCTAssertFalse(guide.completePictures(expectedTarget: "connectionPlan", routeID: "samsung_ok"))
        guide.start("getting_started")
        XCTAssertFalse(guide.completePictures(expectedTarget: "connectionPlan", routeID: "samsung_ok"))
        guide.restore("getting_started", index: 3, selections: ["chooseTV": "samsung", "chooseHome": "alexa"])
        for route in ["unknown", "voice", "identify", "roku_phone", "samsung_model_new"] {
            XCTAssertFalse(guide.completePictures(expectedTarget: "connectionPlan", routeID: route))
            XCTAssertEqual(guide.index, 3)
        }
        XCTAssertFalse(guide.completePictures(expectedTarget: "connectionCheck", routeID: "samsung_ok"))
        XCTAssertTrue(guide.completePictures(expectedTarget: "connectionPlan", routeID: "roku_network"))
        XCTAssertEqual(guide.step?.target, "connectionCheck")
        XCTAssertTrue(guide.completePictures(expectedTarget: "connectionCheck", routeID: "roku_phone"))
        guide.restore("getting_started", index: 3, selections: ["chooseTV": "samsung", "chooseHome": "alexa"])
        XCTAssertTrue(guide.completePictures(expectedTarget: "connectionPlan", routeID: "samsung_ok"))
        XCTAssertEqual(guide.step?.target, "connectionCheck")
        XCTAssertFalse(guide.completePictures(expectedTarget: "connectionPlan", routeID: "samsung_ok"))
        XCTAssertTrue(guide.completePictures(expectedTarget: "connectionCheck", routeID: "samsung_ok"))
        XCTAssertTrue(guide.isLast)
        guide.start("readiness")
        XCTAssertFalse(guide.completePictures(expectedTarget: "connectionPlan", routeID: "samsung_ok"))
        XCTAssertEqual(guide.index, 0)
    }
}
