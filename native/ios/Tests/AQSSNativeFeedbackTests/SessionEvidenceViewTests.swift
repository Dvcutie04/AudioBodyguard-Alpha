import Foundation
import XCTest
@testable import AQSSNativeFeedback

final class SessionEvidenceViewTests: XCTestCase {
    private func fixture() throws -> [String: Any] {
        var root = URL(fileURLWithPath: #filePath)
        for _ in 0..<5 { root.deleteLastPathComponent() }
        let data = try Data(contentsOf: root.appendingPathComponent("contracts/session_evidence_view_v1.json"))
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    func testSharedReadOnlyCoverageVectors() throws {
        let document = try fixture()
        XCTAssertEqual(document["schema_version"] as? Int, 1)
        XCTAssertEqual(document["purpose"] as? String, "read_only_reference_projection_not_physical_qualification")
        let cases = try XCTUnwrap(document["coverage_cases"] as? [[String: Any]])
        XCTAssertGreaterThanOrEqual(cases.count, 10)
        for entry in cases {
            let identifier = try XCTUnwrap(entry["id"] as? String)
            let sample: AQSSCoverageSample?
            if let fields = entry["sample"] as? [String: Any] {
                let rawState = try XCTUnwrap(fields["state"] as? String)
                sample = AQSSCoverageSample(
                    runtimeId: try XCTUnwrap(fields["runtime"] as? String),
                    clockDomainId: try XCTUnwrap(fields["clock"] as? String),
                    receivedMonotonic: try XCTUnwrap(fields["received"] as? NSNumber).doubleValue,
                    expiresMonotonic: try XCTUnwrap(fields["expires"] as? NSNumber).doubleValue,
                    state: try XCTUnwrap(AQSSSessionState(rawValue: rawState)),
                    reason: try XCTUnwrap(fields["reason"] as? String),
                    userPaused: try XCTUnwrap(fields["user_paused"] as? Bool)
                )
            } else {
                sample = nil
            }
            let view = AQSSSessionEvidenceView.coverage(
                sample, runtimeId: try XCTUnwrap(entry["current_runtime"] as? String),
                clockDomainId: try XCTUnwrap(entry["current_clock"] as? String),
                nowMonotonic: try XCTUnwrap(entry["now"] as? NSNumber).doubleValue
            )
            XCTAssertEqual(view.state.rawValue, entry["expected_state"] as? String, identifier)
            XCTAssertEqual(view.reason, entry["expected_reason"] as? String, identifier)
        }
    }

    func testSharedReadOnlyCapabilityVectors() throws {
        let document = try fixture()
        let cases = try XCTUnwrap(document["capability_cases"] as? [[String: Any]])
        XCTAssertGreaterThanOrEqual(cases.count, 9)
        for entry in cases {
            let fields = try XCTUnwrap(entry["facts"] as? [String: Any])
            let facts = AQSSCapabilityFacts(
                hardware: fields["hardware"] as? Bool,
                qualification: fields["qualification"] as? Bool,
                permission: fields["permission"] as? Bool,
                route: fields["route"] as? Bool,
                runtime: fields["runtime"] as? Bool,
                evidence: fields["evidence"] as? Bool,
                observedMonotonic: try XCTUnwrap(fields["observed"] as? NSNumber).doubleValue,
                expiresMonotonic: try XCTUnwrap(fields["expires"] as? NSNumber).doubleValue,
                clockDomainId: try XCTUnwrap(fields["clock"] as? String)
            )
            let view = AQSSSessionEvidenceView.capability(
                facts, clockDomainId: try XCTUnwrap(entry["current_clock"] as? String),
                nowMonotonic: try XCTUnwrap(entry["now"] as? NSNumber).doubleValue
            )
            XCTAssertEqual(view.label, entry["expected"] as? String, entry["id"] as? String ?? "fixture")
            XCTAssertFalse(view.canActuate)
        }
    }

    func testMalformedLocalEvidenceNeverShowsActive() {
        let sample = AQSSCoverageSample(runtimeId: "runtime", clockDomainId: "clock",
                                        receivedMonotonic: .nan, expiresMonotonic: 3,
                                        state: .active, reason: "VALIDATED")
        XCTAssertEqual(AQSSSessionEvidenceView.coverage(sample, runtimeId: "runtime",
                                                       clockDomainId: "clock", nowMonotonic: 2).state,
                       .unknownPhysicalState)
    }
}
