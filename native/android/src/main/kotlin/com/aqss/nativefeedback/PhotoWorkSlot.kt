package com.aqss.nativefeedback

/** One process-wide read retains capacity until its own cleanup returns. */
class PhotoWorkSlot {
    class Lease internal constructor()
    class Observation internal constructor(private val detach: () -> Unit) : AutoCloseable {
        override fun close() = detach()
    }
    private var owner: Lease? = null
    private val observers = linkedMapOf<Any, () -> Unit>()
    val occupied: Boolean @Synchronized get() = owner != null
    fun observe(available: () -> Unit): Observation {
        val identity = Any()
        synchronized(this) { observers[identity] = available }
        return Observation { synchronized(this) { observers.remove(identity) }; Unit }
    }
    @Synchronized fun acquire(): Lease? {
        if (owner != null) return null
        return Lease().also { owner = it }
    }
    fun release(lease: Lease): Boolean {
        val callbacks = synchronized(this) {
            if (owner !== lease) return false
            owner = null
            observers.values.toList()
        }
        // Cleanup has returned. View callbacks cannot hold the admission lock.
        for (callback in callbacks) {
            try { callback() } catch (_: Exception) { /* A view cannot undo cleanup. */ }
        }
        return true
    }
    companion object { val process = PhotoWorkSlot() }
}
