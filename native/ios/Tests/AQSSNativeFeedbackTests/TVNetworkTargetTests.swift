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
}
