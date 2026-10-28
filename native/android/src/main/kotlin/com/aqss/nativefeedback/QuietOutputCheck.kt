package com.aqss.nativefeedback

import java.util.Collections
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

enum class QuietStop { COMPLETE, USER, INACTIVE, FOCUS_DENIED, FOCUS_LOSS, ROUTE_CHANGED,
    BUSY, UNSUPPORTED, TIME_LIMIT, CLOCK_FAULT, ATTEMPT_LIMIT, WRITE_FAILED, INVALID_RESULT,
    BACKEND_FAILED, WORKER_INTERRUPTED }
enum class QuietOperation { MINIMUM, FOCUS, OPEN, FORMAT, ZERO_GAIN, WATCH, PLAY, WRITE, ROUTES,
    RETIRE, PAUSE, FLUSH, UNWATCH, RELEASE, ABANDON }
enum class QuietStage { ENTERED, RETURNED, RECORDED }

/** Independent control-side cut. It neither cancels entered calls nor proves silence. */
class QuietOutputControl {
    private val stopped = AtomicReference<QuietStop?>(null)
    val reason: QuietStop? get() = stopped.get()
    fun stop(reason: QuietStop) { stopped.compareAndSet(null, reason) }
}

data class QuietOutputFormat(val initialized: Boolean, val sampleRate: Int, val channels: Int,
                             val pcm16: Boolean, val bufferFrames: Int, val capacityFrames: Int) {
    val matchesProfile: Boolean get() = initialized && sampleRate == 48000 && channels == 1 && pcm16 &&
        bufferFrames in 1..131072 && capacityFrames in bufferFrames..131072
}
class QuietOutputRoutes private constructor(val types: List<Int>, val totalReported: Int, val multipleQuery: Boolean) {
    companion object {
        fun from(types: List<Int>, totalReported: Int, multipleQuery: Boolean): QuietOutputRoutes {
            require(totalReported >= types.size && totalReported >= 0)
            return QuietOutputRoutes(Collections.unmodifiableList(ArrayList(types.take(16))), totalReported, multipleQuery)
        }
    }
}
interface QuietOutputTrack {
    fun format(): QuietOutputFormat
    fun zeroGain(): Int
    fun watchRoute()
    fun play()
    fun write(samples: ShortArray, offset: Int, count: Int): Int
    fun routes(): QuietOutputRoutes
    fun pause()
    fun flush()
    fun unwatchRoute()
    fun release()
}
/** Construction must not allocate an output track or request focus. Worker calls do that explicitly. */
interface QuietOutputBackend {
    val track: QuietOutputTrack?
    fun minimumBufferBytes(): Int
    fun requestFocus(): Int
    fun open(bufferBytes: Int)
    fun retireCallbacks()
    fun abandonFocus(): Int
}
data class QuietTraceEvent(val sequence: Int, val operation: QuietOperation, val stage: QuietStage,
                           val elapsedMs: Long?, val rawValue: Int?, val exception: Boolean,
                           val offsetSamples: Int?, val requestedSamples: Int?, val acceptedSamples: Int)
class QuietOutputResult internal constructor(
    val reason: QuietStop, val acceptedSamples: Int, val attempts: Int,
    val cleanupSucceeded: Boolean, val quarantined: Boolean, val allocationEntered: Boolean,
    val trackOpened: Boolean, val focusGranted: Boolean, val zeroGainAccepted: Boolean?,
    val constructed: QuietOutputFormat?, val routes: QuietOutputRoutes?, val requestedBufferBytes: Int?,
    val unreportedCall: Boolean, val trace: List<QuietTraceEvent>,
) { val physicalOutputVerified: Boolean get() = false }

/**
 * One worker invokes execute exactly once. Other threads may only close control.
 * The source is 256 zero-valued mono PCM16 samples at requested 48 kHz. This is
 * a diagnostic profile, not a selected/verified physical route or protection path.
 */
class QuietOutputCheck(
    private val gate: ForegroundAudioExclusion,
    private val control: QuietOutputControl,
    private val factory: () -> QuietOutputBackend,
    private val clock: () -> Long,
    private val foreground: () -> Boolean,
    private val waitBeforeRetry: (Long) -> Unit,
) {
    companion object {
        const val SAMPLE_COUNT = 256
        const val MAX_ATTEMPTS = 8
        const val BUDGET_MS = 2000L
        const val RETRY_MS = 10L
        const val MAX_BUFFER_BYTES = 262144
        const val MAX_EVENTS = 96
    }
    private class AdmissionClosed : RuntimeException()
    private val launched = AtomicBoolean(false)
    private val source = ShortArray(SAMPLE_COUNT)
    private val events = ArrayList<QuietTraceEvent>(MAX_EVENTS)
    private var backend: QuietOutputBackend? = null
    private var owned: QuietOutputTrack? = null
    private var accepted = 0
    private var attempts = 0
    private var deadline: Long? = null
    private var lastClock: Long? = null
    private var inCall = false
    private var allocationEntered = false
    private var allocationUncertain = false
    private var focusEntered = false
    private var focusGranted = false
    private var playEntered = false
    private var watchEntered = false
    private var gainAccepted: Boolean? = null
    private var constructed: QuietOutputFormat? = null
    private var routes: QuietOutputRoutes? = null
    private var bufferBytes: Int? = null
    @Volatile var result: QuietOutputResult? = null
        private set

    fun execute(): QuietOutputResult {
        check(launched.compareAndSet(false, true)) { "A quiet check cannot be replayed" }
        if (!foreground()) control.stop(QuietStop.INACTIVE)
        if (control.reason != null) return publish(true)
        val started = eventTime() ?: return publish(true)
        if (started > Long.MAX_VALUE - BUDGET_MS) { control.stop(QuietStop.CLOCK_FAULT); return publish(true) }
        deadline = started + BUDGET_MS
        val lease = gate.acquire(ForegroundAudioExclusion.Tool.OUTPUT, this)
        if (lease == null) { control.stop(QuietStop.BUSY); return publish(true) }
        var cleanupOkay = true
        try {
            admit()
            val device = factory().also { backend = it }
            val minimum = invoke(QuietOperation.MINIMUM) { device.minimumBufferBytes() }
            if (minimum !in 1..MAX_BUFFER_BYTES) { control.stop(QuietStop.UNSUPPORTED); throw AdmissionClosed() }
            val requested = maxOf(512, minimum)
            val aligned = requested + requested % 2
            if (aligned > MAX_BUFFER_BYTES) { control.stop(QuietStop.UNSUPPORTED); throw AdmissionClosed() }
            bufferBytes = aligned
            val focus = invoke(QuietOperation.FOCUS,
                classify = { focusGranted = it == 1; if (!focusGranted) control.stop(QuietStop.FOCUS_DENIED) }) {
                focusEntered = true; device.requestFocus()
            }
            if (focus != 1) throw AdmissionClosed()
            invoke(QuietOperation.OPEN) { allocationEntered = true; device.open(aligned) }
            owned = device.track
            val track = owned ?: run { allocationUncertain = true; control.stop(QuietStop.BACKEND_FAILED); throw AdmissionClosed() }
            constructed = invoke(QuietOperation.FORMAT) { track.format() }
            if (constructed?.matchesProfile != true) { control.stop(QuietStop.UNSUPPORTED); throw AdmissionClosed() }
            invoke(QuietOperation.ZERO_GAIN, classify = {
                gainAccepted = it == 0; if (it != 0) control.stop(QuietStop.UNSUPPORTED)
            }) { track.zeroGain() }
            invoke(QuietOperation.WATCH) { watchEntered = true; track.watchRoute() }
            invoke(QuietOperation.PLAY) { playEntered = true; track.play() }
            while (accepted < SAMPLE_COUNT && attempts < MAX_ATTEMPTS) {
                val offset = accepted
                val remaining = SAMPLE_COUNT - offset
                invoke(QuietOperation.WRITE, offset = offset, requested = remaining,
                    classify = { raw ->
                        if (raw < 0) control.stop(QuietStop.WRITE_FAILED)
                        else if (raw > remaining) control.stop(QuietStop.INVALID_RESULT)
                    }, account = { raw -> if (raw in 1..remaining) accepted += raw }) {
                    attempts++; track.write(source, offset, remaining)
                }
                if (control.reason != null) break
                if (accepted < SAMPLE_COUNT && attempts < MAX_ATTEMPTS) waitBeforeRetry(RETRY_MS)
            }
            if (control.reason == null && accepted < SAMPLE_COUNT) control.stop(QuietStop.ATTEMPT_LIMIT)
            if (control.reason == null) routes = invoke(QuietOperation.ROUTES) { track.routes() }
            control.stop(QuietStop.COMPLETE)
        } catch (_: AdmissionClosed) {
            // Admission closure does not erase an already observed return.
        } catch (_: InterruptedException) {
            control.stop(QuietStop.WORKER_INTERRUPTED); Thread.currentThread().interrupt()
        } catch (_: Exception) {
            control.stop(QuietStop.BACKEND_FAILED)
        } finally {
            control.stop(QuietStop.BACKEND_FAILED)
            cleanupOkay = !allocationUncertain && !inCall
            try {
                if (!inCall) {
                    val device = backend
                    if (device != null) {
                        fun cleanup(op: QuietOperation, action: () -> Unit): Boolean = try {
                            invoke(op, cleanup = true, action = action); true
                        } catch (_: Exception) { cleanupOkay = false; false }
                        cleanup(QuietOperation.RETIRE) { device.retireCallbacks() }
                        val track = owned ?: device.track
                        if (track != null) {
                            val paused = !playEntered || cleanup(QuietOperation.PAUSE) { track.pause() }
                            if (playEntered && paused) cleanup(QuietOperation.FLUSH) { track.flush() }
                            if (watchEntered) cleanup(QuietOperation.UNWATCH) { track.unwatchRoute() }
                            // Best effort release still runs after a previous cleanup
                            // failure; the failure remains sticky and quarantines.
                            cleanup(QuietOperation.RELEASE) { track.release() }
                        }
                        if (focusEntered) {
                            try {
                                val abandoned = invoke(QuietOperation.ABANDON, cleanup = true) { device.abandonFocus() }
                                if (abandoned != 1) cleanupOkay = false
                            } catch (_: Exception) { cleanupOkay = false }
                        }
                    }
                }
            } finally {
                if (inCall) cleanupOkay = false
                val released = gate.release(lease, cleanupOkay)
                publish(cleanupOkay && released)
            }
        }
        return checkNotNull(result)
    }

    private fun admit(): Long {
        if (control.reason != null) throw AdmissionClosed()
        if (!foreground()) control.stop(QuietStop.INACTIVE)
        val now = eventTime()
        if (control.reason != null || now == null) throw AdmissionClosed()
        return now
    }

    private fun eventTime(): Long? {
        val now = try { clock() } catch (_: Exception) { control.stop(QuietStop.CLOCK_FAULT); return null }
        if (now < 0 || lastClock?.let { now < it } == true) { control.stop(QuietStop.CLOCK_FAULT); return null }
        lastClock = now
        if (deadline?.let { now >= it } == true) control.stop(QuietStop.TIME_LIMIT)
        return now
    }

    private fun <T> invoke(op: QuietOperation, cleanup: Boolean = false, offset: Int? = null,
                           requested: Int? = null, classify: (T) -> Unit = {}, account: (T) -> Unit = {},
                           action: () -> T): T {
        val enteredAt = if (cleanup) eventTime() else admit()
        inCall = true
        append(op, QuietStage.ENTERED, enteredAt, null, false, offset, requested)
        try {
            val value = action()
            classify(value)
            val raw = when (value) { is Int -> value; is Boolean -> if (value) 1 else 0; else -> null }
            append(op, QuietStage.RETURNED, eventTime(), raw, false, offset, requested)
            account(value) // Deliberately no admission recheck before accounting.
            append(op, QuietStage.RECORDED, eventTime(), raw, false, offset, requested)
            inCall = false
            return value
        } catch (error: Exception) {
            if (op == QuietOperation.OPEN) allocationUncertain = true
            if (!cleanup) control.stop(if (op == QuietOperation.WRITE) QuietStop.WRITE_FAILED else QuietStop.BACKEND_FAILED)
            append(op, QuietStage.RETURNED, eventTime(), null, true, offset, requested)
            append(op, QuietStage.RECORDED, eventTime(), null, true, offset, requested)
            inCall = false
            throw error
        }
    }

    private fun append(op: QuietOperation, stage: QuietStage, time: Long?, raw: Int?, failed: Boolean,
                       offset: Int?, requested: Int?) {
        check(events.size < MAX_EVENTS)
        events.add(QuietTraceEvent(events.size + 1, op, stage, time, raw, failed, offset, requested, accepted))
    }

    private fun publish(cleanupSucceeded: Boolean): QuietOutputResult = QuietOutputResult(
        control.reason ?: QuietStop.CLOCK_FAULT, accepted, attempts, cleanupSucceeded,
        gate.blocked, allocationEntered, owned != null, focusGranted, gainAccepted, constructed,
        routes, bufferBytes, inCall, Collections.unmodifiableList(ArrayList(events)),
    ).also { result = it }
}
