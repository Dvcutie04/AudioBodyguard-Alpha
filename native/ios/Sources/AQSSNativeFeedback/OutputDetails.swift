import Foundation

/// Closed vocabulary: never a port name, address or persistent identifier.
public enum IOSOutputKind: CaseIterable, Equatable {
    case speaker, receiver, headphones, bluetoothA2DP, bluetoothHFP, bluetoothLE
    case airPlay, usb, hdmi, lineOut, car, other
    public var title: String {
        switch self {
        case .speaker: return "Built-in speaker"
        case .receiver: return "Built-in receiver"
        case .headphones: return "Headphones"
        case .bluetoothA2DP: return "Bluetooth A2DP"
        case .bluetoothHFP: return "Bluetooth hands-free"
        case .bluetoothLE: return "Bluetooth LE"
        case .airPlay: return "AirPlay"
        case .usb: return "USB audio"
        case .hdmi: return "HDMI audio"
        case .lineOut: return "Line out"
        case .car: return "Car audio"
        case .other: return "Other output"
        }
    }
}

public enum OutputDetailsError: Error { case invalidBuild, invalidOSVersion, invalidClock, invalidCounts, oversizedReport }

/// An immutable manual session query, never proof of active playback or hardware format.
public struct OutputDetailsSnapshot: Equatable {
    public static let maxPorts = 16
    public static let maxUTF16Units = 8192
    public static let maxUTF8Bytes = 16384
    public static let notice = "Session details only. Playback and protection are not verified."
    public let buildDetails: String
    public let capturedAtMillis: Int64
    public let portTypes: [IOSOutputKind]
    public let totalReported: Int
    public let summary: String
    public let text: String

    private init(buildDetails: String, capturedAtMillis: Int64, portTypes: [IOSOutputKind],
                 totalReported: Int, summary: String, text: String) {
        self.buildDetails = buildDetails; self.capturedAtMillis = capturedAtMillis
        self.portTypes = portTypes; self.totalReported = totalReported
        self.summary = summary; self.text = text
    }

    public static func capture(buildDetails: String, osVersion: String, portTypes: [IOSOutputKind],
                               totalReported: Int, capturedAtMillis: Int64) throws -> Self {
        try validateBuild(buildDetails)
        guard Array(osVersion.utf8.prefix(17)).count <= 16 else { throw OutputDetailsError.invalidOSVersion }
        let parts = osVersion.split(separator: ".", omittingEmptySubsequences: false)
        guard osVersion == "Unavailable" || ((1...3).contains(parts.count) && parts.allSatisfy {
            (1...3).contains($0.utf8.count) && $0.utf8.allSatisfy { (48...57).contains($0) }
        }) else { throw OutputDetailsError.invalidOSVersion }
        guard totalReported >= 0, portTypes.count <= maxPorts,
              portTypes.count == min(totalReported, maxPorts) else { throw OutputDetailsError.invalidCounts }
        guard (0...253_402_300_799_999).contains(capturedAtMillis) else { throw OutputDetailsError.invalidClock }
        // Format whole seconds and the integer remainder separately; far-future
        // Double date precision must not round a 999-ms timestamp into another year.
        let utc = ISO8601DateFormatter(); utc.timeZone = TimeZone(secondsFromGMT: 0)
        utc.formatOptions = [.withInternetDateTime]
        let seconds = utc.string(from: Date(timeIntervalSince1970: Double(capturedAtMillis / 1000)))
        let clock = String(seconds.dropLast()) + String(format: ".%03dZ", Int(capturedAtMillis % 1000))
        let outputs = portTypes.isEmpty ? "No output ports reported" : portTypes.enumerated()
            .map { "Output \($0.offset + 1): \($0.element.title)" }.joined(separator: "\n")
        let retained = totalReported > maxPorts ? "First 16 retained; \(totalReported - maxPorts) additional outputs omitted" : "All reported outputs retained"
        let summary = "Reported outputs: \(totalReported)\n\(outputs)\n\(retained)"
        let text = ["Audio Bodyguard iPhone output details (v1)", "Captured at (phone clock, UTC): \(clock)",
                    "", buildDetails, "iOS/iPadOS version: \(osVersion)", "",
                    "Source: iOS audio session current-route output port types", summary,
                    "Port names and identifiers: Not included", "Audio session active: Unknown", "",
                    "This is a session metadata snapshot, not a list of every available device.",
                    "This check does not activate or configure the audio session.",
                    "Actual playback route: Unknown", "Negotiated format: Unknown",
                    "Backend and ownership review: Pending", "Independent capture: Not recorded",
                    "Calibration and clock mapping: Unknown", "Physical output and protection: Not verified",
                    "Outputs may have changed since this snapshot.", "", notice].joined(separator: "\n")
        guard text.utf16.count <= maxUTF16Units, text.utf8.count <= maxUTF8Bytes else { throw OutputDetailsError.oversizedReport }
        return Self(buildDetails: buildDetails, capturedAtMillis: capturedAtMillis, portTypes: portTypes,
                    totalReported: totalReported, summary: summary, text: text)
    }

    private static func validateBuild(_ value: String) throws {
        guard Array(value.utf16.prefix(513)).count <= 512 else { throw OutputDetailsError.invalidBuild }
        let lines = value.components(separatedBy: "\n")
        guard lines.count == 4, lines[0] == "Audio Bodyguard", lines[1] == "Platform: iPhone/iPad",
              lines[2].hasPrefix("Version: "), lines[3].hasPrefix("Build: ") else { throw OutputDetailsError.invalidBuild }
        let version = String(lines[2].dropFirst(9)), build = String(lines[3].dropFirst(7))
        guard (1...96).contains(version.utf16.count), !version.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              version.unicodeScalars.allSatisfy({ scalar in
                  switch scalar.properties.generalCategory {
                  case .control, .format, .lineSeparator, .paragraphSeparator: return false
                  default: return true
                  }
              }), build == "Unavailable" || ((1...19).contains(build.utf8.count) && build.utf8.allSatisfy({ (48...57).contains($0) }))
        else { throw OutputDetailsError.invalidBuild }
    }
}
