import XCTest
@testable import AQSSNativeFeedback

final class GuideProgressTests: XCTestCase {
    func testConfirmedPhotoSkipsTheOptionalHomeQuestionAndBackReturnsToTV() {
        for index in [0, 1] {
            var guide = AQSSGuideProgress()
            guide.restore("getting_started", index: index, selections: [:])
            for invalid in [nil, "invented", "alexa", "unsure"] as [String?] {
                XCTAssertFalse(guide.acceptPhotoBrand(invalid)); XCTAssertEqual(guide.index, index)
            }
            XCTAssertTrue(guide.acceptPhotoBrand("samsung"))
            XCTAssertEqual(guide.step?.target, "connectionPlan")
            XCTAssertEqual(guide.selected("chooseHome")?.id, "neither")
            XCTAssertFalse(guide.acceptPhotoBrand("lg"))
            guide.back(); XCTAssertEqual(guide.step?.target, "chooseTV")
        }
        var guide = AQSSGuideProgress(); guide.start("readiness")
        XCTAssertFalse(guide.acceptPhotoBrand("samsung")); XCTAssertFalse(guide.selectHomeApp("google"))
    }
    func testChoicesGateEachNextStepAndNeverSkip() {
        var guide = AQSSGuideProgress()
        XCTAssertFalse(guide.next()); XCTAssertFalse(guide.start("unknown"))
        XCTAssertTrue(guide.start("getting_started")); guide.back(); XCTAssertEqual(guide.index, 0)
        XCTAssertTrue(guide.next()); XCTAssertEqual(guide.step?.target, "chooseTV")
        XCTAssertFalse(guide.next()); XCTAssertFalse(guide.select("alexa")); XCTAssertFalse(guide.select("invented"))
        XCTAssertTrue(guide.select("samsung")); XCTAssertTrue(guide.next())
        XCTAssertEqual(guide.step?.target, "connectionPlan")
        XCTAssertEqual(guide.selected("chooseHome")?.id, "neither")
        XCTAssertEqual(guide.stepNumber, 3); XCTAssertEqual(guide.stepCount, 5)
        XCTAssertTrue(guide.selectHomeApp("alexa")); XCTAssertFalse(guide.selectHomeApp("invented"))
        XCTAssertEqual(guide.selected("chooseTV")?.title, "Samsung")
        guide.back(); XCTAssertEqual(guide.step?.target, "chooseTV")
        XCTAssertEqual(guide.selected("chooseHome")?.id, "alexa")
        XCTAssertTrue(guide.select("lg")); XCTAssertTrue(guide.next())
        XCTAssertEqual(guide.step?.target, "connectionPlan")
        while guide.next() {}
        XCTAssertTrue(guide.isLast); XCTAssertEqual(guide.index, 5); XCTAssertFalse(guide.next())
        guide.close(); XCTAssertNil(guide.topic); XCTAssertTrue(guide.selections.isEmpty)
        XCTAssertTrue(guide.start("getting_started")); XCTAssertEqual(guide.index, 0); XCTAssertNil(guide.selected("chooseTV"))
    }
    func testRestoreCannotBypassMissingOrInvalidChoices() {
        var guide = AQSSGuideProgress()
        guide.restore("getting_started", index: 100, selections: [:]); XCTAssertEqual(guide.index, 1)
        guide.restore("getting_started", index: 6, selections: ["chooseTV": "invalid", "chooseHome": "alexa"]); XCTAssertEqual(guide.index, 1)
        guide.restore("getting_started", index: 6, selections: ["chooseTV": "unsure"]); XCTAssertEqual(guide.index, 5)
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
    func testSamsungPhonePicturesAdvanceOnlyThePhonePart() {
        var guide = AQSSGuideProgress()
        guide.restore("getting_started", index: 3, selections: ["chooseTV": "samsung", "chooseHome": "neither"])
        XCTAssertFalse(guide.completePictures(expectedTarget: "connectionPlan", routeID: "samsung_phone"))
        XCTAssertEqual(guide.index, 3)
        XCTAssertTrue(guide.completePictures(expectedTarget: "connectionPlan", routeID: "samsung_pin"))
        XCTAssertTrue(guide.completePictures(expectedTarget: "connectionCheck", routeID: "samsung_phone"))
        XCTAssertTrue(guide.isLast)
    }
    func testEveryBrandPhoneCompanionAdvancesOnlyThePhonePart() {
        for route in Set(AQSSSetupContent.groups.compactMap(\.phoneRoute)) {
            var guide = AQSSGuideProgress()
            guide.restore("getting_started", index: 3, selections: ["chooseTV": "lg", "chooseHome": "neither"])
            XCTAssertFalse(guide.completePictures(expectedTarget: "connectionPlan", routeID: route), route)
            XCTAssertEqual(guide.index, 3)
            XCTAssertTrue(guide.completePictures(expectedTarget: "connectionPlan", routeID: "lg_pair"))
            XCTAssertTrue(guide.completePictures(expectedTarget: "connectionCheck", routeID: route), route)
            XCTAssertTrue(guide.isLast)
        }
    }
}
