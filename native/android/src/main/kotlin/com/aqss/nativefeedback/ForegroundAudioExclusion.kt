package com.aqss.nativefeedback

/** Process-local resource exclusion only; never output/protection authority. */
class ForegroundAudioExclusion {
    enum class Tool { INPUT, OUTPUT }
    enum class State { AVAILABLE, OCCUPIED, BLOCKED }
    class Lease internal constructor(val tool: Tool, private val retainedOwner: Any)
    companion object { val process = ForegroundAudioExclusion() }
    private var owner: Lease? = null
    @Volatile var blocked = false
        private set

    /** An observation, never a reservation. Only acquire/release change ownership. */
    val state: State
        @Synchronized get() = when {
            blocked -> State.BLOCKED
            owner != null -> State.OCCUPIED
            else -> State.AVAILABLE
        }

    @Synchronized fun acquire(tool: Tool, retainedOwner: Any): Lease? {
        if (blocked || owner != null) return null
        return Lease(tool, retainedOwner).also { owner = it }
    }

    @Synchronized fun release(lease: Lease?, cleanupSucceeded: Boolean): Boolean {
        if (lease == null || owner !== lease || blocked) return false
        if (!cleanupSucceeded) { blocked = true; return false }
        owner = null
        return true
    }
}
