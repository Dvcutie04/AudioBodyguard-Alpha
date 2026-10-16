package com.aqss.nativefeedback

import kotlin.test.*

class PcmInputLevelTest {
    @Test fun zeroSamplesDoNotClaimAcousticSilence() {
        val level = PcmInputLevel.measure(ShortArray(1600), 1600)
        assertNull(level.rmsDbfs)
        assertEquals(0.0, level.peakFraction)
        assertEquals(0, level.clippedSamples)
    }

    @Test fun digitalAmplitudeUsesSigned16FullScaleAndOnlyTheReadPrefix() {
        val level = PcmInputLevel.measure(shortArrayOf(16384, -16384, 32767), 2)
        assertEquals(-6.020599913, level.rmsDbfs!!, 0.000001)
        assertEquals(0.5, level.peakFraction)
        assertEquals(0, level.clippedSamples)
        assertEquals(2, level.sampleCount)
    }

    @Test fun mostNegativeSampleDoesNotOverflowAndClippingIsCounted() {
        val level = PcmInputLevel.measure(shortArrayOf(-32768, 32767), 2)
        assertEquals(1.0, level.peakFraction)
        assertEquals(2, level.clippedSamples)
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
}
