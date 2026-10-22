package com.aqss.nativefeedback

/** Test-first API scaffold; native screens do not use it yet. */
class PhotoWorkSlot {
    class Lease internal constructor()
    val occupied: Boolean get() = false
    fun acquire(): Lease? = Lease()
    fun release(lease: Lease): Boolean = false
    companion object { val process = PhotoWorkSlot() }
}
