package com.aqss.nativefeedback

/** A selection owns one import and one OCR result. No device or output authority. */
class PhotoReviewRun(private val nowMs: () -> Long) {
    class Token internal constructor()
    private var owner: Token? = null
    private var reading = false

    @Synchronized fun select(): Token = Token().also { owner = it; reading = false }
    @Synchronized fun isSelecting(token: Token): Boolean = owner === token && !reading
    @Synchronized fun isReading(token: Token): Boolean = owner === token && reading
    @Synchronized fun beginReading(token: Token): Boolean {
        if (owner !== token || reading) return false
        reading = true
        return true
    }
    @Synchronized fun complete(token: Token): Boolean {
        if (owner !== token || !reading) return false
        owner = null; reading = false
        return true
    }
    @Synchronized fun cancel(token: Token): Boolean {
        if (owner !== token) return false
        owner = null; reading = false
        return true
    }
    @Synchronized fun clear() { owner = null; reading = false }
}
