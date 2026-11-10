import Foundation

/// Only authored controls inside the owned test player. Not a remote-control API.
public enum OwnedSkipAction: String, Equatable {
    case intro = "SKIP_INTRO"
    case recap = "SKIP_RECAP"
}

public enum OwnedSkipDecision: Equatable {
    case unavailable
    case requested
    case callFailed
}

public struct OwnedSkipSnapshot: Equatable {
    public let playerID: String
    public let playbackSessionID: String
    public let contentID: String
    public let generation: Int
    public let introVisible: Bool
    public let introEnabled: Bool
    public let recapVisible: Bool
    public let recapEnabled: Bool

    public init(playerID: String, playbackSessionID: String, contentID: String,
                generation: Int, introVisible: Bool, introEnabled: Bool,
                recapVisible: Bool, recapEnabled: Bool) {
        self.playerID = playerID; self.playbackSessionID = playbackSessionID
        self.contentID = contentID; self.generation = generation
        self.introVisible = introVisible; self.introEnabled = introEnabled
        self.recapVisible = recapVisible; self.recapEnabled = recapEnabled
    }

    fileprivate var valid: Bool {
        let ids = [playerID, playbackSessionID, contentID]
        return generation >= 0 && ids.allSatisfy { id in
            (1...96).contains(id.utf8.count) && id.utf8.allSatisfy { byte in
                (48...57).contains(byte) || (65...90).contains(byte) ||
                (97...122).contains(byte) || [46, 95, 58, 45].contains(byte)
            }
        }
    }

    fileprivate func offers(_ action: OwnedSkipAction) -> Bool {
        switch action {
        case .intro: return introVisible && introEnabled
        case .recap: return recapVisible && recapEnabled
        }
    }
}

public struct OwnedSkipProposal {
    public let action: OwnedSkipAction
    fileprivate let runID: String
    fileprivate let state: OwnedSkipSnapshot
    fileprivate let nonce: UUID
}

/// Main-actor gate: final recognition proposes; fresh state authorizes one callback.
/// A callback result is REQUESTED, never proof of an external player/TV effect.
@MainActor public final class OwnedVoiceSkipGate {
    public static let grammarVersion = "voice-skip-v1"
    private var runID: String?
    private var lastRunID: String?
    private var selected: OwnedSkipSnapshot?
    private var pending: OwnedSkipProposal?
    private var used = false

    public init() {}

    public static func parse(_ text: String, final: Bool) -> OwnedSkipAction? {
        guard final, (1...96).contains(text.count), text.unicodeScalars.allSatisfy({ (32...126).contains(Int($0.value)) }) else { return nil }
        let normalized = text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard let regex = try? NSRegularExpression(pattern: #"^audio\s+bodyguard\s*,?\s*skip\s+(intro|recap)[.!?]?$"#),
              let match = regex.firstMatch(in: normalized, range: NSRange(normalized.startIndex..., in: normalized)),
              match.range.location == 0, match.range.length == (normalized as NSString).length,
              let range = Range(match.range(at: 1), in: normalized) else { return nil }
        return normalized[range] == "intro" ? .intro : .recap
    }

    public func start(runID: String, player: OwnedSkipSnapshot) -> Bool {
        guard self.runID == nil, runID != lastRunID, (1...96).contains(runID.utf8.count),
              runID.utf8.allSatisfy({ (48...57).contains($0) || (65...90).contains($0) ||
                   (97...122).contains($0) || [46, 95, 58, 45].contains($0) }),
              player.valid else { return false }
        self.runID = runID; lastRunID = runID; selected = player
        used = false; pending = nil
        return true
    }

    public func stop() {
        runID = nil; selected = nil; pending = nil; used = false
    }

    public func propose(_ text: String, final: Bool, runID: String,
                        observed: OwnedSkipSnapshot) -> OwnedSkipProposal? {
        guard self.runID == runID, !used, pending == nil, selected == observed,
              let action = Self.parse(text, final: final), observed.offers(action) else { return nil }
        let proposal = OwnedSkipProposal(action: action, runID: runID, state: observed, nonce: UUID())
        pending = proposal
        return proposal
    }

    public func request(_ proposal: OwnedSkipProposal?, runID: String,
                        observed: OwnedSkipSnapshot, permitted: Bool, foreground: Bool,
                        pressOwnedButton: (OwnedSkipAction) -> Bool) -> OwnedSkipDecision {
        guard let p = proposal, self.runID == runID, !used,
              p.runID == runID, p.nonce == pending?.nonce, selected == observed,
              p.state == observed, observed.offers(p.action) else { return .unavailable }
        // No authorization can be revived without another explicit listening Start.
        guard permitted, foreground else { stop(); return .unavailable }
        used = true; pending = nil
        return pressOwnedButton(p.action) ? .requested : .callFailed
    }
    /// Final recognized text only requests an app-owned callback, never physical verification.
    public func requestFinal(_ text: String?, runID: String, observed: OwnedSkipSnapshot,
                             permitted: Bool, foreground: Bool,
                             pressOwnedButton: (OwnedSkipAction) -> Bool) -> OwnedSkipDecision {
        guard permitted, foreground else { stop(); return .unavailable }
        guard let text = text,
              let proposal = propose(text, final: true, runID: runID, observed: observed) else {
            return .unavailable
        }
        return request(proposal, runID: runID, observed: observed,
                       permitted: permitted, foreground: foreground,
                       pressOwnedButton: pressOwnedButton)
    }

}
