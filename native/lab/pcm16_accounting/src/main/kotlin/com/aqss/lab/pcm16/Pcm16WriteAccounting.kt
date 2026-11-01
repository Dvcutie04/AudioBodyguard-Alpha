package com.aqss.lab.pcm16

import java.util.Collections

/** Sample units for one interleaved PCM16 request; this does not negotiate a format. */
class Pcm16Span private constructor(
    val offsetSamples: Int,
    val sampleCount: Int,
    val channelCount: Int,
) {
    val offsetFrames: Int get() = offsetSamples / channelCount
    val frameCount: Int get() = sampleCount / channelCount
    val offsetBytes: Long get() = offsetSamples.toLong() * 2L
    val byteCount: Long get() = sampleCount.toLong() * 2L

    companion object {
        fun checked(bufferSamples: Int, offsetSamples: Int, sampleCount: Int, channelCount: Int): Pcm16Span {
            require(bufferSamples > 0 && channelCount > 0)
            require(offsetSamples >= 0 && sampleCount > 0)
            // Subtraction avoids a wrapping offset + count admission check.
            require(sampleCount <= bufferSamples && offsetSamples <= bufferSamples - sampleCount)
            require(bufferSamples % channelCount == 0)
            require(offsetSamples % channelCount == 0 && sampleCount % channelCount == 0)
            return Pcm16Span(offsetSamples, sampleCount, channelCount)
        }
    }
}

enum class Pcm16ResultKind { ACCEPTED_PREFIX, ZERO, NATIVE_ERROR, INVALID_RETURN, EXCEPTION }
enum class Pcm16InhibitReason { USER_HOLD, NATIVE_ERROR, INVALID_RETURN, EXCEPTION, TRACE_FULL }
enum class Pcm16EventKind { CALL_ENTERED, CALL_RETURNED, RETURN_RECORDED, HOLD_REQUESTED, HOLD_ACKNOWLEDGED }

/** A fixture ticket, matched by object identity; its numeric IDs are not authority. */
class Pcm16WriteRequest internal constructor(
    val workId: Long,
    val callId: Int,
    val span: Pcm16Span,
    private val source: ShortArray,
) {
    fun copySamples(): ShortArray = source.copyOfRange(span.offsetSamples, span.offsetSamples + span.sampleCount)
}

data class Pcm16TraceEvent(
    val sequence: Int,
    val kind: Pcm16EventKind,
    val callId: Int?,
    val offsetSamples: Int?,
    val requestedSamples: Int?,
    val rawValue: Int?,
    val resultKind: Pcm16ResultKind?,
    val acceptedByCall: Int?,
    val accountedSamples: Int,
    val inhibitReason: Pcm16InhibitReason?,
)

/**
 * Deterministic, single-thread accounting lab. No native call, scheduler, clock,
 * output authority, cleanup acknowledgement or physical observation is supplied.
 * The scripted driver must report the real return separately from accounting it.
 */
class Pcm16WriteAccounting private constructor(
    val workId: Long,
    val channelCount: Int,
    private val source: ShortArray,
) {
    companion object {
        const val MAX_SAMPLES = 4096
        const val MAX_CALLS = 8
        const val MAX_TRACE_EVENTS = MAX_CALLS * 3 + 2

        fun create(workId: Long, channelCount: Int, samples: ShortArray): Pcm16WriteAccounting {
            require(workId > 0)
            require(samples.size in 1..MAX_SAMPLES)
            Pcm16Span.checked(samples.size, 0, samples.size, channelCount)
            return Pcm16WriteAccounting(workId, channelCount, samples.copyOf())
        }
    }

    private data class Result(val rawValue: Int?, val kind: Pcm16ResultKind, val acceptedSamples: Int?)
    private class Pending(val request: Pcm16WriteRequest, var result: Result? = null)

    private val events = ArrayList<Pcm16TraceEvent>(MAX_TRACE_EVENTS)
    private var pending: Pending? = null
    private var holdAcknowledged = false

    var accountedSamples: Int = 0
        private set
    val accountedFrames: Int get() = accountedSamples / channelCount
    val accountedBytes: Long get() = accountedSamples.toLong() * 2L
    val remainingSamples: Int get() = source.size - accountedSamples
    var callsStarted: Int = 0
        private set
    var admissionOpen: Boolean = true
        private set
    var outcomeUnknown: Boolean = false
        private set
    var inhibitReason: Pcm16InhibitReason? = null
        private set
    val trace: List<Pcm16TraceEvent> get() = Collections.unmodifiableList(ArrayList(events))

    fun beginWrite(): Pcm16WriteRequest? {
        if (!admissionOpen || pending != null || remainingSamples == 0) return null
        if (callsStarted == MAX_CALLS) {
            inhibit(Pcm16InhibitReason.TRACE_FULL)
            return null
        }
        // The three call events are reserved by the fixed call limit. Hold and
        // acknowledgement have two separate slots and never evict call history.
        val span = Pcm16Span.checked(source.size, accountedSamples, remainingSamples, channelCount)
        val request = Pcm16WriteRequest(workId, callsStarted + 1, span, source)
        callsStarted++
        pending = Pending(request)
        outcomeUnknown = true
        append(Pcm16EventKind.CALL_ENTERED, request)
        return request
    }

    fun returned(request: Pcm16WriteRequest, rawValue: Int): Boolean {
        val call = pending ?: return false
        if (call.request !== request || call.result != null) return false
        val result = when {
            rawValue < 0 -> Result(rawValue, Pcm16ResultKind.NATIVE_ERROR, null)
            rawValue > request.span.sampleCount || rawValue % channelCount != 0 ->
                Result(rawValue, Pcm16ResultKind.INVALID_RETURN, null)
            rawValue == 0 -> Result(0, Pcm16ResultKind.ZERO, 0)
            else -> Result(rawValue, Pcm16ResultKind.ACCEPTED_PREFIX, rawValue)
        }
        observeReturn(call, result)
        return true
    }

    /** Driver-observed exception completion; never used to manufacture a timeout return. */
    fun failed(request: Pcm16WriteRequest): Boolean {
        val call = pending ?: return false
        if (call.request !== request || call.result != null) return false
        observeReturn(call, Result(null, Pcm16ResultKind.EXCEPTION, null))
        return true
    }

    fun recordReturn(request: Pcm16WriteRequest): Boolean {
        val call = pending ?: return false
        if (call.request !== request) return false
        val result = call.result ?: return false
        // Validation bounds each accepted prefix by the retained suffix. A hold
        // cannot erase a positive result that returned from an entered call.
        accountedSamples += result.acceptedSamples ?: 0
        append(Pcm16EventKind.RETURN_RECORDED, request, result)
        pending = null
        return true
    }

    fun hold() = inhibit(Pcm16InhibitReason.USER_HOLD)

    /** Only this model's call accounting is acknowledged, never native retirement. */
    fun acknowledgeHold(): Boolean {
        if (admissionOpen || pending != null) return false
        if (!holdAcknowledged) {
            holdAcknowledged = true
            append(Pcm16EventKind.HOLD_ACKNOWLEDGED)
        }
        return true
    }

    private fun observeReturn(call: Pending, result: Result) {
        call.result = result
        append(Pcm16EventKind.CALL_RETURNED, call.request, result)
        when (result.kind) {
            Pcm16ResultKind.NATIVE_ERROR -> inhibit(Pcm16InhibitReason.NATIVE_ERROR)
            Pcm16ResultKind.INVALID_RETURN -> inhibit(Pcm16InhibitReason.INVALID_RETURN)
            Pcm16ResultKind.EXCEPTION -> inhibit(Pcm16InhibitReason.EXCEPTION)
            else -> Unit
        }
    }

    private fun inhibit(reason: Pcm16InhibitReason) {
        if (!admissionOpen) return
        admissionOpen = false
        inhibitReason = reason
        append(Pcm16EventKind.HOLD_REQUESTED)
    }

    private fun append(kind: Pcm16EventKind, request: Pcm16WriteRequest? = null, result: Result? = null) {
        check(events.size < MAX_TRACE_EVENTS)
        events.add(Pcm16TraceEvent(events.size + 1, kind, request?.callId,
            request?.span?.offsetSamples, request?.span?.sampleCount, result?.rawValue,
            result?.kind, result?.acceptedSamples, accountedSamples, inhibitReason))
    }
}
