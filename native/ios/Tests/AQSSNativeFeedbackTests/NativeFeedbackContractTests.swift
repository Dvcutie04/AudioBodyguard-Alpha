import Foundation
import XCTest
@testable import AQSSNativeFeedback

final class NativeFeedbackContractTests: XCTestCase {
    private func contractData() throws -> Data {
        var root = URL(fileURLWithPath: #filePath)
        for _ in 0..<5 {
            root.deleteLastPathComponent()
        }
        return try Data(contentsOf: root.appendingPathComponent("contracts/tv_selection_native_feedback_v1.json"))
    }

    func testSharedFixtureDecodesWithSwiftModels() throws {
        let data = try contractData()
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertEqual(object["schema_version"] as? Int, 1)
        XCTAssertEqual(object["capability"] as? String, "feedback_sync_only")
        let cases = try XCTUnwrap(object["cases"] as? [[String: Any]])
        XCTAssertFalse(cases.isEmpty)

        for fixture in cases {
            let requestObject = try XCTUnwrap(fixture["request"] as? [String: Any])
            let expectedObject = try XCTUnwrap(fixture["expected"] as? [String: Any])
            let requestData = try JSONSerialization.data(withJSONObject: requestObject)
            let expectedData = try JSONSerialization.data(withJSONObject: expectedObject)
            let errorObject = expectedObject["error"] as? [String: Any]
            let errorCode = errorObject?["code"] as? String

            if errorCode == "INVALID_FEEDBACK" {
                XCTAssertThrowsError(try JSONDecoder().decode(NativeFeedbackSyncRequest.self, from: requestData))
            } else {
                let request = try JSONDecoder().decode(NativeFeedbackSyncRequest.self, from: requestData)
                XCTAssertFalse(request.events.isEmpty)
                XCTAssertEqual(request.events.first?.schemaVersion, 1)
            }

            let response = try JSONDecoder().decode(NativeFeedbackSyncResponse.self, from: expectedData)
            XCTAssertEqual(response.schemaVersion, 1)
            XCTAssertEqual(response.ok, expectedObject["ok"] as? Bool)
        }
    }
}
