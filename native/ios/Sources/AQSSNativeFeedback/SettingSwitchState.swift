/// Local switch presentation only. No setting tap creates connection evidence,
/// saves a device preference, or dispatches an audio command.
public struct AQSSSettingSwitchState: Equatable, Sendable {
    public private(set) var enabled: Set<String> = []
    public private(set) var attempts: [String: Double] = [:]
    private let allowed = Set(AQSSInterfaceContent.settings.map(\.id))
    public init() {}

    public var nextExpiry: Double? { attempts.values.min() }
    public func isOn(_ id: String) -> Bool { enabled.contains(id) || attempts[id] != nil }
    public func isAttempting(_ id: String) -> Bool { attempts[id] != nil }

    public mutating func press(_ id: String, connectionVerified: Bool, now: Double) {
        guard allowed.contains(id), now.isFinite, now >= 0 else { return }
        expire(now: now)
        if connectionVerified {
            attempts.removeValue(forKey: id)
            if !enabled.insert(id).inserted { enabled.remove(id) }
            else if id == "dialogue" { enabled.remove("night") }
            else if id == "night" { enabled.remove("dialogue") }
        } else {
            enabled.removeAll()
            // Repeated taps cannot restart or extend the two-second prompt.
            if attempts[id] == nil { attempts[id] = now + 2 }
        }
    }

    public mutating func expire(now: Double) {
        guard now.isFinite, now >= 0 else { reset(); return }
        attempts = attempts.filter { $0.value > now }
    }

    public mutating func connectionLost() { reset() }
    public mutating func reset() { enabled.removeAll(); attempts.removeAll() }
}
