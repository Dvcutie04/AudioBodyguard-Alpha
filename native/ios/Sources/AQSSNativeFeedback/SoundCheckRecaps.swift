import Foundation

/// Allowlisted input-stop observations, never output or protection evidence.
public enum SoundCheckEnd: String, CaseIterable {
    case stoppedByUser = "Stopped by you"
    case timeLimit = "30-second limit reached"
    case leftScreen = "Stopped when the app lost focus"
    case helpOpened = "Stopped to open help"
    case inputUnavailable = "Input was unavailable or stopped"
    case permissionChanged = "Microphone access was unavailable or changed"
    case inputBlocked = "Input was blocked"
    case routeChanged = "Microphone route changed"
    case noSamples = "No current input samples"
    case invalidInput = "Input format or clock changed"
    case audioInterrupted = "Audio was interrupted"
    case audioServicesChanged = "Audio services changed"
    case couldNotStart = "Microphone could not start"
    case cleanupFailed = "Input cleanup failed; restart the app before retrying"
    case closed = "Sound check closed"
}

public struct SoundCheckRecap: Equatable {
    public let inputObserved: Bool
    public let end: SoundCheckEnd
}

/// Five completed recaps plus one boolean draft in this process. No samples,
/// levels, words, names, identifiers or timestamps enter completed rows.
/// This presentation store has no microphone-release or endpoint authority.
@MainActor
public final class SoundCheckRecaps {
    public static let shared = SoundCheckRecaps()
    public struct Token: Equatable { fileprivate let id = UUID() }
    private var owner: Token?
    private var observed = false
    private var completed: [SoundCheckRecap] = []
    public init() {}

    public func begin() -> Token? {
        guard owner == nil else { return nil }
        let token = Token(); owner = token; observed = false
        return token
    }
    @discardableResult public func observe(_ token: Token?) -> Bool {
        guard let token = token, token == owner else { return false }
        observed = true; return true
    }
    @discardableResult public func finish(_ token: Token?, end: SoundCheckEnd) -> Bool {
        guard let token = token, token == owner else { return false }
        if completed.count == 5 { completed.removeLast() }
        completed.insert(SoundCheckRecap(inputObserved: observed, end: end), at: 0)
        owner = nil; observed = false
        return true
    }
    public func snapshot() -> [SoundCheckRecap] { completed }
    public func clear() { completed = []; owner = nil; observed = false }
}

/// Two immutable views of one reviewed snapshot; selection never edits recaps.
public struct PrivateSupportReportSnapshot {
    private let buildOnly: String
    private let withChecks: String
    public init(buildDetails: String, recaps: [SoundCheckRecap]) {
        buildOnly = buildDetails
        withChecks = buildDetails + "\n\n" + soundCheckSupportReportSection(recaps)
    }
    public func text(includeRecentChecks: Bool) -> String {
        includeRecentChecks ? withChecks : buildOnly
    }
}

/// An allowlisted, bounded text snapshot. Never a raw log or physical evidence.
public func soundCheckSupportReportSection(_ recaps: [SoundCheckRecap]) -> String {
    var lines = ["Recent sound checks (this app session)"]
    if recaps.isEmpty { lines.append("No completed sound checks in this app session.") }
    for (index, row) in recaps.prefix(5).enumerated() {
        if index > 0 { lines.append("") }
        lines.append("Check \(index + 1): \(row.inputObserved ? "Input samples observed" : "No input samples observed")")
        lines.append(row.end.rawValue)
    }
    return lines.joined(separator: "\n") + "\n\nInput observations only; not proof of sound safety, protection or TV control."
}
