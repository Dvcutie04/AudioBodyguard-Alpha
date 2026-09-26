import Foundation

// Read-only reference projection. These values cannot attest physical output,
// grant a capability, keep an iOS process alive, or open endpoint handoff.
public enum AQSSSessionState: String, Sendable {
    case active = "ACTIVE"
    case degraded = "DEGRADED"
    case paused = "PAUSED"
    case recoveryRequired = "RECOVERY_REQUIRED"
    case unknownPhysicalState = "UNKNOWN_PHYSICAL_STATE"
}

public struct AQSSCoverageSample: Sendable {
    public let runtimeId: String
    public let clockDomainId: String
    public let receivedMonotonic: Double
    public let expiresMonotonic: Double
    public let state: AQSSSessionState
    public let reason: String
    public let userPaused: Bool

    public init(runtimeId: String, clockDomainId: String, receivedMonotonic: Double,
                expiresMonotonic: Double, state: AQSSSessionState, reason: String,
                userPaused: Bool = false) {
        self.runtimeId = runtimeId
        self.clockDomainId = clockDomainId
        self.receivedMonotonic = receivedMonotonic
        self.expiresMonotonic = expiresMonotonic
        self.state = state
        self.reason = reason
        self.userPaused = userPaused
    }
}

public struct AQSSCoverageView: Equatable, Sendable {
    public let state: AQSSSessionState
    public let reason: String
    public let secondaryReasons: [String]
}

public struct AQSSCapabilityFacts: Sendable {
    public let hardware: Bool?
    public let qualification: Bool?
    public let permission: Bool?
    public let route: Bool?
    public let runtime: Bool?
    public let evidence: Bool?
    public let observedMonotonic: Double
    public let expiresMonotonic: Double
    public let clockDomainId: String

    public init(hardware: Bool?, qualification: Bool?, permission: Bool?,
                route: Bool?, runtime: Bool?, evidence: Bool?,
                observedMonotonic: Double, expiresMonotonic: Double,
                clockDomainId: String) {
        self.hardware = hardware
        self.qualification = qualification
        self.permission = permission
        self.route = route
        self.runtime = runtime
        self.evidence = evidence
        self.observedMonotonic = observedMonotonic
        self.expiresMonotonic = expiresMonotonic
        self.clockDomainId = clockDomainId
    }
}

public struct AQSSCapabilityView: Equatable, Sendable {
    public let label: String
    public let reasons: [String]
    public let canActuate = false
}

public enum AQSSSessionEvidenceView {
    private static let safeReasons: Set<String> = [
        "AUTHORITY_INVALID", "CONNECTIVITY_UNAVAILABLE", "FRESH_VALIDATION_REQUIRED",
        "FUTURE_EVIDENCE", "FUTURE_MONOTONIC_EVIDENCE", "MONOTONIC_BASELINE_REQUIRED",
        "NON_MONOTONIC_CLOCK", "NON_MONOTONIC_EVIDENCE", "NOT_VALIDATED",
        "PERMISSION_DENIED", "PROTECTION_PATH_INELIGIBLE", "RUNTIME_INELIGIBLE",
        "SENSOR_UNAVAILABLE", "STALE_EVIDENCE", "VALIDATED", "USER_PAUSED",
        "PATH_ELIGIBLE", "POST_CONDITION_UNOBSERVED", "REFERENCE_ONLY",
    ]

    private static func identity(_ value: String) -> Bool {
        !value.isEmpty && value == value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func validTime(_ value: Double) -> Bool {
        value.isFinite && value >= 0
    }

    public static func coverage(_ sample: AQSSCoverageSample?, runtimeId: String,
                                clockDomainId: String, nowMonotonic: Double) -> AQSSCoverageView {
        let unknown = AQSSSessionState.unknownPhysicalState
        guard identity(runtimeId), identity(clockDomainId), validTime(nowMonotonic) else {
            return AQSSCoverageView(state: unknown, reason: "INVALID_CURRENT_CONTEXT", secondaryReasons: [])
        }
        guard let sample = sample else {
            return AQSSCoverageView(state: unknown, reason: "NO_OBSERVATION", secondaryReasons: [])
        }
        guard identity(sample.runtimeId), identity(sample.clockDomainId),
              identity(sample.reason), validTime(sample.receivedMonotonic),
              validTime(sample.expiresMonotonic),
              sample.expiresMonotonic >= sample.receivedMonotonic,
              (!sample.userPaused || sample.state == .paused) else {
            return AQSSCoverageView(state: unknown, reason: "INVALID_REPORTED_EVIDENCE", secondaryReasons: [])
        }
        let reason = safeReasons.contains(sample.reason) ? sample.reason : "OTHER_REASON"
        guard sample.runtimeId == runtimeId, sample.clockDomainId == clockDomainId,
              nowMonotonic >= sample.receivedMonotonic else {
            return AQSSCoverageView(state: unknown, reason: "RUNTIME_OR_CLOCK_CHANGED", secondaryReasons: [reason])
        }
        if nowMonotonic > sample.expiresMonotonic {
            if sample.userPaused {
                return AQSSCoverageView(state: .paused, reason: reason, secondaryReasons: ["EVIDENCE_EXPIRED"])
            }
            return AQSSCoverageView(state: unknown, reason: "EVIDENCE_EXPIRED", secondaryReasons: [reason])
        }
        return AQSSCoverageView(state: sample.state, reason: reason, secondaryReasons: [])
    }

    public static func capability(_ facts: AQSSCapabilityFacts, clockDomainId: String,
                                  nowMonotonic: Double) -> AQSSCapabilityView {
        guard identity(clockDomainId), identity(facts.clockDomainId), validTime(nowMonotonic),
              validTime(facts.observedMonotonic), validTime(facts.expiresMonotonic),
              facts.expiresMonotonic >= facts.observedMonotonic else {
            return AQSSCapabilityView(label: "UNKNOWN", reasons: ["INVALID_REPORTED_EVIDENCE"])
        }
        guard clockDomainId == facts.clockDomainId,
              nowMonotonic >= facts.observedMonotonic,
              nowMonotonic <= facts.expiresMonotonic else {
            return AQSSCapabilityView(label: "UNKNOWN", reasons: ["EVIDENCE_EXPIRED_OR_RUNTIME_CHANGED"])
        }
        let checks: [(Bool?, String, String)] = [
            (facts.hardware, "UNSUPPORTED", "HARDWARE_UNKNOWN"),
            (facts.qualification, "NOT_QUALIFIED", "QUALIFICATION_UNKNOWN"),
            (facts.permission, "PERMISSION_DENIED", "PERMISSION_UNKNOWN"),
            (facts.route, "ROUTE_UNAVAILABLE", "ROUTE_UNKNOWN"),
            (facts.runtime, "RUNTIME_INELIGIBLE", "RUNTIME_UNKNOWN"),
            (facts.evidence, "OBSERVATION_UNAVAILABLE", "EVIDENCE_UNKNOWN"),
        ]
        let blocked = checks.compactMap { $0.0 == false ? $0.1 : nil }
        if !blocked.isEmpty { return AQSSCapabilityView(label: "BLOCKED", reasons: blocked) }
        let missing = checks.compactMap { $0.0 == nil ? $0.2 : nil }
        if !missing.isEmpty { return AQSSCapabilityView(label: "UNKNOWN", reasons: missing) }
        return AQSSCapabilityView(label: "AVAILABLE_FOR_REVIEW", reasons: [])
    }
}
