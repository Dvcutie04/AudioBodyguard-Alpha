package com.aqss.nativefeedback

import java.util.UUID

/** Allowlisted input-stop observations, never output or protection evidence. */
enum class SoundCheckEnd(val label: String) {
    STOPPED_BY_USER("Stopped by you"),
    TIME_LIMIT("30-second limit reached"),
    LEFT_SCREEN("Stopped when the app lost focus"),
    HELP_OPENED("Stopped to open help"),
    INPUT_UNAVAILABLE("Input was unavailable or stopped"),
    PERMISSION_CHANGED("Microphone access was unavailable or changed"),
    INPUT_BLOCKED("Input was blocked"),
    ROUTE_CHANGED("Microphone route changed"),
    NO_SAMPLES("No current input samples"),
    INVALID_INPUT("Input format or clock changed"),
    AUDIO_INTERRUPTED("Audio was interrupted"),
    AUDIO_SERVICES_CHANGED("Audio services changed"),
    COULD_NOT_START("Microphone could not start"),
    CLEANUP_FAILED("Input cleanup failed; restart the app before retrying"),
    CLOSED("Sound check closed"),
}

data class SoundCheckRecap(val inputObserved: Boolean, val end: SoundCheckEnd)

/** At most five completed recaps plus one boolean draft, scoped to this process.
 * No samples, levels, words, names, identifiers or timestamps enter completed rows.
 * Clearing this presentation store cannot release microphone or endpoint authority.
 */
class SoundCheckRecaps {
    companion object { val process = SoundCheckRecaps() }
    class Token internal constructor(internal val id: UUID = UUID.randomUUID())
    private var owner: Token? = null
    private var observed = false
    private val completed = ArrayDeque<SoundCheckRecap>()

    @Synchronized fun begin(): Token? {
        if (owner != null) return null
        return Token().also { owner = it; observed = false }
    }

    @Synchronized fun observe(token: Token?): Boolean {
        if (token == null || token !== owner) return false
        observed = true
        return true
    }

    @Synchronized fun finish(token: Token?, end: SoundCheckEnd): Boolean {
        if (token == null || token !== owner) return false
        if (completed.size == 5) completed.removeLast()
        completed.addFirst(SoundCheckRecap(observed, end))
        owner = null; observed = false
        return true
    }

    @Synchronized fun snapshot(): List<SoundCheckRecap> = completed.toList()

    @Synchronized fun clear() {
        completed.clear(); owner = null; observed = false
    }
}
