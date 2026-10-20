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
