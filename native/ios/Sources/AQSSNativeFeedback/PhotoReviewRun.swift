import Foundation

/// A selection owns one import and one OCR result, never device or output authority.
public final class PhotoReviewRun {
    public struct Token: Equatable { fileprivate let identity = UUID() }
    private let lock = NSLock()
    private var owner: Token?
    private var reading = false
    public init() {}

    public func select() -> Token {
        lock.lock(); defer { lock.unlock() }
        let token = Token(); owner = token; reading = false; return token
    }
    public func isSelecting(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return owner == token && !reading
    }
    public func isReading(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return owner == token && reading
    }
    public func beginReading(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard owner == token, !reading else { return false }
        reading = true; return true
    }
    public func complete(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard owner == token, reading else { return false }
        owner = nil; reading = false; return true
    }
    public func cancel(_ token: Token) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard owner == token else { return false }
        owner = nil; reading = false; return true
    }
    public func clear() {
        lock.lock(); defer { lock.unlock() }
        owner = nil; reading = false
    }
}
