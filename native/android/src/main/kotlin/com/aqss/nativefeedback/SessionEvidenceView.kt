package com.aqss.nativefeedback

// Read-only reference projection. No endpoint authority, OS lifecycle, output
// verification or handoff readiness is conferred by constructing these values.
enum class SessionState {
    ACTIVE, DEGRADED, PAUSED, RECOVERY_REQUIRED, UNKNOWN_PHYSICAL_STATE
}

data class CoverageSample(
    val runtimeId: String,
    val clockDomainId: String,
    val receivedMonotonic: Double,
    val expiresMonotonic: Double,
    val state: SessionState,
    val reason: String,
    val userPaused: Boolean = false,
)

data class CoverageView(
    val state: SessionState,
    val reason: String,
    val secondaryReasons: List<String> = emptyList(),
)

data class CapabilityFacts(
    val hardware: Boolean?,
    val qualification: Boolean?,
    val permission: Boolean?,
    val route: Boolean?,
    val runtime: Boolean?,
    val evidence: Boolean?,
    val observedMonotonic: Double,
    val expiresMonotonic: Double,
    val clockDomainId: String,
)

data class CapabilityView(
    val label: String,
    val reasons: List<String>,
    val canActuate: Boolean = false,
) {
    init {
        require(!canActuate) { "A read-only capability projection cannot authorize actuation" }
    }
}

object SessionEvidenceView {
    private val safeReasons = setOf(
        "AUTHORITY_INVALID", "CONNECTIVITY_UNAVAILABLE", "FRESH_VALIDATION_REQUIRED",
        "FUTURE_EVIDENCE", "FUTURE_MONOTONIC_EVIDENCE", "MONOTONIC_BASELINE_REQUIRED",
        "NON_MONOTONIC_CLOCK", "NON_MONOTONIC_EVIDENCE", "NOT_VALIDATED",
        "PERMISSION_DENIED", "PROTECTION_PATH_INELIGIBLE", "RUNTIME_INELIGIBLE",
        "SENSOR_UNAVAILABLE", "STALE_EVIDENCE", "VALIDATED", "USER_PAUSED",
        "PATH_ELIGIBLE", "POST_CONDITION_UNOBSERVED", "REFERENCE_ONLY",
    )

    private fun identity(value: String): Boolean = value.isNotEmpty() && value == value.trim()
    private fun validTime(value: Double): Boolean = value.isFinite() && value >= 0.0

    fun coverage(sample: CoverageSample?, runtimeId: String,
                 clockDomainId: String, nowMonotonic: Double): CoverageView {
        val unknown = SessionState.UNKNOWN_PHYSICAL_STATE
        if (!identity(runtimeId) || !identity(clockDomainId) || !validTime(nowMonotonic)) {
            return CoverageView(unknown, "INVALID_CURRENT_CONTEXT")
        }
        if (sample == null) return CoverageView(unknown, "NO_OBSERVATION")
        if (!identity(sample.runtimeId) || !identity(sample.clockDomainId) ||
            !identity(sample.reason) || !validTime(sample.receivedMonotonic) ||
            !validTime(sample.expiresMonotonic) || sample.expiresMonotonic < sample.receivedMonotonic ||
            (sample.userPaused && sample.state != SessionState.PAUSED)
        ) return CoverageView(unknown, "INVALID_REPORTED_EVIDENCE")
        val reason = if (sample.reason in safeReasons) sample.reason else "OTHER_REASON"
        if (sample.runtimeId != runtimeId || sample.clockDomainId != clockDomainId ||
            nowMonotonic < sample.receivedMonotonic
        ) return CoverageView(unknown, "RUNTIME_OR_CLOCK_CHANGED", listOf(reason))
        if (nowMonotonic > sample.expiresMonotonic) {
            if (sample.userPaused) {
                return CoverageView(SessionState.PAUSED, reason, listOf("EVIDENCE_EXPIRED"))
            }
            return CoverageView(unknown, "EVIDENCE_EXPIRED", listOf(reason))
        }
        return CoverageView(sample.state, reason)
    }

    fun capability(facts: CapabilityFacts, clockDomainId: String,
                   nowMonotonic: Double): CapabilityView {
        if (!identity(clockDomainId) || !identity(facts.clockDomainId) ||
            !validTime(nowMonotonic) || !validTime(facts.observedMonotonic) ||
            !validTime(facts.expiresMonotonic) || facts.expiresMonotonic < facts.observedMonotonic
        ) return CapabilityView("UNKNOWN", listOf("INVALID_REPORTED_EVIDENCE"))
        if (clockDomainId != facts.clockDomainId ||
            nowMonotonic < facts.observedMonotonic || nowMonotonic > facts.expiresMonotonic
        ) return CapabilityView("UNKNOWN", listOf("EVIDENCE_EXPIRED_OR_RUNTIME_CHANGED"))
        val checks = listOf(
            Triple(facts.hardware, "UNSUPPORTED", "HARDWARE_UNKNOWN"),
            Triple(facts.qualification, "NOT_QUALIFIED", "QUALIFICATION_UNKNOWN"),
            Triple(facts.permission, "PERMISSION_DENIED", "PERMISSION_UNKNOWN"),
            Triple(facts.route, "ROUTE_UNAVAILABLE", "ROUTE_UNKNOWN"),
            Triple(facts.runtime, "RUNTIME_INELIGIBLE", "RUNTIME_UNKNOWN"),
            Triple(facts.evidence, "OBSERVATION_UNAVAILABLE", "EVIDENCE_UNKNOWN"),
        )
        val blocked = checks.filter { it.first == false }.map { it.second }
        if (blocked.isNotEmpty()) return CapabilityView("BLOCKED", blocked)
        val missing = checks.filter { it.first == null }.map { it.third }
        if (missing.isNotEmpty()) return CapabilityView("UNKNOWN", missing)
        return CapabilityView("AVAILABLE_FOR_REVIEW", emptyList())
    }
}
