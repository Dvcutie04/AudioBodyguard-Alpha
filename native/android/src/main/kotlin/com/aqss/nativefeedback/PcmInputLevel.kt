package com.aqss.nativefeedback

import kotlin.math.abs
import kotlin.math.log10
import kotlin.math.sqrt

/** Digital microphone samples only. Carries no calibration, acoustic safety or actuation claim. */
class PcmInputLevel private constructor(
    val sampleCount: Int,
    val rmsDbfs: Double?,
    val peakFraction: Double,
    val fullScaleSamples: Int,
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

/** Main-thread display freshness gate. Clock rollback and expiry latch the run off. */
class SoundCheckWindow {
    enum class EndReason { stopped, clockInvalid, timeLimit }
    var active = false
        private set
    var endReason = EndReason.stopped
        private set
    private var generation = 0L
    private var startedAt = 0L
    private var checkedAt = 0L
    private var lastAt = -1L
    private var latest: PcmInputLevel? = null

    fun start(nowMs: Long): Long? {
        stop()
        if (nowMs < 0 || generation == Long.MAX_VALUE) return null
        generation++
        active = true; startedAt = nowMs; checkedAt = nowMs; lastAt = -1
        return generation
    }

    private fun eligible(nowMs: Long): Boolean {
        if (!active) return false
        val reason = when {
            nowMs < checkedAt -> EndReason.clockInvalid
            nowMs - startedAt >= 30_000 -> EndReason.timeLimit
            else -> null
        }
        if (reason != null) { stop(); endReason = reason; return false }
        checkedAt = nowMs
        return true
    }

    fun offer(run: Long?, receivedAtMs: Long, nowMs: Long, value: PcmInputLevel): Boolean {
        // Reject the old identity before observing its clock; it cannot close a newer run.
        if (run != generation || !eligible(nowMs) || receivedAtMs < startedAt || receivedAtMs <= lastAt ||
            nowMs < receivedAtMs || nowMs - receivedAtMs >= 750) return false
        latest = value; lastAt = receivedAtMs
        return true
    }

    fun current(nowMs: Long): PcmInputLevel? {
        if (!eligible(nowMs) || lastAt < 0 || nowMs - lastAt >= 750) {
            latest = null
        }
        return latest
    }

    fun stop() { active = false; latest = null; endReason = EndReason.stopped }
}
