import Foundation

/// One process-wide read retains capacity until its own cleanup returns.
public final class PhotoWorkSlot: @unchecked Sendable {
    public struct Lease: Equatable, Sendable { fileprivate let identity = UUID() }
    public final class Observation: @unchecked Sendable {
        private let detach: @Sendable () -> Void
        fileprivate init(_ detach: @escaping @Sendable () -> Void) { self.detach = detach }
        public func close() { detach() }
        deinit { detach() }
    }
    public static let process = PhotoWorkSlot()
    private let lock = NSLock()
    private var owner: Lease?
    private var observers: [UUID: @Sendable () -> Void] = [:]
    public init() {}
    public var occupied: Bool {
        lock.lock(); defer { lock.unlock() }
        return owner != nil
    }
    public func observe(_ available: @escaping @Sendable () -> Void) -> Observation {
        let identity = UUID()
        lock.lock(); observers[identity] = available; lock.unlock()
        return Observation { [weak self] in self?.removeObservation(identity) }
    }
    private func removeObservation(_ identity: UUID) {
        lock.lock(); defer { lock.unlock() }
        observers.removeValue(forKey: identity)
    }
    public func acquire() -> Lease? {
        lock.lock(); defer { lock.unlock() }
        guard owner == nil else { return nil }
        let lease = Lease(); owner = lease; return lease
    }
    @discardableResult public func release(_ lease: Lease) -> Bool {
        lock.lock()
        guard owner == lease else { lock.unlock(); return false }
        owner = nil
        let callbacks = Array(observers.values)
        lock.unlock()
        // A view may query or detach from its callback without deadlocking.
        for callback in callbacks { callback() }
        return true
    }
}
