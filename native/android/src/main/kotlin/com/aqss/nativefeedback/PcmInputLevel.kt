package com.aqss.nativefeedback

import kotlin.math.abs
import kotlin.math.log10
import kotlin.math.sqrt

/** Digital microphone samples only. Carries no calibration, acoustic safety or actuation claim. */
class PcmInputLevel private constructor(
    val sampleCount: Int,
    val rmsDbfs: Double?,
    val peakFraction: Double,
    val clippedSamples: Int,
) {
    companion object {
        fun measure(samples: ShortArray, count: Int): PcmInputLevel {
            require(count in 1..samples.size)
            var energy = 0.0
            var peak = 0
            var clipped = 0
            for (i in 0 until count) {
                val value = samples[i].toInt()
                val magnitude = abs(value)
                val normalized = value / 32768.0
                energy += normalized * normalized
                peak = maxOf(peak, magnitude)
                if (value == -32768 || value == 32767) clipped++
            }
            val rms = sqrt(energy / count)
            return PcmInputLevel(count, if (rms == 0.0) null else 20.0 * log10(rms), peak / 32768.0, clipped)
        }
    }
}

/** Main-thread display freshness gate, independent of any protection or coverage projector. */
class SoundCheckWindow {
    private var generation = 0L
    private var active = false
    private var startedAt = 0L
    private var lastAt = -1L
    private var latest: PcmInputLevel? = null

    fun start(nowMs: Long): Long {
        require(nowMs >= 0)
        generation++
        active = true; startedAt = nowMs; lastAt = -1; latest = null
        return generation
    }

    fun offer(run: Long, receivedAtMs: Long, nowMs: Long, value: PcmInputLevel): Boolean {
        if (!active || run != generation || receivedAtMs < startedAt || receivedAtMs <= lastAt ||
            nowMs < receivedAtMs || nowMs - receivedAtMs >= 750 || nowMs - startedAt >= 30_000) return false
        latest = value; lastAt = receivedAtMs
        return true
    }

    fun current(nowMs: Long): PcmInputLevel? {
        if (!active || nowMs < lastAt || nowMs - lastAt >= 750 || nowMs - startedAt >= 30_000) {
            latest = null
        }
        return latest
    }

    fun stop() { active = false; latest = null }
}
