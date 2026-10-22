package com.aqss.nativefeedback

/** One process-wide read retains capacity until its own cleanup returns. */
class PhotoWorkSlot {
    class Lease internal constructor()
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
