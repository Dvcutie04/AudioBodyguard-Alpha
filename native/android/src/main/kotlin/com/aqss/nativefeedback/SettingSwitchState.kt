package com.aqss.nativefeedback

/** Local switch presentation, never connection evidence, persistence or dispatch. */
class SettingSwitchState {
    private val allowed = InterfaceContent.settings.map { it.id }.toSet()
    private val enabled = mutableSetOf<String>()
    private val attempts = mutableMapOf<String, Double>()
    val nextExpiry: Double? get() = attempts.values.minOrNull()
    fun isOn(id: String) = id in enabled || id in attempts
    fun isAttempting(id: String) = id in attempts

    fun press(id: String, connectionVerified: Boolean, now: Double) {
        if (id !in allowed || !now.isFinite() || now < 0) return
        expire(now)
        if (connectionVerified) {
            attempts.remove(id)
            if (!enabled.add(id)) enabled.remove(id)
            else if (id == "dialogue") enabled.remove("night")
            else if (id == "night") enabled.remove("dialogue")
        } else {
            enabled.clear()
            // Repeated taps do not restart or extend the two-second prompt.
            if (id !in attempts) attempts[id] = now + 2
        }
    }

    fun expire(now: Double) {
        if (!now.isFinite() || now < 0) { reset(); return }
        attempts.entries.removeAll { it.value <= now }
    }
    fun connectionLost() = reset()
    fun reset() { enabled.clear(); attempts.clear() }
}
