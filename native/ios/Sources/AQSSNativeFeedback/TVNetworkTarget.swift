import Foundation

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
