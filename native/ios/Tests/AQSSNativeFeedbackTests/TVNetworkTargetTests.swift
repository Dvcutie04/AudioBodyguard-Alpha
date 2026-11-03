import XCTest
@testable import AQSSNativeFeedback

final class TVNetworkTargetTests: XCTestCase {
    func testOnlyCanonicalPrivateUnicastCandidatesAreAccepted() {
        for address in ["10.0.0.1", "10.255.255.254", "172.16.0.1", "172.31.255.254", "192.168.1.105"] {
            XCTAssertEqual(AQSSLocalTVTarget(address)?.address, address)
        }
        XCTAssertEqual(AQSSLocalTVTarget(" 192.168.1.105\n")?.octets, [192, 168, 1, 105])
    }

    func testNoDnsUrlPublicLoopbackBroadcastOrAlternateNumberSyntax() {
        for address in ["", "tv.local", "https://192.168.1.2", "192.168.1.2:7345", "8.8.8.8",
                        "127.0.0.1", "0.0.0.0", "169.254.1.1", "224.0.0.1", "255.255.255.255",
                        "172.15.1.1", "172.32.1.1", "192.169.1.1", "10.0.0.0", "10.0.0.255",
                        "::1", "::ffff:192.168.1.1", "192.168.1", "192..1.1", "192.168.1.1.",
                        "192.168.1.256", "192.168.01.1", "+10.0.0.1", "0xa000001", "167772161",
                        "１０.0.0.1", "10.0.0.1/path", "10.0.0.1\n10.0.0.2", String(repeating: " ", count: 65)] {
            XCTAssertNil(AQSSLocalTVTarget(address), address)
        }
    }

    func testWorkAndEvidenceScopeStayBounded() {
        XCTAssertEqual(AQSSLocalTVTarget.ports, [7345, 9000])
        XCTAssertEqual(AQSSLocalTVTarget.timeoutSeconds, 4)
        XCTAssertEqual(AQSSLocalTVTarget.boundary, "TV identity, pairing and audio protection are not verified.")
    }

    func testEveryTrialOutcomeIsHistoricalPrivateAndNeverPairingEvidence() throws {
        let build = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: 1.0.0\nBuild: 10.1"
        for outcome in TVTrialOutcome.allCases {
            let report = try TVTrialReport.capture(buildDetails: build, outcome: outcome, reviewedAtMillis: 0)
            XCTAssertTrue(report.text.contains("Outcome: " + outcome.rawValue))
            XCTAssertTrue(report.text.contains("1970-01-01T00:00:00.000Z"))
            XCTAssertTrue(report.text.contains("TV identity: Not verified\nTV pairing: Not verified\nAudio protection: Not verified"))
            XCTAssertTrue(report.text.contains(build))
            XCTAssertFalse(report.text.contains("192.168.1.105"))
            XCTAssertLessThan(report.text.utf8.count, 4096)
        }
    }

    func testTrialReviewRetainsOneImmutableOutcomeAndExactBuild() throws {
        let build = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: 1.0.0\nBuild: 10.1"
        let first = try TVTrialReport.capture(buildDetails: build, outcome: .serviceAnswered, reviewedAtMillis: 0)
        _ = try TVTrialReport.capture(buildDetails: build, outcome: .noResponse, reviewedAtMillis: 1000)
        XCTAssertTrue(first.text.contains("Outcome: SERVICE_ANSWERED_UNVERIFIED"))
        XCTAssertFalse(first.text.contains("NO_SERVICE_RESPONSE"))
        XCTAssertThrowsError(try TVTrialReport.capture(buildDetails: build + "\nTV IP: secret", outcome: .stopped, reviewedAtMillis: 0))
        XCTAssertThrowsError(try TVTrialReport.capture(buildDetails: build, outcome: .stopped, reviewedAtMillis: -1))
        XCTAssertThrowsError(try TVTrialReport.capture(buildDetails: build, outcome: .stopped, reviewedAtMillis: 253_402_300_800_000))
    }
}
