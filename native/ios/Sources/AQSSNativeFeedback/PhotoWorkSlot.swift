import Foundation

/// One process-wide read retains capacity until its own cleanup returns.
public final class PhotoWorkSlot: @unchecked Sendable {
    public struct Lease: Equatable, Sendable { fileprivate let identity = UUID() }
    public static let process = PhotoWorkSlot()
    private let lock = NSLock()
    private var owner: Lease?
    public init() {}
    public var occupied: Bool {
        lock.lock(); defer { lock.unlock() }
        return owner != nil
    }
    public func acquire() -> Lease? {
        lock.lock(); defer { lock.unlock() }
        guard owner == nil else { return nil }
        let lease = Lease(); owner = lease; return lease
    }
    @discardableResult public func release(_ lease: Lease) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard owner == lease else { return false }
        owner = nil; return true
    }
}
