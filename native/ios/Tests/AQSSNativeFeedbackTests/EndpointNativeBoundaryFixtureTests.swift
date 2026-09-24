// Synthetic conformance only. This test cannot certify a native output boundary.
import Foundation
import XCTest

final class EndpointNativeBoundaryFixtureTests: XCTestCase {
    private func fixture() throws -> [String: Any] {
        var root = URL(fileURLWithPath: #filePath)
        for _ in 0..<5 {
            root.deleteLastPathComponent()
        }
        let data = try Data(contentsOf: root.appendingPathComponent("contracts/endpoint_native_boundary_v1.json"))
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    private func syntheticEligible(_ trace: [String: Any]) -> Bool {
        guard let claim = trace["claim"] as? [String: Any],
              let activation = trace["activation"] as? [String: Any],
              let submission = trace["submission"] as? [String: Any],
              let native = trace["native"] as? [String: Any],
              let protection = trace["protection"] as? [String: Any],
              let times = trace["times"] as? [String: Any] else { return false }

        let fields = ["resource_id", "request_id", "controller_id", "fencing_token", "runtime_id", "stream_id", "route_id", "route_epoch", "continuity_id"]
        guard Set(claim.keys) == Set(fields), Set(activation.keys) == Set(fields), Set(submission.keys) == Set(fields) else { return false }
        for field in fields {
            if field == "fencing_token" || field == "route_epoch" {
                guard let issued = claim[field] as? Int,
                      let active = activation[field] as? Int,
                      let current = submission[field] as? Int,
                      issued == active && issued == current else { return false }
            } else {
                guard let issued = claim[field] as? String,
                      let active = activation[field] as? String,
                      let current = submission[field] as? String,
                      issued == active && issued == current else { return false }
            }
        }

        guard (protection["activation"] as? Bool) == true,
              (protection["submission"] as? Bool) == true else { return false }
        let flags = ["backend_qualified", "registry_complete", "evidence_authorized", "history_authenticated", "route_enforced", "cut_closed", "admission_closed", "publication_closed"]
        for flag in flags where (native[flag] as? Bool) != true {
            return false
        }
        guard let issuedAt = times["issued_at"] as? Int,
              let expiresAt = times["expires_at"] as? Int,
              let activationAt = times["activation_at"] as? Int,
              let submissionAt = times["submission_at"] as? Int,
              issuedAt <= activationAt && activationAt <= submissionAt && submissionAt < expiresAt else { return false }
        guard let disposition = native["output_disposition"] as? String,
              (disposition == "completed" || disposition == "discarded"),
              let retained = native["retained_generations"] as? [Int],
              let closed = native["closed_generations"] as? [Int],
              let retiredThrough = native["retired_through_generation"] as? Int,
              let work = native["work"] as? [[String: Any]],
              Set(retained).isSubset(of: Set(closed)) else { return false }
        for item in work {
            guard let generation = item["generation"] as? Int else { return false }
            if generation <= retiredThrough && (item["settled"] as? Bool) != true {
                return false
            }
        }
        return (native["actual_route_id"] as? String) == (claim["route_id"] as? String) && (native["actual_route_epoch"] as? Int) == (claim["route_epoch"] as? Int)
    }

    func testSharedSyntheticBoundaryVectors() throws {
        let document = try fixture()
        XCTAssertEqual(document["schema_version"] as? Int, 1)
        XCTAssertEqual(document["profile_id"] as? String, "AQSS/owned-pcm-gain-lab/v1")
        XCTAssertEqual(document["capability"] as? String, "test_only_trace_conformance")
        let baseline = try XCTUnwrap(document["baseline"] as? [String: Any])
        let cases = try XCTUnwrap(document["cases"] as? [[String: Any]])
        XCTAssertEqual(cases.count, 18)
        var identifiers = Set<String>()
        for fixtureCase in cases {
            let identifier = try XCTUnwrap(fixtureCase["id"] as? String)
            XCTAssertTrue(identifiers.insert(identifier).inserted, identifier)
            let expected = try XCTUnwrap(fixtureCase["eligible"] as? Bool)
            let changes = try XCTUnwrap(fixtureCase["changes"] as? [String: Any])
            var trace = baseline
            for (section, patch) in changes {
                var values = try XCTUnwrap(trace[section] as? [String: Any])
                let entries = try XCTUnwrap(patch as? [String: Any])
                for (key, value) in entries {
                    values[key] = value
                }
                trace[section] = values
            }
            XCTAssertEqual(syntheticEligible(trace), expected, identifier)
        }
    }
}
