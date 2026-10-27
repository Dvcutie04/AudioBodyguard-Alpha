import Foundation

public enum TestSetupField: String, CaseIterable, Hashable {
    case playbackPhone = "playback_phone", intendedOutput = "intended_output"
    case observerPhone = "observer_phone", recordingApp = "recording_app"
    case placement, constraints

    public var title: String {
        switch self {
        case .playbackPhone: return "Playback phone"
        case .intendedOutput: return "Intended output"
        case .observerPhone: return "Second phone"
        case .recordingApp: return "Recording app and mode"
        case .placement: return "Phone placement"
        case .constraints: return "Setup constraints"
        }
    }
    public var hint: String {
        switch self {
        case .playbackPhone: return "Model and OS version"
        case .intendedOutput: return "For example: phone speaker. Your plan, not a detected route."
        case .observerPhone: return "Model and OS, or unavailable"
        case .recordingApp: return "App name and the mode you can check"
        case .placement: return "Where each phone would be placed"
        case .constraints: return "Missing equipment or anything you cannot check"
        }
    }
}

public enum TestSetupReportError: Error { case invalidBuild, invalidNotes, invalidClock, oversizedReport }

/// Immutable user notes, never measured output or authorization.
public struct TestSetupReportSnapshot {
    public let text: String
    public static let maxFieldUnits = 160
    public static let maxCharacters = 4 * 1024
    public static let maxUTF8Bytes = 8 * 1024
    public static let notice = "Setup notes only. Nothing is verified."

    public static func limitInput(_ value: String) -> String {
        var prefix = Array(value.utf16.prefix(maxFieldUnits))
        if let last = prefix.last, (0xD800...0xDBFF).contains(last) { prefix.removeLast() }
        return String(decoding: prefix, as: UTF16.self)
    }

    public static func capture(buildDetails: String, notes: [TestSetupField: String], reviewedAtMillis: Int64) throws -> Self {
        guard Array(buildDetails.utf16.prefix(513)).count <= 512 else { throw TestSetupReportError.invalidBuild }
        let lines = buildDetails.components(separatedBy: "\n")
        guard lines.count == 4, lines[0] == "Audio Bodyguard", lines[1] == "Platform: iPhone/iPad",
              lines[2].hasPrefix("Version: "), lines[3].hasPrefix("Build: ") else { throw TestSetupReportError.invalidBuild }
        let version = String(lines[2].dropFirst("Version: ".count))
        let build = String(lines[3].dropFirst("Build: ".count))
        guard (1...96).contains(version.utf16.count), !version.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              try normalized(version) == version else { throw TestSetupReportError.invalidBuild }
        guard build == "Unavailable" || ((1...19).contains(build.utf8.count) && build.utf8.allSatisfy { (48...57).contains($0) }) else {
            throw TestSetupReportError.invalidBuild
        }
        guard (0...253_402_300_799_999).contains(reviewedAtMillis) else { throw TestSetupReportError.invalidClock }
        let utc = ISO8601DateFormatter()
        utc.timeZone = TimeZone(secondsFromGMT: 0)
        utc.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let clock = utc.string(from: Date(timeIntervalSince1970: Double(reviewedAtMillis) / 1000))
        var body = ["Audio Bodyguard test setup (v1)", "Notes reviewed at (phone clock, UTC): " + clock,
                    "", buildDetails, "", "Your notes (not verified)"]
        for field in TestSetupField.allCases {
            let value = try normalized(notes[field] ?? "")
            let quoted = value.isEmpty ? "Unknown" : "\"" + value.replacingOccurrences(of: "\\", with: "\\\\")
                .replacingOccurrences(of: "\"", with: "\\\"") + "\""
            body.append(field.title + ": " + quoted)
        }
        body += ["", "Actual playback route: Unknown", "Negotiated format: Unknown",
                 "Backend and ownership review: Pending", "Independent capture: Not recorded",
                 "Calibration and clock mapping: Unknown", "Playback/capture consent: Not collected",
                 "Physical output and protection: Not verified", "", notice,
                 "This worksheet does not authorize playback or recording."]
        let text = body.joined(separator: "\n")
        guard text.utf16.count <= maxCharacters, text.utf8.count <= maxUTF8Bytes else { throw TestSetupReportError.oversizedReport }
        return Self(text: text)
    }

    private static func normalized(_ value: String) throws -> String {
        let units = Array(value.utf16.prefix(maxFieldUnits + 1))
        guard units.count <= maxFieldUnits else { throw TestSetupReportError.invalidNotes }
        var result = String.UnicodeScalarView()
        for scalar in value.unicodeScalars {
            switch scalar.properties.generalCategory {
            case .control, .format, .lineSeparator, .paragraphSeparator: result.append(" ")
            default: result.append(scalar)
            }
        }
        return String(result).trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
