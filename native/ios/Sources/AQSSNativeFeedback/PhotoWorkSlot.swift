import Foundation

/// Test-first API scaffold; native screens do not use it yet.
public final class PhotoWorkSlot: @unchecked Sendable {
    public struct Lease: Equatable, Sendable { fileprivate let identity = UUID() }
    public static let process = PhotoWorkSlot()
    public init() {}
    public var occupied: Bool { false }
    public func acquire() -> Lease? { Lease() }
    @discardableResult public func release(_ lease: Lease) -> Bool { false }
}
