package com.aqss.nativefeedback

import kotlin.test.*
import org.junit.Test

/** Availability is an observation; acquire/release remain the resource authority. */
class AudioAvailabilityTest {
    @Test fun observingAvailabilityCannotReserveOrReleaseAnOwner() {
        val gate = ForegroundAudioExclusion()
        repeat(20) { assertEquals(ForegroundAudioExclusion.State.AVAILABLE, gate.state) }
        val owner = assertNotNull(gate.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        repeat(20) { assertEquals(ForegroundAudioExclusion.State.OCCUPIED, gate.state) }
        assertNull(gate.acquire(ForegroundAudioExclusion.Tool.INPUT, Any()))
        assertTrue(gate.release(owner, true))
        assertEquals(ForegroundAudioExclusion.State.AVAILABLE, gate.state)
    }

    @Test fun inputAndOutputObserveTheSameOwnershipWithoutAnOptimisticReservation() {
        val shared = ForegroundAudioExclusion()
        val input = ForegroundMicrophoneGate(shared)
        assertEquals(ForegroundAudioExclusion.State.AVAILABLE, shared.state)
        // An AVAILABLE observation is not a reservation: another tool may win.
        val output = assertNotNull(shared.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        assertNull(input.acquire())
        assertEquals(ForegroundAudioExclusion.State.OCCUPIED, shared.state)
        assertTrue(shared.release(output, true))
        val microphone = assertNotNull(input.acquire())
        assertEquals(ForegroundAudioExclusion.State.OCCUPIED, shared.state)
        assertNull(shared.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        assertTrue(input.release(microphone, true))
        assertEquals(ForegroundAudioExclusion.State.AVAILABLE, shared.state)
    }

    @Test fun staleOrForeignCleanupCannotChangeTheObservedCurrentState() {
        val gate = ForegroundAudioExclusion()
        val old = assertNotNull(gate.acquire(ForegroundAudioExclusion.Tool.INPUT, Any()))
        assertTrue(gate.release(old, true))
        val owner = assertNotNull(gate.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        val foreignGate = ForegroundAudioExclusion()
        val foreign = assertNotNull(foreignGate.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        for (lease in listOf(null, old, foreign)) for (cleaned in listOf(false, true)) {
            assertFalse(gate.release(lease, cleaned))
            assertEquals(ForegroundAudioExclusion.State.OCCUPIED, gate.state)
            assertFalse(gate.blocked)
        }
        assertTrue(gate.release(owner, true))
        assertEquals(ForegroundAudioExclusion.State.AVAILABLE, gate.state)
    }

    @Test fun unresolvedCleanupStaysBlockedAcrossObservationsAndLaterSuccessfulReleaseClaims() {
        for (tool in ForegroundAudioExclusion.Tool.entries) {
            val gate = ForegroundAudioExclusion()
            val owner = assertNotNull(gate.acquire(tool, Any()))
            assertFalse(gate.release(owner, false))
            repeat(20) {
                assertEquals(ForegroundAudioExclusion.State.BLOCKED, gate.state)
                assertTrue(gate.blocked)
                assertFalse(gate.release(owner, true))
                assertNull(gate.acquire(ForegroundAudioExclusion.Tool.INPUT, Any()))
                assertNull(gate.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
            }
        }
    }
}
