package com.aqss.nativefeedback

/** One selected image owns a 30-second result window. This does not cancel OS work. */
class PhotoReviewRun(private val nowMs: () -> Long) {
    class Token internal constructor()
    enum class EndReason { timeLimit, clockInvalid }
    private var owner: Token? = null
    private var reading = false
    private var failure: EndReason? = null
    private var startedAt = 0L
    private var checkedAt = 0L

    @Synchronized fun select(): Token = Token().also { owner = it; reading = false; failure = null }
    @Synchronized fun isSelecting(token: Token): Boolean = owner === token && !reading && failure == null
    @Synchronized fun isReading(token: Token): Boolean {
        // An obsolete callback cannot sample the clock or close a newer review.
        if (owner !== token || !reading) return false
        val now = nowMs()
        failure = when {
            now < checkedAt -> EndReason.clockInvalid
            now - startedAt >= 30_000 -> EndReason.timeLimit
            else -> null
        }
        if (failure != null) { reading = false; return false }
        checkedAt = now
        return true
    }
    @Synchronized fun beginReading(token: Token): Boolean {
        if (!isSelecting(token)) return false
        val now = nowMs()
        if (now < 0) { failure = EndReason.clockInvalid; return false }
        reading = true; startedAt = now; checkedAt = now
        return true
    }
    @Synchronized fun endReason(token: Token): EndReason? = if (owner === token) failure else null
    @Synchronized fun complete(token: Token): Boolean {
        // Publication checks elapsed time even if the UI timer has not run.
        if (!isReading(token)) return false
        owner = null; reading = false
        return true
    }
    @Synchronized fun cancel(token: Token): Boolean {
        if (owner !== token) return false
        clear(); return true
    }
    @Synchronized fun clear() { owner = null; reading = false; failure = null }
}
