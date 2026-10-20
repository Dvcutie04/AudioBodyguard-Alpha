package com.aqss.nativefeedback

import java.util.concurrent.CountDownLatch
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread
import kotlin.test.*

class MicrophoneLifecycleTest {
    @Test fun voiceAndMeterShareOneReservation() {
        val gate = ForegroundMicrophoneGate()
        val voice = assertNotNull(gate.acquire())
        assertNull(gate.acquire())
        assertTrue(gate.release(voice, cleanupSucceeded = true))
        assertNotNull(gate.acquire())
    }

    @Test fun missingAndStaleOwnersCannotReleaseAnotherRun() {
        val gate = ForegroundMicrophoneGate()
        val old = assertNotNull(gate.acquire())
        assertTrue(gate.release(old, true))
        val current = assertNotNull(gate.acquire())
        assertFalse(gate.release(null, false))
        assertFalse(gate.release(old, true))
        assertFalse(gate.blocked)
        assertNull(gate.acquire())
        assertTrue(gate.release(current, true))
    }

    @Test fun unresolvedCleanupBlocksBothToolsAndSurvivesRetry() {
        val gate = ForegroundMicrophoneGate()
        val owner = assertNotNull(gate.acquire())
        assertFalse(gate.release(owner, false))
        assertTrue(gate.blocked)
        assertNull(gate.acquire())
        assertFalse(gate.release(owner, true))
        assertNull(gate.acquire())
    }

    @Test fun simultaneousStartsStillHaveExactlyOneOwner() {
        val gate = ForegroundMicrophoneGate()
        val ready = CountDownLatch(2)
        val start = CountDownLatch(1)
        val winners = AtomicInteger()
        val callers = (1..2).map {
            thread {
                ready.countDown(); start.await()
                if (gate.acquire() != null) winners.incrementAndGet()
            }
        }
        ready.await(); start.countDown(); callers.forEach { it.join() }
        assertEquals(1, winners.get())
    }

    @Test fun oldSpeechCallbacksCannotReopenOrStopANewRun() {
        val run = VoiceInputRun()
        val old = assertNotNull(run.start(1000))
        run.stop()
        assertFalse(run.accepts(old, 1100, true, true))
        val current = assertNotNull(run.start(1200))
        assertFalse(run.accepts(old, 1300, true, true))
        assertTrue(run.accepts(current, 1300, true, true))
    }

    @Test fun voiceStopsAtTheElapsedTimeLimitWithoutAnotherCallback() {
        val run = VoiceInputRun()
        val token = assertNotNull(run.start(1000))
        assertTrue(run.accepts(token, 30999, true, true))
        assertFalse(run.accepts(token, 31000, true, true))
        assertEquals(VoiceInputRun.EndReason.timeLimit, run.endReason)
        assertFalse(run.accepts(token, 31001, true, true))
    }

    @Test fun inactivityAndPermissionLossLatchVoiceOff() {
        for (foreground in listOf(false, true)) {
            val run = VoiceInputRun()
            val token = assertNotNull(run.start(1000))
            assertFalse(run.accepts(token, 1100, foreground, !foreground))
            assertEquals(if (foreground) VoiceInputRun.EndReason.permission else VoiceInputRun.EndReason.inactive, run.endReason)
            assertFalse(run.accepts(token, 1200, true, true))
        }
    }

    @Test fun invalidClockAndRollbackLatchVoiceOff() {
        val run = VoiceInputRun()
        assertNull(run.start(-1))
        val token = assertNotNull(run.start(1000))
        assertTrue(run.accepts(token, 1200, true, true))
        assertFalse(run.accepts(token, 1199, true, true))
        assertEquals(VoiceInputRun.EndReason.clockInvalid, run.endReason)
        assertFalse(run.accepts(token, 1300, true, true))
    }

    @Test fun recognizedTextIsBoundedWithoutSplittingSurrogatePairs() {
        assertEquals("ordinary words", boundedRecognizedWords("ordinary words"))
        for (text in listOf("🦋".repeat(2000), "a" + "\u0301".repeat(10000))) {
            val words = boundedRecognizedWords(text)
            assertEquals(500, words.codePointCount(0, words.length))
            assertTrue(words.toByteArray(Charsets.UTF_8).size <= 2000)
            assertFalse(Character.isLowSurrogate(words.first()))
        }
    }
}
