import XCTest
#if os(macOS)
import Network
import Security
#endif
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

    func testTrialFollowUpKeepsReachabilitySeparateFromReviewAndPairing() {
        XCTAssertEqual(TVTrialOutcome.addressRejected.followUp, .addressPictures)
        XCTAssertEqual(TVTrialOutcome.wifiRequired.followUp, .phoneWiFi)
        XCTAssertEqual(TVTrialOutcome.noResponse.followUp, .phoneWiFi)
        XCTAssertEqual(TVTrialOutcome.serviceAnswered.followUp, .review)
        for outcome in [TVTrialOutcome.unavailable, .stopped, .cleanupUnresolved] {
            XCTAssertNil(outcome.followUp)
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

#if os(macOS)
    func testCertificateObservationReadsTheFixtureLeafAndRefusesTLS() throws {
        guard #available(macOS 15.0, *) else { throw XCTSkip("Requires in-memory identity import") }
        // Reuse the Android loopback fixture so both transports check the same leaf.
        let nativeRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
        let fixture = nativeRoot.appendingPathComponent("android/src/test/resources/tv-loopback-fixture.p12.fixture")
        let data = try Data(contentsOf: fixture)
        var items: CFArray?
        let importOptions = [kSecImportExportPassphrase as String: "fixture-only",
                             kSecImportToMemoryOnly as String: true] as CFDictionary
        let status = SecPKCS12Import(data as CFData, importOptions, &items)
        XCTAssertEqual(status, errSecSuccess)
        let entry = try XCTUnwrap((items as? [[String: Any]])?.first)
        let identity = try XCTUnwrap(entry[kSecImportItemIdentity as String]) as! SecIdentity
        let serverOptions = NWProtocolTLS.Options()
        sec_protocol_options_set_local_identity(serverOptions.securityProtocolOptions,
                                                try XCTUnwrap(sec_identity_create(identity)))
        let serverParameters = NWParameters(tls: serverOptions)
        let loopback: NWEndpoint.Host = "127.0.0.1"
        serverParameters.requiredLocalEndpoint = .hostPort(host: loopback, port: .any)
        let listener = try NWListener(using: serverParameters)
        defer { listener.cancel() }

        let listening = expectation(description: "Synthetic TLS listener started")
        let serverRejected = expectation(description: "Server handshake was refused")
        listener.stateUpdateHandler = { state in
            if case .ready = state { listening.fulfill() }
        }
        listener.newConnectionHandler = { peer in
            peer.stateUpdateHandler = { state in
                switch state {
                case .failed:
                    serverRejected.fulfill()
                    peer.cancel()
                case .ready:
                    XCTFail("Observation let the server finish the handshake")
                    peer.cancel()
                case .cancelled:
                    peer.stateUpdateHandler = nil
                default: break
                }
            }
            peer.start(queue: .main)
        }
        listener.start(queue: .main)
        wait(for: [listening], timeout: 8)

        let observer = AQSSPeerCertificateObserver()
        XCTAssertNil(observer.fingerprint)
        let leafObserved = expectation(description: "Client observed the peer certificate and refused TLS")
        let options = observer.makeTLSOptions { leafObserved.fulfill() }
        let client = NWConnection(host: loopback, port: try XCTUnwrap(listener.port),
                                  using: NWParameters(tls: options))
        defer { client.cancel() }
        let clientClosed = expectation(description: "Client connection was cancelled")
        client.stateUpdateHandler = { state in
            if case .cancelled = state { clientClosed.fulfill() }
            if case .ready = state { XCTFail("Observation let the client finish the handshake") }
        }
        client.start(queue: .main)
        wait(for: [leafObserved, serverRejected], timeout: 8)
        client.cancel()
        wait(for: [clientClosed], timeout: 5)
        XCTAssertEqual(observer.fingerprint, "eb7b8b2d7b964b9513c28b8d64e4722047ee0eb83bc85644796587590be6e904")
    }
#endif
}
