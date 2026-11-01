package com.aqss.nativefeedback

import kotlin.test.*

class PcmInputLevelTest {
    @Test fun zeroSamplesDoNotClaimAcousticSilence() {
        val level = PcmInputLevel.measure(ShortArray(1600), 1600)
        assertNull(level.rmsDbfs)
        assertEquals(0.0, level.peakFraction)
        assertEquals(0, level.fullScaleSamples)
    }

    @Test fun digitalAmplitudeUsesSigned16FullScaleAndOnlyTheReadPrefix() {
        val level = PcmInputLevel.measure(shortArrayOf(16384, -16384, 32767), 2)
        assertEquals(-6.020599913, level.rmsDbfs!!, 0.000001)
        assertEquals(0.5, level.peakFraction)
        assertEquals(0, level.fullScaleSamples)
        assertEquals(2, level.sampleCount)
    }

    @Test fun mostNegativeSampleDoesNotOverflowAndFullScaleIsCounted() {
        val level = PcmInputLevel.measure(shortArrayOf(-32768, 32767), 2)
        assertEquals(1.0, level.peakFraction)
        assertEquals(2, level.fullScaleSamples)
        assertTrue(level.rmsDbfs!! <= 0.0)
        assertFailsWith<IllegalArgumentException> { PcmInputLevel.measure(shortArrayOf(1), 0) }
        assertFailsWith<IllegalArgumentException> { PcmInputLevel.measure(shortArrayOf(1), 2) }
    }

    @Test fun anOldRunCannotRepopulateTheDisplayAfterStopOrRestart() {
        val window = SoundCheckWindow()
        val first = window.start(1000)
        val level = PcmInputLevel.measure(shortArrayOf(1000), 1)
        assertTrue(window.offer(first, 1100, 1100, level))
        assertNotNull(window.current(1100))
        window.stop()
        assertNull(window.current(1100))
        val second = window.start(1200)
        assertFalse(window.offer(first, 1300, 1300, level))
        assertTrue(window.offer(second, 1300, 1300, level))
    }

    @Test fun staleFutureRollbackAndExpiredInputNeverRemainLive() {
        val window = SoundCheckWindow()
        val run = window.start(1000)
        val level = PcmInputLevel.measure(shortArrayOf(1000), 1)
        assertFalse(window.offer(run, 900, 1100, level))
        assertFalse(window.offer(run, 1200, 1100, level))
        assertFalse(window.offer(run, 1100, 1900, level))
        assertTrue(window.offer(run, 1900, 1900, level))
        assertFalse(window.offer(run, 1800, 1900, level))
        assertNull(window.current(2650))
        assertNull(window.current(1800))
        assertFalse(window.offer(run, 31000, 31000, level))
        assertNull(window.current(31000))
    }

    @Test fun deadlineCannotBeUndoneByALaterCallbackWithAnEarlierClock() {
        val window = SoundCheckWindow()
        val run = window.start(1000)
        val level = PcmInputLevel.measure(shortArrayOf(1000), 1)
        assertTrue(window.offer(run, 30998, 30998, level))
        assertNull(window.current(31000))
        assertFalse(window.offer(run, 30999, 30999, level))
        assertFalse(window.offer(run, 31001, 31001, level))
        assertNull(window.current(31001))
        val next = window.start(32000)
        assertFalse(window.offer(run, 32100, 32100, level))
        assertTrue(window.offer(next, 32100, 32100, level))
    }

    @Test fun rollbackBetweenDisplayTicksClosesTheRunBeforeAnotherSample() {
        val window = SoundCheckWindow()
        val run = window.start(1000)
        val level = PcmInputLevel.measure(shortArrayOf(1000), 1)
        assertTrue(window.offer(run, 1100, 1100, level))
        assertNotNull(window.current(1200))
        assertNull(window.current(1199))
        assertFalse(window.offer(run, 1300, 1300, level))
        assertNull(window.current(1300))
    }

    @Test fun rollbackWhileWaitingForFirstSampleAlsoClosesTheRun() {
        val window = SoundCheckWindow()
        val run = window.start(1000)
        val level = PcmInputLevel.measure(shortArrayOf(1000), 1)
        assertNull(window.current(1200))
        assertNull(window.current(1199))
        assertFalse(window.offer(run, 1300, 1300, level))
        assertNull(window.current(1300))
    }

    @Test fun anInvalidNewStartCannotLeaveThePreviousReadingLive() {
        val window = SoundCheckWindow()
        val run = window.start(1000)
        val level = PcmInputLevel.measure(shortArrayOf(1000), 1)
        assertTrue(window.offer(run, 1100, 1100, level))
        assertNull(window.start(-1))
        assertNull(window.current(1200))
        assertFalse(window.offer(run, 1200, 1200, level))
        val next = window.start(1300)
        assertTrue(window.offer(next, 1400, 1400, level))
    }

    @Test fun staleRunClocksCannotCloseANewerRunAndStalenessCanRecover() {
        val window = SoundCheckWindow()
        val old = window.start(1000)
        window.stop()
        val run = window.start(Long.MAX_VALUE - 29_999)
        val level = PcmInputLevel.measure(shortArrayOf(1000), 1)
        assertFalse(window.offer(old, 0, Long.MAX_VALUE, level))
        assertTrue(window.offer(run, Long.MAX_VALUE - 1000, Long.MAX_VALUE - 1000, level))
        assertNotNull(window.current(Long.MAX_VALUE - 251))
        assertNull(window.current(Long.MAX_VALUE - 250))
        assertTrue(window.offer(run, Long.MAX_VALUE, Long.MAX_VALUE, level))
        assertNotNull(window.current(Long.MAX_VALUE))
    }
}
