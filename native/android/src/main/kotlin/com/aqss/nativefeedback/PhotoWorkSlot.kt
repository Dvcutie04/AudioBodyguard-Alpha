package com.aqss.nativefeedback

/** One process-wide read retains capacity until its own cleanup returns. */
class PhotoWorkSlot {
    class Lease internal constructor()
    class Observation internal constructor(private val detach: () -> Unit) : AutoCloseable {
        override fun close() = detach()
    }
    // Test-first notification scaffold; admission and cleanup policy are unchanged.
    fun observe(available: () -> Unit): Observation = Observation {}
    private var owner: Lease? = null
    val occupied: Boolean @Synchronized get() = owner != null
    @Synchronized fun acquire(): Lease? {
        if (owner != null) return null
        return Lease().also { owner = it }
    }
    @Synchronized fun release(lease: Lease): Boolean {
        if (owner !== lease) return false
        owner = null
        return true
    }
    companion object { val process = PhotoWorkSlot() }
}
