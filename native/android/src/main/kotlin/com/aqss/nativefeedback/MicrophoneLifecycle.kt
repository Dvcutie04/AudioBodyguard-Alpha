package com.aqss.nativefeedback

/** Process-local arbitration of foreground input tools; never output authority. */
class ForegroundMicrophoneGate {
    class Lease internal constructor()
    companion object { val process = ForegroundMicrophoneGate() }
    private var owner: Lease? = null
    @Volatile var blocked = false
        private set

    @Synchronized fun acquire(): Lease? {
        if (owner != null || blocked) return null
        return Lease().also { owner = it }
    }

    /** A missing/stale lease cannot release or quarantine someone else's run. */
    @Synchronized fun release(lease: Lease?, cleanupSucceeded: Boolean): Boolean {
        if (lease == null || owner !== lease || blocked) return false
        if (!cleanupSucceeded) { blocked = true; return false }
        owner = null
        return true
    }
}

/** Main-thread recognition lifetime. OS scheduling is not a physical cutoff bound. */
class VoiceInputRun {
    enum class EndReason { stopped, inactive, permission, clockInvalid, timeLimit }
    var endReason = EndReason.stopped
        private set
    private var active = false
    private var generation = 0L
    private var started = 0L
    private var checked = 0L
    fun start(now: Long): Long? {
        stop()
        if (now < 0 || generation == Long.MAX_VALUE) return null
        generation++; started = now; checked = now; active = true
        return generation
    }
    fun accepts(run: Long, now: Long, foreground: Boolean, permission: Boolean): Boolean {
        if (!active || run != generation) return false
        val reason = when {
            !foreground -> EndReason.inactive
            !permission -> EndReason.permission
            now < checked -> EndReason.clockInvalid
            now - started >= 30_000 -> EndReason.timeLimit
            else -> null
        }
        if (reason != null) { stop(); endReason = reason; return false }
        checked = now
        return true
    }
    fun stop() { active = false; endReason = EndReason.stopped }
}

/** At most 500 Unicode code points / 2,000 UTF-8 bytes, not 500 grapheme clusters. */
fun boundedRecognizedWords(text: String): String {
    var start = text.length
    var count = 0
    while (start > 0 && count < 500) {
        start -= Character.charCount(text.codePointBefore(start)); count++
    }
    return text.substring(start)
}
