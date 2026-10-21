import Foundation

/// One selected image owns a 30-second result window. This does not cancel OS work.
public final class PhotoReviewRun {
    public struct Token: Equatable, Sendable { fileprivate let identity = UUID() }
    public enum EndReason { case timeLimit, clockInvalid }
    private let lock = NSLock()
    private let now: () -> Double
    private var owner: Token?
    private var reading = false
    private var failure: EndReason?
    private var startedAt = 0.0
    private var checkedAt = 0.0
    public init(now: @escaping () -> Double) { self.now = now }

    public func select() -> Token {
        lock.lock(); defer { lock.unlock() }
        let token = Token(); owner = token; reading = false; failure = nil; return token
    }
    public func isSelecting(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return owner == token && !reading && failure == nil
    }
    private func eligible(_ token: Token) -> Bool {
        // Check identity before the clock: old callbacks cannot end a replacement.
        guard owner == token, reading else { return false }
        let sample = now()
        if !sample.isFinite || sample < checkedAt { failure = .clockInvalid }
        else if sample - startedAt >= 30 { failure = .timeLimit }
        if failure != nil { reading = false; return false }
        checkedAt = sample; return true
    }
    public func isReading(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return eligible(token)
    }
    public func beginReading(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard owner == token, !reading, failure == nil else { return false }
        let sample = now()
        guard sample.isFinite, sample >= 0 else { failure = .clockInvalid; return false }
        reading = true; startedAt = sample; checkedAt = sample; return true
    }
    public func endReason(_ token: Token) -> EndReason? {
        lock.lock(); defer { lock.unlock() }
        return owner == token ? failure : nil
    }
    public func complete(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        // Publication checks elapsed time even if the UI timer has not run.
        guard eligible(token) else { return false }
        owner = nil; reading = false; return true
    }
    public func cancel(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard owner == token else { return false }
        owner = nil; reading = false; failure = nil; return true
    }
    public func clear() {
        lock.lock(); defer { lock.unlock() }
        owner = nil; reading = false; failure = nil
    }
}
