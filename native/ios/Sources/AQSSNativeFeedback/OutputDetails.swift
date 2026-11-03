import Foundation

/// Preserve the installed CFBundleVersion label, including TestFlight attempts.
/// Bounded report metadata only; this does not validate an App Store submission.
public enum IOSInstalledBuildLabel {
    public static func isValid(_ value: String) -> Bool {
        if value == "Unavailable" { return true }
        guard value.utf8.count <= 59 else { return false }
        let parts = value.split(separator: ".", omittingEmptySubsequences: false)
        return (1...3).contains(parts.count) && parts.allSatisfy {
            (1...19).contains($0.utf8.count) && $0.utf8.allSatisfy { (48...57).contains($0) }
        }
    }
}

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

/// A short, truthful next step derived only from the current-route port types.
/// It never names a device or upgrades metadata into connection verification.
public enum IOSConnectionGuide: Equatable {
    case phone, personalAudio, homeAudioCandidate, externalAudio, mixed, unavailable

    public var title: String {
        switch self {
        case .phone: return "Audio is still on this phone"
        case .personalAudio: return "This phone reports a wireless or personal-audio route"
        case .homeAudioCandidate: return "This phone reports a TV or home-audio route"
        case .externalAudio: return "This phone reports an external-audio route"
        case .mixed: return "Several output types need confirmation"
        case .unavailable: return "No output type was reported"
        }
    }

    public var nextStep: String {
        switch self {
        case .phone:
            return "Open Control Center, choose your TV or home-audio output, then refresh."
        case .personalAudio:
            return "Confirm the selected name in Control Center. If it is not your TV or home device, choose the correct output."
        case .homeAudioCandidate:
            return "Confirm the same selected name in Control Center and on your TV before continuing."
        case .externalAudio:
            return "Confirm the cable or accessory leads to the intended TV or home-audio device."
        case .mixed:
            return "Open Control Center, confirm the selected output, then refresh this check."
        case .unavailable:
            return "Open Control Center, choose an output, then return and refresh."
        }
    }

    static func from(portTypes: [IOSOutputKind], totalReported: Int) -> Self {
        guard totalReported > 0, !portTypes.isEmpty else { return .unavailable }
        guard totalReported == portTypes.count else { return .mixed }
        let groups = portTypes.map { kind -> IOSConnectionGuide in
            switch kind {
            case .speaker, .receiver: return .phone
            case .headphones, .bluetoothA2DP, .bluetoothHFP, .bluetoothLE: return .personalAudio
            case .airPlay, .hdmi: return .homeAudioCandidate
            case .usb, .lineOut, .car: return .externalAudio
            case .other: return .mixed
            }
        }
        guard let first = groups.first, groups.dropFirst().allSatisfy({ $0 == first }) else { return .mixed }
        return first
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
    public let connectionGuide: IOSConnectionGuide
    public let summary: String
    public let text: String

    private init(buildDetails: String, capturedAtMillis: Int64, portTypes: [IOSOutputKind],
                 totalReported: Int, connectionGuide: IOSConnectionGuide, summary: String, text: String) {
        self.buildDetails = buildDetails; self.capturedAtMillis = capturedAtMillis
        self.portTypes = portTypes; self.totalReported = totalReported
        self.connectionGuide = connectionGuide
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
        let guide = IOSConnectionGuide.from(portTypes: portTypes, totalReported: totalReported)
        let text = ["Audio Bodyguard iPhone output details (v1)", "Captured at (phone clock, UTC): \(clock)",
                    "", buildDetails, "iOS/iPadOS version: \(osVersion)", "",
                    "Source: iOS audio session current-route output port types", summary,
                    "Connection guide: \(guide.title)", "Next check: \(guide.nextStep)",
                    "Connection verification: Not verified", "TV command sent: No",
                    "Port names and identifiers: Not included", "Audio session active: Unknown", "",
                    "This is a session metadata snapshot, not a list of every available device.",
                    "This check does not activate or configure the audio session.",
                    "Actual playback route: Unknown", "Negotiated format: Unknown",
                    "Backend and ownership review: Pending", "Independent capture: Not recorded",
                    "Calibration and clock mapping: Unknown", "Physical output and protection: Not verified",
                    "Outputs may have changed since this snapshot.", "", notice].joined(separator: "\n")
        guard text.utf16.count <= maxUTF16Units, text.utf8.count <= maxUTF8Bytes else { throw OutputDetailsError.oversizedReport }
        return Self(buildDetails: buildDetails, capturedAtMillis: capturedAtMillis, portTypes: portTypes,
                    totalReported: totalReported, connectionGuide: guide, summary: summary, text: text)
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
              }), IOSInstalledBuildLabel.isValid(build)
        else { throw OutputDetailsError.invalidBuild }
    }
}
