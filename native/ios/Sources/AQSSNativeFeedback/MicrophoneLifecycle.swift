import Foundation

/// Process-local arbitration for the two foreground input tools, not output authority.
/// All session configuration and teardown must pass through the current lease.
@MainActor
public final class ForegroundMicrophoneGate {
    public struct Lease: Equatable { fileprivate let identity = UUID() }
    public enum Rejection: Error { case notOwner }
    public static let shared = ForegroundMicrophoneGate()
    public private(set) var blocked = false
    public var available: Bool { owner == nil && !blocked }
    private var owner: Lease?
    private var deactivationRequired = false
    public init() {}

    public func acquire() -> Lease? {
        guard available else { return nil }
        let lease = Lease(); owner = lease
        return lease
    }

    public func activate(_ lease: Lease, using configure: () throws -> Void) throws {
        guard owner == lease, !deactivationRequired, !blocked else { throw Rejection.notOwner }
        // Configuration can change the app-wide session before throwing.
        // Retain cleanup responsibility from entry, not only successful return.
        deactivationRequired = true
        try configure()
    }

    /// A missing, stale or foreign lease must never call the global session API.
    /// Failed deactivation quarantines this process until the app exits.
    @discardableResult
    public func release(_ lease: Lease?, using deactivate: () throws -> Void) -> Bool {
        guard let lease = lease, owner == lease, !blocked else { return false }
        if deactivationRequired {
            do { try deactivate() }
            catch { blocked = true; return false }
        }
        deactivationRequired = false; owner = nil
        return true
    }
}

/// One latest text update per recognition run; no queue of main-thread closures.
/// Recognition callbacks are not the real-time audio callback and may take this lock.
public final class VoiceResultMailbox {
    public struct Update {
        public let text: String?
        public let final: Bool
        public let failed: Bool
    }
    private let lock = NSLock()
    private var closed = false, terminal = false
    private var latest: Update?
    public init() {}

    public func publish(text: String?, final: Bool, failed: Bool) {
        // At most 500 Unicode scalars / 2,000 UTF-8 bytes, even for one large grapheme.
        let words = text.map { String(String.UnicodeScalarView($0.unicodeScalars.suffix(500))) }
        lock.lock(); defer { lock.unlock() }
        guard !closed, !terminal else { return }
        latest = Update(text: words ?? latest?.text, final: final, failed: failed)
        terminal = final || failed
    }
    public func take() -> Update? {
        lock.lock(); defer { lock.unlock() }
        let update = latest; latest = nil; return update
    }
    public func close() {
        lock.lock(); defer { lock.unlock() }
        closed = true; latest = nil
    }
}
