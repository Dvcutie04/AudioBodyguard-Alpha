import Foundation
#if canImport(Network) && canImport(Security) && canImport(CryptoKit)
import CryptoKit
import Network
import Security

/// Observe one leaf certificate and always reject the handshake.
@available(macOS 12.0, *)
final class AQSSPeerCertificateObserver: @unchecked Sendable {
    private let lock = NSLock()
    private var digest: String?

    var fingerprint: String? {
        lock.lock()
        defer { lock.unlock() }
        return digest
    }

    func makeTLSOptions(onObservation: @escaping @Sendable () -> Void) -> NWProtocolTLS.Options {
        let options = NWProtocolTLS.Options()
        sec_protocol_options_set_verify_block(options.securityProtocolOptions, { [self] _, trust, complete in
            var didObserve = false
            defer {
                complete(false)
                if didObserve { onObservation() }
            }
            let peerTrust = sec_trust_copy_ref(trust).takeRetainedValue()
            guard SecTrustSetNetworkFetchAllowed(peerTrust, false) == errSecSuccess,
                  let chain = SecTrustCopyCertificateChain(peerTrust) as? [SecCertificate],
                  let leaf = chain.first else { return }
            let der = SecCertificateCopyData(leaf) as Data
            guard !der.isEmpty, der.count <= 16 * 1024 else { return }
            let fingerprint = SHA256.hash(data: der).map { String(format: "%02x", $0) }.joined()
            lock.lock()
            if digest == nil {
                digest = fingerprint
                didObserve = true
            }
            lock.unlock()
        }, DispatchQueue.global(qos: .userInitiated))
        return options
    }
}
#endif

/// A single explicitly entered private IPv4 host. This is not a TV identity.
public struct AQSSLocalTVTarget: Equatable, Sendable {
    public let address: String
    public let octets: [UInt8]
    public static let ports: [UInt16] = [7345, 9000]
    public static let timeoutSeconds = 4
    public static let boundary = "TV identity, pairing and audio protection are not verified."
    public static let invalidAddress = "Enter the private IPv4 address shown in your TV’s network settings."

    public init?(_ input: String) {
        guard input.utf8.count <= 64 else { return nil }
        let value = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty, value.utf8.count <= 15 else { return nil }
        let parts = value.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 4 else { return nil }
        var bytes: [UInt8] = []
        for part in parts {
            guard !part.isEmpty, part.utf8.allSatisfy({ $0 >= 48 && $0 <= 57 }),
                  part.count == 1 || part.first != "0", let byte = UInt8(part) else { return nil }
            bytes.append(byte)
        }
        let privateRange = bytes[0] == 10 || (bytes[0] == 172 && (16...31).contains(bytes[1]))
            || (bytes[0] == 192 && bytes[1] == 168)
        // Deliberately restrictive first diagnostic: no common network/broadcast suffix.
        guard privateRange, (1...254).contains(bytes[3]) else { return nil }
        address = value
        octets = bytes
    }
}

public enum TVTrialFollowUp: Equatable, Sendable {
    case addressPictures, phoneWiFi, review
}

public enum TVTrialOutcome: String, CaseIterable, Sendable {
    case addressRejected = "ADDRESS_REJECTED", wifiRequired = "WIFI_REQUIRED"
    case unavailable = "CHECK_UNAVAILABLE", serviceAnswered = "SERVICE_ANSWERED_UNVERIFIED"
    case noResponse = "NO_SERVICE_RESPONSE", stopped = "CHECK_STOPPED"
    case cleanupUnresolved = "CLEANUP_UNRESOLVED"

    public var followUp: TVTrialFollowUp? {
        switch self {
        case .addressRejected: return .addressPictures
        case .wifiRequired, .noResponse: return .phoneWiFi
        case .serviceAnswered: return .review
        case .unavailable, .stopped, .cleanupUnresolved: return nil
        }
    }
}

/// One explicitly reviewed, historical description. No host, free-text notes,
/// device identifier or authentication/actuation authority can enter this type.
public struct TVTrialReport: Equatable, Sendable {
    public let text: String
    private init(text: String) { self.text = text }
    public static let notice = "Historical check only. TV identity, pairing and protection are not verified."
    public static let betaScope = "Friends can try the setup pictures and phone sound/voice checks. The in-app network check tests VIZIO candidate services only. Other TV brands use their official app guides. TV control and audio protection are not available in this beta."

    public static func capture(buildDetails: String, outcome: TVTrialOutcome, reviewedAtMillis: Int64) throws -> Self {
        // Reuse the bounded installed-build and phone-clock validation.
        _ = try TestSetupReportSnapshot.capture(buildDetails: buildDetails, notes: [:], reviewedAtMillis: reviewedAtMillis)
        let utc = ISO8601DateFormatter()
        utc.timeZone = TimeZone(secondsFromGMT: 0)
        utc.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let clock = utc.string(from: Date(timeIntervalSince1970: Double(reviewedAtMillis) / 1000))
        let result: String
        switch outcome {
        case .addressRejected: result = "No native check started: the entered address was rejected."
        case .wifiRequired: result = "No native check started: a suitable Wi-Fi path was unavailable."
        case .unavailable: result = "No new native check started: previous work was closing or unavailable."
        case .serviceAnswered: result = "A TCP service answered at that moment. Its identity is not authenticated."
        case .noResponse: result = "The check ended without establishing a service response. The cause is unknown."
        case .stopped: result = "The check stopped. This is not a successful connection result."
        case .cleanupUnresolved: result = "Cleanup was not confirmed. Another check must remain blocked."
        }
        let text = ["Audio Bodyguard connection trial (v1)",
                    "Reviewed at (phone clock, UTC): " + clock, "", buildDetails, "",
                    "Selected test: VIZIO candidate TCP services (not a verified TV model)",
                    "Outcome: " + outcome.rawValue, result, "",
                    "No TV command or audio was sent by this check.",
                    "TV identity: Not verified", "TV pairing: Not verified", "Audio protection: Not verified", "",
                    notice, "No TV address, Wi-Fi name, password, audio or photo is included.",
                    "Reviewing or sharing this text does not authorize a device action."].joined(separator: "\n")
        return Self(text: text)
    }
}
